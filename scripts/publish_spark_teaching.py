"""Publish executable source excerpts and a notebook from one PySpark script."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'scripts/run_spark_study.py').read_text(encoding='utf-8')
tree = ast.parse(source)
functions = {n.name: ast.get_source_segment(source, n)
             for n in tree.body if isinstance(n, ast.FunctionDef)}
imports = source[source.index('import argparse'):source.index('def prepare')].strip()
sections = [
    ('Load, clean and filter postings', ['prepare'],
     'The input is a set of Parquet posting partitions. The code selects only the fields needed for employer classification, parses dates in UTC, applies the January–September window, requires US geography and a recognized sector, and excludes explicitly marked staffing records. Missing staffing status is retained. Blank employer names and titles cannot contribute to employer features. Duplicate IDs cause an error rather than an arbitrary choice between conflicting records.'),
    ('Aggregate employers and split before learning features', ['employers_and_splits'],
     'Each employer is one observation. At least 20 usable postings and an 80% dominant-sector share are required. The binary target is 1 for NAICS 62 and 0 for other recognized sectors. Within each class, a seeded hash orders employer keys for a reproducible 70/10/20 split. This prevents one normalized employer key from appearing in both training and test data. Different names for the same organization remain an unresolved source of leakage.'),
    ('Construct title shares and employer-name indicators', ['feature_rows'],
     'A title feature equals its posting count divided by all usable postings for that employer. Name-word features are binary indicators. Industry codes define the target and are excluded from the predictor vector. For example, 30 occurrences of a title among 100 employer postings give a title-share value of 0.30.'),
    ('Fit vocabulary on training employers', ['fit_vocabulary', 'vectorize'],
     'For each candidate, significance is positive-class frequency divided by total training frequency. Candidates need more than one positive occurrence. Median significance and frequency thresholds are applied separately to title and name features; if fewer than 50 survive, the frequency threshold falls to the first quartile. Title shares below 1% are removed. Spark uses exact observed quantiles here, which can differ from NumPy interpolated quantiles. The vocabulary is frozen before validation and test vectors are built. An unseen title contributes no new column. Zero means the employer lacks a selected feature, not that its industry is unknown.'),
    ('Specify the classification algorithms', ['candidates'],
     'The following constructors cover the nine classification families in the Spark DataFrame classification guide [@sparkclassification]. Every model receives the same nonnegative feature vectors. Two parameter settings per family illustrate validation-based selection; this small search does not establish a globally optimal model.'),
    ('Select settings and evaluate held-out employers', ['binary_metrics', 'evaluate'],
     'Only training employers fit model parameters. Validation positive-class F1 selects the first best setting in the declared candidate order. The selected model is tested once without refitting. Confusion matrices use rows for observed labels and columns for predictions: [[TN, FP], [FN, TP]]. Precision is TP/(TP+FP), recall is TP/(TP+FN), and F1 is 2TP/(2TP+FP+FN). Undefined ratios are reported as zero. Accuracy is shown beside F1 because the two answer different questions. The majority baseline is learned from training labels; the all-positive baseline reveals how much recall can be obtained without discrimination.'),
]
intro = '''## Analysis design and execution

The measured SVM and GBDT results elsewhere in this report were produced with scikit-learn. This PySpark implementation is a separate comparison using the same source partitions and employer-level feature concept. Its hash-based split, quantile convention, regularization settings and estimator implementations differ, so its scores must be reported separately. Spark's `regParam` is not substituted directly for scikit-learn's `C`.

The complete [Python script](scripts/run_spark_study.py) and [Jupyter notebook](notebooks/pyspark_classification.ipynb) expose the steps below. The script reads an authorized copy of the source data and writes aggregate results to a separate directory. Source postings are not redistributed. PySpark 4.2.0 is pinned in the repository requirements.

```bash
spark-submit --master local[2] --conf spark.ui.enabled=false scripts/run_spark_study.py --data-dir /path/to/Jobs_2026_US --output-dir data/spark-study
```

## Libraries and feature scope

'''
text = intro + '```python\n' + imports + '\n```\n'
cells = [{'cell_type': 'markdown', 'metadata': {}, 'source': [
    '# Employer classification in PySpark\n',
    'Run on your authorized Jobs_2026_US copy. This notebook generates a separate Spark experiment; published scikit-learn scores are not notebook outputs.\n']}]

def code_cell(code):
    return {'cell_type': 'code', 'metadata': {}, 'execution_count': None,
            'outputs': [], 'source': code.splitlines(keepends=True)}

cells.append(code_cell(imports))
for heading, names, prose in sections:
    text += '\n## ' + heading + '\n\n' + prose + '\n\n'
    cells.append({'cell_type': 'markdown', 'metadata': {},
                  'source': ['## ' + heading + '\n', prose]})
    for name in names:
        text += '```python\n' + functions[name] + '\n```\n\n'
        cells.append(code_cell(functions[name]))

text += '''## What each classifier tests

| Classifier | Role in the comparison | Important constraint |
|---|---|---|
| Logistic regression | Linear probability model | Default prediction threshold is 0.5 |
| Decision tree | A small set of feature splits | Depth limits complexity |
| Random forest | Average over randomized trees | More trees increase computation |
| Gradient-boosted trees | Sequentially improve tree predictions | Spark GBT classification is binary |
| Linear SVM | Maximum-margin linear separation | Binary; balanced training weights; no calibrated probabilities |
| Naive Bayes | Conditional-independence baseline | Multinomial variant needs nonnegative features; title shares are a modeling approximation |
| Multilayer perceptron | Nonlinear neural network | Input width equals feature count; output width equals two classes |
| One-vs-rest logistic | Demonstrate a multiclass reduction | Redundant for this binary task; two logistic classifiers are fitted |
| Factorization machine | Model pairwise feature interactions | More latent factors increase capacity |

Source for available estimator families and constraints: @sparkclassification. The comparison uses the binary healthcare task; it does not claim to test every variant of every estimator or the older RDD API.

## Run the workflow

The entry point connects the stages, prints filtering counts and each model's evaluation, and records versions, settings, split support and input hashes. A failed run does not write a new completed manifest.

'''
text += '```python\n' + functions['main'] + '\n\nif __name__ == "__main__":\n    main()\n```\n'
cells.append(code_cell('''data_dir = Path('/path/to/Jobs_2026_US')
files = sorted(data_dir.glob('jobs_2026_part_*.parquet'))
assert files, 'Set data_dir to an authorized copy of the posting partitions'
spark = (SparkSession.builder.appName('HealthcareClassificationNotebook')
         .config('spark.sql.session.timeZone', 'UTC')
         .config('spark.sql.shuffle.partitions', '4').getOrCreate())
try:
    jobs, ledger = prepare(spark, files)
    print(json.dumps(ledger, indent=2))
    employers, support = employers_and_splits(jobs)
    print(json.dumps(support, indent=2))
    long = feature_rows(jobs, employers).cache()
    vocabulary, thresholds = fit_vocabulary(long)
    matrix = vectorize(long, employers, vocabulary).cache()
    results = evaluate(matrix, len(vocabulary))
    print(json.dumps(results, indent=2))
finally:
    spark.stop()
'''))
run_path = ROOT / 'data/spark-study/run.json'
text += '\n## Spark execution evidence\n\n'
if run_path.exists():
    run = json.loads(run_path.read_text(encoding='utf-8'))
    text += f"The completed PySpark {run['version']} run processed {run['ledger']['source_rows']:,} source rows and fitted {run['feature_count']} feature columns. The [Spark manifest](data/spark-study/run.json) records the inputs, partition sizes, candidate settings and measured results.\n\n"
    text += 'The processing counts below are computed by the Spark functions above.\n\n```text\n'
    text += json.dumps(run['ledger'], indent=2) + '\n```\n\n'
    text += '| Partition | Other employers | NAICS 62 employers |\n|---|---:|---:|\n'
    for split in ['train', 'validation', 'test']:
        counts = {int(r['label']): r['count'] for r in run['splits'] if r['split'] == split}
        text += f"| {split} | {counts[0]} | {counts[1]} |\n"
    text += '\n| Model | Precision (NAICS 62) | Recall | F1 | Accuracy |\n|---|---:|---:|---:|---:|\n'
    for r in run['models']:
        text += f"| {r['model']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | {r['accuracy']:.3f} |\n"
    text += '\nConfusion counts use TN (true negatives), FP (false positives), FN (false negatives) and TP (true positives).\n\n| Model | TN | FP | FN | TP |\n|---|---:|---:|---:|---:|\n'
    for r in run['models']:
        (tn, fp), (fn, tp) = r['confusion_matrix']
        text += f"| {r['model']} | {tn} | {fp} | {fn} | {tp} |\n"
    best = max((r for r in run['models'] if 'validation_f1' in r), key=lambda r: r['validation_f1'])
    text += f"\n{best['model']} achieved the highest validation F1 ({best['validation_f1']:.3f}) in this small search; its held-out F1 was {best['f1']:.3f}. This comparison is exploratory. A single small holdout cannot establish a stable ordering of algorithm families. The counts expose missed healthcare employers and false inclusions that F1 alone obscures. The original scikit-learn and Spark holdouts contain different employers; differences between their scores cannot be attributed solely to the software engine.\n"
    cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': [
        '## Recorded command-line run\n',
        'These aggregate results were generated by the companion script, not by executing the saved notebook cells.\n',
        '```json\n' + json.dumps({'ledger': run['ledger'], 'splits': run['splits'],
            'results': [{k: v for k,v in r.items() if k != 'trials'} for r in run['models']]}, indent=2) + '\n```']})
else:
    text += 'No completed Spark result manifest accompanies this version. The code specifies the experiment; the numerical SVM and GBDT results in the Results section belong to the scikit-learn run.\n'
(ROOT / '_content/spark-walkthrough.md').write_text(text, encoding='utf-8')
(ROOT / 'notebooks').mkdir(exist_ok=True)
(ROOT / 'notebooks/pyspark_classification.ipynb').write_text(json.dumps({
    'cells': cells, 'metadata': {'kernelspec': {'display_name': 'Python 3',
    'language': 'python', 'name': 'python3'}}, 'nbformat': 4, 'nbformat_minor': 5}, indent=2), encoding='utf-8')
print('SPARK TEACHING PUBLISHED')
