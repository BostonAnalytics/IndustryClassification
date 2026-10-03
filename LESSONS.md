# Lessons

Written by /aar-loop after each session's After Action Review. Read this file before starting a new task in this project. Every entry should be concrete and checkable, never vague.

## 2026-10-03 -- Jobs_2026 contains postings outside 2026 and mixed state/remote labels. Apply explicit POSTED bounds, normalize state abbreviations and On-site/Onsite, and record every exclusion before reporting healthcare benchmarks. Do not infer cohort dates from folder names.
- Expected: Reconstruct the paper and run a dated healthcare analyst study across the Jobs_2026 partitions.
- Actual: Scanned 97 partitions and 2350355 rows; final January-September 2026 cohort yields 112 healthcare analyst postings and 362 eligible employers. Initial unrestricted-year results were discarded.
- Why: The input folder combines historical dates, heterogeneous field conventions and conflicting employer sectors. Final filters and the dominant-sector rule are explicit in scripts/run_study.py and data/study/run.json. No global rule or skill change proposed.
- tags: industry-classification,data-quality,quarto
