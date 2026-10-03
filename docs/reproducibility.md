# Reproducibility

## Rebuild the website

```bash
quarto render
python scripts/verify_site.py
```

The output is `_site/index.html`. These commands finish without starting a local server. Quarto 1.11.1 was used. Rendering consumes saved aggregates and does not rerun analysis.

## Reproduce the Jobs_2026_US adaptation

```bash
python -m pip install -r requirements-study.txt
python scripts/run_study.py --data-dir E:/Data/Jobs_2026_US
python scripts/run_eda.py --data-dir E:/Data/Jobs_2026_US
python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026_US --sample=true
python scripts/publish_study.py
python scripts/publish_eda.py
python scripts/verify_study.py
python scripts/verify_eda.py
quarto render
```

Replace the data-directory argument with your authorized copy. The script reads only `jobs_2026_part_*.parquet`; the salary-options lookup is not a posting partition. It scans all 82 parts, streams selected columns, and records hashes, filters, versions, settings and metrics in [run.json](../data/study/run.json). Source postings and descriptions are not redistributed. Aggregates live in `data/study/`; charts live in `images/`.

The period is January 1 through September 30, 2026. Unknown industry codes 00 and 99 are excluded explicitly. The dedicated requirements-study.txt pins the packages used for this run independently of deployment dependencies. The script keeps the first occurrence of each posting ID in filename order. Different IDs for the same real vacancy are not resolved. Country must be explicitly US, industry must be present, and explicitly flagged staffing records are excluded. The dominant employer sector must cover at least 80% of its eligible postings. See [the study](../career_evaluation.qmd) for adaptations and limitations.

## Word report

```bash
quarto render final_report.qmd --to docx
```

`final_report.qmd` combines the paper, new results, market baseline, skills evidence and limitations. Export verification status is recorded in GATES.md. The separate AI disclosure is in `ai-disclosure.qmd` and its rendered website page.

The DOCX export includes the original four charts and four new exploratory charts. Page-layout review could not be completed because LibreOffice is absent. Treat the Word file as a generated draft until its pagination and tables have been checked in Word or LibreOffice. Citation verification also checks that the four new image files are embedded in the DOCX.

On this Windows installation, `quarto.cmd` failed to resolve its path containing spaces. The successful build used `C:/Program Files/Quarto/bin/quarto.exe` directly. Quarto subprocesses also required execution outside the sandbox. These are local build constraints, not study-method changes.

## Execution environment

The user explicitly requested this computer. The guides require assigned AWS EC2 execution, so this is a disclosed deviation. To submit under those rules, reproduce on EC2 and record its environment. Keep credentials out of source control and rendered pages.

## PySpark classification workflow

`scripts/run_spark_study.py` uses the installed PySpark 4.2.0 package (already pinned in `requirements.txt`). Its independent experiment reads the same 82 source partitions and produces `data/spark-study/run.json`. It uses a deterministic within-class hash split, not the scikit-learn split; do not substitute one run's scores into the other's tables. Nine DataFrame classifier families and two constant baselines share 424 training-selected features. Raw postings and employer keys are not exported.

On this Windows host, `spark-submit` initially selected the Microsoft Store Python alias. Explicit `SPARK_HOME` and the repository Python executable resolve that launcher failure. Java 25 also failed with `Invalid argument: connect` for its default temporary Unix-domain socket path. The completed run used a workspace socket directory:

```powershell
$env:PYSPARK_DRIVER_PYTHON='D:/Repositories/IndustryClassification/.venv/Scripts/python.exe'
$env:PYSPARK_PYTHON='D:/Repositories/IndustryClassification/.venv/Scripts/python.exe'
$env:SPARK_HOME='C:/Program Files/Python312/Lib/site-packages/pyspark'
spark-submit --master 'local[2]' --driver-java-options '-Djdk.net.unixdomain.tmpdir=D:/Repositories/IndustryClassification/tmp' --conf spark.ui.enabled=false --conf spark.driver.port=6049 --conf spark.blockManager.port=6050 scripts/run_spark_study.py --data-dir E:/Data/Jobs_2026_US --output-dir data/spark-study
python scripts/publish_spark_teaching.py
python scripts/verify_spark_teaching.py
```

The local Spark run was explicitly authorized. These machine-specific paths belong in this maintainer document, not in the paper. Publishing extracts functions directly from the runnable script and generates the shared walkthrough and notebook. The notebook cells remain unexecuted; a Markdown section contains the separately identified command-line results. Rebuild the Word report and website after publishing.

The October 3 paper revision removes conversation and submission instructions from public prose. Previous detailed AI-assistance history is retained in `docs/ai-assistance-history.md`; the public disclosure is concise. LibreOffice remains unavailable; installed Microsoft Word can export a PDF for page review. Word reported a COM disconnect after export, so the PDF must be checked independently for completeness.

## Static website publication

The `_site` directory is a static website. Public deployment has not been performed. Verify the GitHub Pages configuration and live URL before marking the publication requirement complete.
