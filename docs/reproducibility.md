# Reproducibility

## Rebuild the website

```bash
quarto render
python scripts/verify_site.py
```

The output is `_site/index.html`. These commands finish without starting a local server. Quarto 1.11.1 was used. Rendering consumes saved aggregates and does not rerun analysis.

## Reproduce the Jobs_2026 adaptation

```bash
python -m pip install -r requirements-study.txt
python scripts/run_study.py --data-dir E:/Data/Jobs_2026
python scripts/publish_study.py
python scripts/verify_study.py
quarto render
```

Replace the data-directory argument with your authorized copy. The script reads only `jobs_2026_part_*.parquet`; the salary-options lookup is not a posting partition. It scans all 97 parts, streams selected columns, and records hashes, filters, versions, settings and metrics in [run.json](data/study/run.json). Source postings and descriptions are not redistributed. Aggregates live in `data/study/`; charts live in `images/`.

The period is January 1 through September 30, 2026. Unknown industry codes 00 and 99 are excluded explicitly. The dedicated requirements-study.txt pins the packages used for this run independently of deployment dependencies. The script keeps the first occurrence of each posting ID in filename order. Different IDs for the same real vacancy are not resolved. Country must be explicitly US, industry must be present, and explicitly flagged staffing records are excluded. The dominant employer sector must cover at least 80% of its eligible postings. See [the study](study.qmd) for adaptations and limitations.

## Word report

```bash
quarto render final_report.qmd --to docx
```

`final_report.qmd` combines the paper, new results, market baseline, skills evidence and limitations. Export verification status is recorded in GATES.md. The separate AI disclosure is in `ai-disclosure.qmd` and its rendered website page.

The DOCX export completed without warnings, with four embedded PNG charts. Page-layout review could not be completed because LibreOffice is absent. Treat the Word file as a generated draft until its pagination and tables have been checked in Word or LibreOffice.

On this Windows installation, `quarto.cmd` failed to resolve its path containing spaces. The successful build used `C:/Program Files/Quarto/bin/quarto.exe` directly. Quarto subprocesses also required execution outside the sandbox. These are local build constraints, not study-method changes.

## Execution environment

The user explicitly requested this computer. The guides require assigned AWS EC2 execution, so this is a disclosed deviation. To submit under those rules, reproduce on EC2 and record its environment. Keep credentials out of source control and rendered pages.

## Publishing

The `_site` directory is a static website. Public deployment has not been performed. Verify the GitHub Pages configuration and live URL before marking the publication requirement complete.
