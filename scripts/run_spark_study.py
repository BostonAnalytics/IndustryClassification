"""Employer-level PySpark classification; publish aggregate evidence only."""

import argparse
import hashlib
import json
from pathlib import Path

import pyspark
from pyspark.sql import SparkSession, Window, functions as F
from pyspark.ml.classification import (
    LogisticRegression,
    DecisionTreeClassifier,
    RandomForestClassifier,
    GBTClassifier,
    LinearSVC,
    NaiveBayes,
    MultilayerPerceptronClassifier,
    OneVsRest,
    FMClassifier,
)
from pyspark.ml.feature import VectorAssembler

SECTORS = (
    "11 21 22 23 31 32 33 31-33 42 44 45 44-45 48 49 48-49 "
    "51 52 53 54 55 56 61 62 71 72 81 92"
).split()


def prepare(spark, files):
    raw = spark.read.parquet(*[str(p) for p in files])
    columns = [
        "ID",
        "POSTED",
        "COMPANY_NAME",
        "TITLE_NAME",
        "PARSED_COUNTRY_ISO_ABBR",
        "NAICS_2022_2",
        "NAICS2",
        "COMPANY_IS_STAFFING",
    ]
    raw = raw.select(*columns).cache()
    ledger = {"source_rows": raw.count()}
    # Conflicting duplicate IDs need an explicit source ordering rule.
    unique = raw.filter(F.col("ID").isNotNull()).dropDuplicates(["ID"])
    ledger["unique_id_rows"] = unique.count()
    if (
        raw.filter(F.col("ID").isNotNull()).count()
        != ledger["unique_id_rows"]
    ):
        raise ValueError(
            "Duplicate IDs found; resolve source order before analysis"
        )
    dated = unique.withColumn(
        "date", F.to_date(F.try_to_timestamp("POSTED"))
    )
    dated = dated.filter(
        (F.col("date") >= "2026-01-01") & (F.col("date") < "2026-10-01")
    )
    ledger["period_rows"] = dated.count()
    us = dated.filter(
        F.upper(F.trim("PARSED_COUNTRY_ISO_ABBR")) == "US"
    )
    ledger["us_rows"] = us.count()
    sector = F.when(
        F.length(F.trim("NAICS_2022_2")) > 0, F.trim("NAICS_2022_2")
    ).otherwise(F.trim("NAICS2"))
    known = us.withColumn("sector", sector).filter(
        F.col("sector").isin(SECTORS)
    )
    ledger["sector_known_rows"] = known.count()
    jobs = known.filter(
        ~F.coalesce(F.col("COMPANY_IS_STAFFING") == 1, F.lit(False))
    )
    ledger["nonstaffing_or_unknown_rows"] = jobs.count()
    jobs = (
        jobs.withColumn(
            "employer",
            F.regexp_replace(
                F.lower(F.trim("COMPANY_NAME")), r"\s+", " "
            ),
        )
        .withColumn("title", F.lower(F.trim("TITLE_NAME")))
        .filter(
            F.col("employer").isNotNull()
            & ~F.col("employer").isin("", "unknown", "unclassified")
        )
        .filter(
            F.col("title").isNotNull()
            & ~F.col("title").isin("", "unclassified")
        )
        .select("employer", "title", "sector")
        .cache()
    )
    ledger["employer_model_postings"] = jobs.count()
    raw.unpersist()
    return jobs, ledger


def employers_and_splits(jobs):
    totals = jobs.groupBy("employer").agg(
        F.count("*").alias("postings")
    )
    counts = jobs.groupBy("employer", "sector").count()
    dominant = (
        counts.withColumn(
            "rank",
            F.row_number().over(
                Window.partitionBy("employer").orderBy(
                    F.desc("count"), "sector"
                )
            ),
        )
        .filter("rank = 1")
        .join(totals, "employer")
        .filter(
            (F.col("postings") >= 20)
            & (F.col("count") / F.col("postings") >= 0.8)
        )
        .withColumn("label", (F.col("sector") == "62").cast("double"))
        .orderBy(F.desc("postings"), "employer")
        .limit(10000)
        .select("employer", "postings", "label")
    )
    # Rank within class by a seeded hash; no posting can cross employer splits.
    order = Window.partitionBy("label").orderBy(
        F.sha2(F.concat(F.lit("2017:"), F.col("employer")), 256),
        "employer",
    )
    size = Window.partitionBy("label")
    split = (
        dominant.withColumn("rank", F.row_number().over(order))
        .withColumn("class_n", F.count("*").over(size))
        .withColumn(
            "split",
            F.when(
                F.col("rank") <= F.floor(0.7 * F.col("class_n")),
                "train",
            )
            .when(
                F.col("rank") <= F.floor(0.8 * F.col("class_n")),
                "validation",
            )
            .otherwise("test"),
        )
        .select("employer", "postings", "label", "split")
        .cache()
    )
    support = [
        r.asDict()
        for r in split.groupBy("split", "label").count().collect()
    ]
    if len(support) != 6 or any(r["count"] < 2 for r in support):
        raise ValueError(
            "Every split needs at least two employers of each class"
        )
    return split, support


def feature_rows(jobs, employers):
    titles = (
        jobs.groupBy("employer", "title")
        .count()
        .join(employers, "employer")
        .withColumn("feature", F.concat(F.lit("t:"), F.col("title")))
        .withColumn("value", F.col("count") / F.col("postings"))
    )
    words = (
        employers.withColumn(
            "word",
            F.explode(
                F.array_distinct(
                    F.split(
                        F.regexp_replace("employer", "[^a-z]+", " "),
                        " ",
                    )
                )
            ),
        )
        .filter(F.length("word") > 0)
        .withColumn("feature", F.concat(F.lit("w:"), F.col("word")))
        .withColumn("value", F.lit(1.0))
        .withColumn("count", F.lit(1))
    )
    cols = ["employer", "label", "split", "feature", "value", "count"]
    return titles.select(*cols).unionByName(words.select(*cols))


def fit_vocabulary(long):
    # Frequency counts postings for titles, employers for name words.
    stats = (
        long.filter("split = 'train'")
        .groupBy("feature")
        .agg(
            F.sum("count").alias("frequency"),
            F.sum(
                F.when(F.col("label") == 1, F.col("count")).otherwise(0)
            ).alias("positive"),
        )
        .filter("positive > 1")
        .withColumn(
            "significance", F.col("positive") / F.col("frequency")
        )
    )
    vocab, thresholds = [], {}
    for prefix in ["t:", "w:"]:
        part = stats.filter(F.col("feature").startswith(prefix)).cache()
        if not part.count():
            raise ValueError("No training vocabulary for " + prefix)
        s = part.approxQuantile("significance", [0.5], 0)[0]
        f = part.approxQuantile("frequency", [0.5], 0)[0]
        selected = part.filter(
            (F.col("significance") >= s) & (F.col("frequency") >= f)
        )
        if selected.count() < 50:
            f = part.approxQuantile("frequency", [0.25], 0)[0]
            selected = part.filter(
                (F.col("significance") >= s) & (F.col("frequency") >= f)
            )
        vocab.extend(
            r.feature for r in selected.select("feature").collect()
        )
        thresholds[prefix] = {"significance": s, "frequency": f}
        part.unpersist()
    # Remove title columns absent after the within-employer cutoff in training.
    active = long.filter(
        (F.col("value") >= 0.01) & (F.col("split") == "train")
    )
    observed = {
        r.feature for r in active.select("feature").distinct().collect()
    }
    return sorted(set(vocab) & observed), thresholds


def vectorize(long, employers, vocabulary):
    if not vocabulary:
        raise ValueError("Empty training feature matrix")
    # Bound the driver vocabulary by the fitted training features, not raw rows.
    wide = (
        long.filter(F.col("value") >= 0.01)
        .groupBy("employer")
        .pivot("feature", vocabulary)
        .sum("value")
    )
    # Safe column aliases avoid interpreting dots in title names as nested fields.
    aliases = ["x" + str(i) for i in range(len(vocabulary))]
    wide = wide.toDF("employer", *aliases)
    matrix = employers.join(wide, "employer", "left").fillna(
        0.0, subset=aliases
    )
    return VectorAssembler(
        inputCols=aliases, outputCol="features"
    ).transform(matrix)


def candidates(dimension):
    # Two small validation candidates per family keep the example tractable.
    return {
        "Logistic regression": [
            LogisticRegression(regParam=r, maxIter=100)
            for r in [0.01, 0.1]
        ],
        "Decision tree": [
            DecisionTreeClassifier(maxDepth=d, seed=2017)
            for d in [2, 3]
        ],
        "Random forest": [
            RandomForestClassifier(numTrees=100, maxDepth=d, seed=2017)
            for d in [2, 3]
        ],
        "GBT": [
            GBTClassifier(
                maxIter=100, maxDepth=d, stepSize=0.1, seed=2017
            )
            for d in [2, 3]
        ],
        "Linear SVM": [
            LinearSVC(regParam=r, maxIter=100, weightCol="weight")
            for r in [0.01, 0.1]
        ],
        "Naive Bayes": [
            NaiveBayes(smoothing=s, modelType="multinomial")
            for s in [0.5, 1.0]
        ],
        "Multilayer perceptron": [
            MultilayerPerceptronClassifier(
                layers=[dimension, h, 2], maxIter=100, seed=2017
            )
            for h in [8, 16]
        ],
        "One-vs-rest logistic": [
            OneVsRest(
                classifier=LogisticRegression(regParam=r, maxIter=100),
                parallelism=1,
            )
            for r in [0.01, 0.1]
        ],
        "Factorization machine": [
            FMClassifier(
                factorSize=k, maxIter=100, stepSize=0.01, seed=2017
            )
            for k in [4, 8]
        ],
    }


def binary_metrics(predictions):
    counts = {
        (int(r.label), int(r.prediction)): r["count"]
        for r in predictions.groupBy("label", "prediction")
        .count()
        .collect()
    }
    tn, fp = counts.get((0, 0), 0), counts.get((0, 1), 0)
    fn, tp = counts.get((1, 0), 0), counts.get((1, 1), 0)
    total = tn + fp + fn + tp
    if not total:
        raise ValueError("Empty evaluation partition")
    return {
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "accuracy": (tp + tn) / total,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "support": total,
    }


def evaluate(matrix, dimension):
    train = matrix.filter("split = 'train'").cache()
    validation = matrix.filter("split = 'validation'").cache()
    test = matrix.filter("split = 'test'").cache()
    class_counts = {
        int(r.label): r["count"]
        for r in train.groupBy("label").count().collect()
    }
    n = sum(class_counts.values())
    train = train.withColumn(
        "weight",
        F.when(
            F.col("label") == 1, n / (2 * class_counts[1])
        ).otherwise(n / (2 * class_counts[0])),
    ).cache()
    results = []
    for name, options in candidates(dimension).items():
        trials, best, best_score = [], None, -1.0
        for estimator in options:
            model = estimator.fit(train)
            score = binary_metrics(model.transform(validation))["f1"]
            params = {
                p.name: str(v)
                for p, v in estimator.extractParamMap().items()
            }
            trials.append(
                {"parameters": params, "validation_f1": score}
            )
            if score > best_score:
                best, best_score = model, score
        result = {
            "model": name,
            "validation_f1": best_score,
            "trials": trials,
            **binary_metrics(best.transform(test)),
        }
        results.append(result)
        print(json.dumps(result), flush=True)
    majority = max(class_counts, key=class_counts.get)
    for name, value in [
        ("Training majority", majority),
        ("All positive", 1),
    ]:
        results.append(
            {
                "model": name,
                **binary_metrics(
                    test.withColumn("prediction", F.lit(float(value)))
                ),
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(args.data_dir.glob("jobs_2026_part_*.parquet"))
    if not files:
        parser.error("No posting partitions found")
    spark = (
        SparkSession.builder.appName("HealthcareEmployerClassification")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    try:
        jobs, ledger = prepare(spark, files)
        print("FILTER LEDGER " + json.dumps(ledger), flush=True)
        employers, support = employers_and_splits(jobs)
        long = feature_rows(jobs, employers).cache()
        vocabulary, thresholds = fit_vocabulary(long)
        matrix = vectorize(long, employers, vocabulary).cache()
        results = evaluate(matrix, len(vocabulary))
        manifest = {
            "engine": "pyspark",
            "version": pyspark.__version__,
            "seed": 2017,
            "split_method": "within-class SHA256 rank 70/10/20",
            "ledger": ledger,
            "splits": support,
            "feature_count": len(vocabulary),
            "thresholds": thresholds,
            "models": results,
            "files": [],
        }
        for path in files:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
            manifest["files"].append(
                {"file": path.name, "sha256": digest}
            )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "run.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        print("SPARK STUDY COMPLETE", flush=True)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
