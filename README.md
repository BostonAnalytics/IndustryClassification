# IndustryClassification

Quarto reconstruction of Goindani et al. (2017), plus a locally executed Jobs_2026 adaptation for healthcare data analysts in NAICS 62.

## Build

```bash
quarto render
python scripts/verify_site.py
```

Open `_site/index.html`. No local server is required.

## Reproduce the study

```bash
python -m pip install -r requirements.txt
python scripts/run_study.py --data-dir E:/Data/Jobs_2026
python scripts/publish_study.py
python scripts/verify_study.py
quarto render
quarto render final_report.qmd --to docx
```

Use your authorized Jobs_2026 location. Aggregate results, input hashes, versions and metrics are saved under `data/study`. Source posting data is not committed. `study.qmd` documents adaptations and label limitations. `course.qmd` records unmet submission requirements. The user explicitly authorized local computation instead of EC2.

The supplied M3/M02_Proj.qmd was absent; M3/M03_Proj.qmd was used with the substitution disclosed. No public deployment or personal skill assessment is claimed.
