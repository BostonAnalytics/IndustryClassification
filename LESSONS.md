# Lessons

Written by /aar-loop after each session's After Action Review. Read this file before starting a new task in this project. Every entry should be concrete and checkable, never vague.

## 2026-10-03 -- Jobs_2026 contains postings outside 2026 and mixed state/remote labels. Apply explicit POSTED bounds, normalize state abbreviations and On-site/Onsite, and record every exclusion before reporting healthcare benchmarks. Do not infer cohort dates from folder names.
- Expected: Reconstruct the paper and run a dated healthcare analyst study across the Jobs_2026 partitions.
- Actual: Scanned 97 partitions and 2350355 rows; final January-September 2026 cohort yields 112 healthcare analyst postings and 362 eligible employers. Initial unrestricted-year results were discarded.
- Why: The input folder combines historical dates, heterogeneous field conventions and conflicting employer sectors. Final filters and the dominant-sector rule are explicit in scripts/run_study.py and data/study/run.json. No global rule or skill change proposed.
- tags: industry-classification,data-quality,quarto

## 2026-10-03 -- Use reference.bib and the shared _content/research-framing.md for website/report citations; run scripts/verify_citations.py after rendering both outputs. Keep Chern et al. 2018 (random forest) separate from Goindani et al. 2017 (GBDT).
- Expected: Connect research sources and align the existing website/report with Module 1 research-writing requirements without changing results.
- Actual: Added 12 bibliography entries, a shared five-source review, research questions and paper sections. Fifteen HTML pages and the DOCX bibliography render; citation-target checks and an intentionally broken-target control pass. run.json hash is unchanged.
- Why: One bibliography and shared narrative prevent duplicated source records; related publications have different experimental designs. No global rule or skill change proposed.
- tags: citations,quarto,research-writing

## 2026-10-03 -- For the additional PDFs, distinguish Grybauskas et al. SSRN preprint (3828 deduplicated postings, 3034 complete records, 2108 salary observations including external estimates), Shovic and Everett textbook, and Mahl and Guenther image audit. Do not cite image-audit findings as evidence of bias in Jobs_2026 or transfer the salary model to the three-observation healthcare salary subset.
- Expected: Assess three supplied PDFs for relevance to the healthcare industry-classification and skills study.
- Actual: Reviewed study methods and limitations plus relevant textbook sections; only the SSRN paper directly studies job-posting skills. No website or empirical results changed.
- Why: The supplied files differ in source type, research question, observation unit and salary provenance. This is project context; no rule or skill change proposed.
- tags: literature-review,source-scope

## 2026-10-03 -- Dataset-wide EDA uses scripts/run_eda.py and data/eda; cohort EDA uses scripts/publish_eda.py and data/study. Compare filenames, row counts and SHA-256 hashes with data/study/run.json before presenting both as one snapshot.
- Expected: Include E:/Data/Jobs_2026 in the analysis and EDA.
- Actual: Existing models already used all 97 partitions; added source-level profiles for 2350355 rows while retaining the separate 112-posting career EDA.
- Why: Raw-row and filtered-cohort analyses have different denominators. Separate outputs prevent overwriting the cohort EDA; full manifest comparison verifies common inputs. No rule or skill change proposed.
- tags: eda,provenance,denominators

## 2026-10-03 -- In scripts/publish_eda.py use the saved skill label SQL (Programming Language), not SQL. The role EDA uses TITLE_NAME while cohort selection uses TITLE_RAW/TITLE_CLEAN; unexpected labels must remain visible for review.
- Expected: Generate course-aligned cohort EDA from saved aggregates without changing the study.
- Actual: Added four EDA charts and source tables, consolidated nine website pages, and verified citations plus DOCX figure embedding. Corrected a failed lookup of SQL.
- Why: The supplied skill taxonomy uses expanded labels and title fields serve different purposes. No rule or skill change proposed.
- tags: eda,labels,course-structure

## 2026-10-03 -- For inline Jobs_2026 examples, scripts/publish_sample.py executes the same code strings it publishes; after quarto render, scripts/verify_sample.py checks every displayed code/output line and rejects an intentionally missing output. Keep data/sample separate from full-study aggregates.
- Expected: Show processing code and partial sample=true outputs within the analysis pages.
- Actual: Executed five chunks on 234493 selected rows, yielding 7 healthcare analyst postings; rendered nine pages and verified chunk outputs plus site links.
- Why: The prior website used static aggregate includes with no visible processing chunks. Capturing stdout from the displayed source connects code to its result while retaining static builds. No rule or skill change proposed.
- tags: quarto,sampling,inline-output

## 2026-10-03 -- E:/Data/Jobs_2026 contains an expanded JobHive snapshot: parts 1-22 total 511607 rows; parts 23-97 add 1838748. Check README.md revision history and manifest.json before describing all matching partitions as the original course release.
- Expected: Explain why the report counts 2.35 million rows when the user expects about 510000.
- Actual: Read current Parquet footers: 97 parts total 2350355. Dataset README documents the 511607-row revision, JobHive expansion and one-record correction.
- Why: A filename glob selected the expanded local snapshot; prior reporting omitted the release distinction. No rule or skill change proposed.
- tags: dataset-version,provenance

## 2026-10-03 -- E:/Data/Jobs_2026_US is a separate parser-selected 2026 US snapshot: 815193 rows in 82 partitions. Do not concatenate it with Jobs_2026. Verify source_directory, input hashes, country/year coverage and downstream counts separately; zero country exclusions are valid and absent Counter keys mean zero.
- Expected: Replace worldwide inputs with the user-selected US-only snapshot throughout the study, EDA and sample=true walkthrough.
- Actual: Recomputed full study and EDA; retained 112 career postings and 362 employers with unchanged metrics. Inline sampling now selects 81163 source rows and 7 career postings. Nine HTML pages and the Word report rebuilt; source, sample, site and citation checks passed.
- Why: The original downstream filters already excluded the extra global rows. The US subset changes source-level denominators without changing the final analytical cohort. No rule or skill change proposed.
- tags: us-source,provenance,sampling

## 2026-10-03 -- For this Windows PySpark 4.2.0 installation, set SPARK_HOME explicitly, use the repository .venv Python for PYSPARK_DRIVER_PYTHON and PYSPARK_PYTHON, and pass -Djdk.net.unixdomain.tmpdir=D:/Repositories/IndustryClassification/tmp to Java 25. Keep Spark results in data/spark-study/run.json because its hash split differs from the scikit-learn split.
- Expected: Remove editorial commentary and show executed PySpark processing and every DataFrame classification family in the paper and website.
- Actual: Executed nine classifier families and two baselines on 815193 source rows; published matching source excerpts, notebook, metrics and confusion counts. Rebuilt ten HTML pages and reviewed the 36-page Word export.
- Why: The Spark launcher initially selected a Windows Store alias; Java 25 could not connect through its default temporary Unix-domain socket path. Explicit runtime paths and a workspace socket directory enabled a complete run. Existing course-note rules already prohibit editorial leakage; no rule change proposed.
- tags: pyspark,windows,paper,teaching

## 2026-10-03 -- GitHub Pages builds must verify data/interactive/manifest.json, render saved content with execution disabled, and copy images/interactive/plotly.min.js plus usa_110m.json. Run publish_interactive.py after script or aggregate changes; verify_site.py checks nested assets and published hashes.
- Expected: Publish visible code, saved tables and interactive plots without the Jobs_2026_US drive or study dependencies.
- Actual: Rendered 12 pages; verified 19 tables, three Plotly views, complete source display and matching published assets. Local browser preview was blocked by URL policy; no server was started.
- Why: Analysis was already disabled, but CI still installed analysis dependencies and assets were only partly enumerated. Bundled exports and hash checks isolate publication from computation. No additional rule or skill change proposed.
- tags: publishing,quarto,plotly

## 2026-10-03 -- Preserve byte-hashed scripts and exports with .gitattributes -text entries for scripts/*.py, data/**, images/** and _content/**. core.autocrlf=true otherwise changes Windows CRLF files on Linux checkout and invalidates saved manifests.
- Expected: Saved asset and provenance hashes should verify on both Windows and GitHub Actions Linux.
- Actual: Found CRLF analysis scripts and CSV exports with core.autocrlf=true; added scoped -text attributes and verified the attributes plus local manifest checks.
- Why: Hashing raw bytes makes line endings part of the provenance contract. This was fixed in the requested publication implementation; no further skill or rule change proposed.
- tags: publishing,git,hashes

## 2026-10-03 -- After adding -text attributes, use git add --renormalize on the affected tracked paths and compare git show :path bytes with data/interactive/manifest.json before committing. A normal git add can retain cached LF blobs for unchanged CRLF CSVs.
- Expected: Create focused commits while preserving all saved provenance hashes.
- Actual: The staged-byte audit found six data/study CSV hash mismatches despite passing working-tree checks. Reapplying attributes reconciled all 65 interactive manifest entries.
- Why: Git reused unchanged tracked blobs until renormalization forced its clean-filter rules to run. Existing byte-preservation guidance did not establish that the Git index matched local files. No rule or skill change proposed.
- tags: git,publishing,staging,hashes

## 2026-10-03 -- Before comparing multiclass and healthcare results, check data/multiclass/run.json comparison_with_saved_binary. The current Jobs_2026_US has 82 changed partition hashes after NAICS hierarchy repair despite the same 815193 rows; preserve separate snapshots and verify with scripts/verify_multiclass.py --published.
- Expected: Add multiclass evaluation while retaining healthcare results.
- Actual: Evaluated six sectors and 328 employers; 47 eligible employers excluded by the 20-employer class threshold. All 82 source hashes differ from the preserved binary experiment. Publication, metric reconciliation and negative controls pass.
- Why: The external source was repaired after the binary run; equal filenames and row counts did not establish snapshot equality. No rule or skill change proposed.
- tags: multiclass,provenance,naics

## 2026-10-03 -- For this checkout, system Python supplies the study dependencies including PyArrow, while .venv supplies Plotly 7.1.0 for publish_interactive.py. Verify versions before regenerating exports, and wait for a quarto render process to exit before retrying; two active renders can collide moving HTML files.
- Expected: Regenerate multiclass results and static website using existing tooling.
- Actual: Recovered from absent virtual-environment PyArrow and a Plotly 7.0.0 export by choosing the existing matching runtimes. A redundant Quarto render collided with the slow first build; the first build completed and final checks verified 13 pages and identical Word bytes.
- Why: Installed environments have different package sets, and quiet initial Quarto work was mistaken for a stall. Existing sequential-build discipline suffices; no rule or skill change proposed.
- tags: runtime,quarto,multiclass
