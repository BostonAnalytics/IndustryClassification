# Course structure and EDA gates

Scope: consolidate the website into Module 1's suggested career-product pages; retain reference.bib and research framing; add reproducible exploratory figures from saved aggregates without changing model results.

- [ ] E1: Only course-aligned pages remain; navigation and local resources resolve after a clean render.
  CHECK: .venv/Scripts/python.exe scripts/verify_site.py
  EXPECT: SITE VERIFIED
- [ ] E2: EDA tables reconcile with saved data, missingness remains explicit, and the figures and report include resolve.
  CHECK: .venv/Scripts/python.exe scripts/verify_source_eda.py
  EXPECT: EDA VERIFIED
- [ ] E3: Website citations and the Word bibliography resolve; model counts and metrics remain valid.
  CHECK: .venv/Scripts/python.exe scripts/verify_citations.py
  EXPECT: CITATIONS VERIFIED
  MANUAL: Also run verify_study.py; compare the run.json SHA-256 before and after; review all new figures.
- [ ] E4: Render the Word report and inspect available output; disclose any unavailable pagination verification.
  MANUAL: Quarto DOCX render, embedded-image inspection, and page rendering if the installed runtime supports it.

