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
