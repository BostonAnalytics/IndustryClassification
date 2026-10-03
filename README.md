# IndustryClassification

Quarto reconstruction of Goindani et al. (2017), plus a locally executed Jobs_2026_US adaptation for healthcare data analysts in NAICS 62.

## Build

```bash
quarto render
python scripts/verify_site.py
```

Open `_site/index.html`. No local server is required.

## Reproduce the study

```bash
python -m pip install -r requirements-study.txt
python scripts/run_study.py --data-dir E:/Data/Jobs_2026_US
python scripts/publish_study.py
python scripts/verify_study.py
quarto render
quarto render final_report.qmd --to docx
```

Use your authorized Jobs_2026_US location. Aggregate results, input hashes, versions and metrics are saved under `data/study`. Source posting data is not committed. `study.qmd` documents adaptations and label limitations. `course.qmd` records unmet submission requirements. The user explicitly authorized local computation instead of EC2.

The supplied M3/M02_Proj.qmd was absent; M3/M03_Proj.qmd was used with the substitution disclosed. No public deployment or personal skill assessment is claimed.

## References and research framing

Dataset-wide EDA also reads `E:/Data/Jobs_2026_US`: run `python scripts/run_eda.py --data-dir E:/Data/Jobs_2026_US`, then `python scripts/verify_source_eda.py --data-dir E:/Data/Jobs_2026_US`. Aggregates, schemas and input hashes are saved in `data/eda` and included in the data-preparation page and Word report. These describe all source rows before healthcare cohort filtering. If the source snapshot changes, regenerate the study before regenerating and verifying the EDA.

`reference.bib` is the single source for bibliography records. Quarto author-date citations (`@key` or `[@key, locator]`) link to formatted references. Add sources there before citing them; do not hand-maintain a second bibliography in the Word report. The shared `_content/research-framing.md` supplies the website introduction and report literature review. `docs/citation-audit.md` documents source checks and access limitations.

After citation edits, rebuild the site and Word report, then run `python scripts/verify_citations.py`. The site uses Quarto's bundled author-date style; a custom CSL can be added later if a named journal style is required.
