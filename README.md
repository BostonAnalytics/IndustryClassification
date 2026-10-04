# IndustryClassification

Quarto career evaluation study for healthcare data analysts in NAICS 62, with a research-paper report adapting Goindani et al. (2017).

The website follows the Module 1 sequence: introduction, data preparation, market baseline and EDA, skill-gap analysis, career evaluation, and final recommendations. References and AI disclosure support the submission. Historical reconstruction remains in the report; extra standalone reconstruction and administration pages have been removed.

## Build

```bash
quarto render
python scripts/verify_site.py
```

Open `_site/index.html`. No local server is required.

## Static GitHub Pages publication

Rendering never runs Python or Spark analysis: `_quarto.yml` disables execution
and evaluation and keeps code visible. `analysis_code.qmd` displays every Python
script in full. Browser JavaScript supplies chart interactions and table filters.
The GitHub workflow verifies saved assets, builds the Word report and website,
checks links, and publishes the rendered site without installing study packages
or accessing `E:/Data/Jobs_2026_US`.

After intentionally refreshing the local study or editing scripts, export again:

```bash
python -m pip install plotly==7.1.0
python scripts/publish_interactive.py
python scripts/verify_static_assets.py
quarto render final_report.qmd --to docx
quarto render
python scripts/verify_site.py
```

Commit the refreshed `_content/`, `data/` and `images/` exports along with code.
`.gitattributes` preserves their exact bytes and the script bytes so provenance
hashes survive Windows-to-Linux Git checkouts.
`data/interactive/` contains chart JSON, HTML tables and a hash manifest;
`images/interactive/` contains Plotly HTML, its shared JavaScript bundle and US
map geometry. Existing PNG figures remain available on the study pages and in
the Word report. Every aggregate CSV has a searchable table and download link
on `interactive.qmd`. Paths are relative for GitHub project sites. Map geometry
is saved from <https://cdn.plot.ly/un/usa_110m.json>; no CDN is required at runtime.
The geometry file is a versioned input, not downloaded during site builds.

Raw source records stay outside the repository; only saved aggregates and
provenance are published. Plotly export behavior follows the
[official HTML export documentation](https://plotly.com/python/interactive-html-export/).

## Inline sample walkthrough

The active input is `E:/Data/Jobs_2026_US`: 815,193 records in 82 partitions,
selected for 2026 dates and consistent parsed US location evidence. It replaces,
rather than appends to, the worldwide snapshot. Source records remain outside this
repository. January–September filters still apply; the full study retains 112
career postings and 362 employers. With `sample=true`, the walkthrough selects
81,163 source rows and retains 7 career postings.

`python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026_US --sample=true`
executes the displayed Python chunks and captures their partial outputs across the
preparation, market, skills and evaluation pages. Sampling deterministically selects
approximately 10% of posting IDs using SHA-256 and seed 2017. All partitions are
scanned; only selected rows are retained. No raw posting records are published.
The sample walkthrough does not refit the employer classifier or replace the full-study results.
After regeneration, run `quarto render`, `python scripts/verify_sample.py` and
`python scripts/verify_site.py`. Sample parameters, input row counts, executed code
and captured outputs are saved in `data/sample/run.json`.

## Reproduce the study

The additional multiclass experiment retains the healthcare and binary analyses.
It normalizes combined NAICS sectors before employer aggregation, requires 20
eligible employers per class, and publishes exclusions alongside held-out metrics.
Run it with the Python environment containing `requirements-study.txt`:

```bash
python scripts/run_multiclass.py --data-dir E:/Data/Jobs_2026_US
python -m unittest discover -s tests -p test_multiclass.py
python scripts/verify_multiclass.py
python scripts/publish_multiclass.py
python scripts/publish_interactive.py
quarto render final_report.qmd --to docx
quarto render
python scripts/verify_static_assets.py
python scripts/verify_site.py
python scripts/verify_multiclass.py --published
```

Results are saved in `data/multiclass`, shared by `multiclass_analysis.qmd` and
the Word report through `_content/multiclass-results.md`. The manifest records
input and code hashes, versions, split support and every model trial. Source
records and employer identities are not exported. Publication uses saved results
and requires no analysis run or access to the source drive.

The multiclass manifest also compares the current input hashes against the saved
binary-study manifest. The source now documents NAICS hierarchy repair, so the
new experiment and preserved healthcare results represent different snapshots
despite equal source row counts. Do not present their scores as a controlled
comparison or replace the earlier manifests without recomputing those analyses.

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
quarto render final_report.qmd --to docx
```

Use your authorized Jobs_2026_US location. Aggregate results, input hashes, versions and metrics are saved under `data/study`. Source posting data is not committed. `study.qmd` documents adaptations and label limitations. `course.qmd` records unmet submission requirements. The user explicitly authorized local computation instead of EC2.

The supplied M3/M02_Proj.qmd was absent; M3/M03_Proj.qmd was used with the substitution disclosed. No public deployment or personal skill assessment is claimed.

## References and research framing

Dataset-wide EDA also reads `E:/Data/Jobs_2026_US`: run `python scripts/run_eda.py --data-dir E:/Data/Jobs_2026_US`, then `python scripts/verify_source_eda.py --data-dir E:/Data/Jobs_2026_US`. Aggregates, schemas and input hashes are saved in `data/eda` and included in the data-preparation page and Word report. These describe all source rows before healthcare cohort filtering. If the source snapshot changes, regenerate the study before regenerating and verifying the EDA.

`reference.bib` is the single source for bibliography records. Quarto author-date citations (`@key` or `[@key, locator]`) link to formatted references. Add sources there before citing them; do not hand-maintain a second bibliography in the Word report. The shared `_content/research-framing.md` supplies the website introduction and report literature review. `docs/citation-audit.md` documents source checks and access limitations.

After citation edits, rebuild the site and Word report, then run `python scripts/verify_citations.py`. The site uses Quarto's bundled author-date style; a custom CSL can be added later if a named journal style is required.
