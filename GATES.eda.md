# Course structure and EDA gates

Scope: consolidate the website into Module 1's suggested career-product pages; retain reference.bib and research framing; add reproducible exploratory figures from saved aggregates without changing model results.

- [x] E1: Only course-aligned pages remain; navigation and local resources resolve after a clean render.
  CHECK: .venv/Scripts/python.exe scripts/verify_site.py
  EXPECT: SITE VERIFIED
- [x] E2: EDA tables reconcile with saved data, missingness remains explicit, and the figures and report include resolve.
  CHECK: .venv/Scripts/python.exe scripts/verify_eda.py
  EXPECT: EDA VERIFIED
- [x] E3: Website citations and the Word bibliography resolve; model counts and metrics remain valid.
  CHECK: .venv/Scripts/python.exe scripts/verify_citations.py
  EXPECT: CITATIONS VERIFIED
  MANUAL: Also run verify_study.py; compare the run.json SHA-256 before and after; review all new figures.
- [x] E4: Render the Word report and inspect available output; disclose any unavailable pagination verification.
  MANUAL: Quarto DOCX render, embedded-image inspection, and page rendering if the installed runtime supports it.


Evidence (PowerShell, D:/Repositories/IndustryClassification):
- G1: exit 0; EDA COMPLETE: 2,350,355 rows; 97 partitions; study manifest matches=True. Two source EDA charts visually inspected.
- G2: exit 0; EDA VERIFIED: hashes, schemas, aggregate denominators and study snapshot reconcile. Existing study and cohort EDA checks also exit 0.
- G3: site and DOCX render exit 0. After render completion: SITE VERIFIED (9 pages), CITATIONS VERIFIED (13 entries), SOURCE EDA INTEGRATION VERIFIED (HTML and DOCX). git diff --check exits 0. Initial site checks during rendering were premature and superseded by these completed-build checks.
- Final ledger: 3 met, 0 unmet, 0 abandoned.


Current E1-E4 verification, superseding the earlier G1-G3 summary above:
- E1: PowerShell, repository root, exit 0: SITE VERIFIED, nine HTML pages with matching QMD sources and resolving resources.
- E2: Same environment, exit 0: EDA VERIFIED, source hashes and denominators reconciled; all four cohort figures visually inspected.
- E3: Same environment, exit 0: CITATIONS VERIFIED, 13 entries, five-source review, HTML targets and Word bibliography; all four cohort PNGs embedded in DOCX. verify_study.py exits 0. run.json remains E3D95C1408BD63D2FD440C7CD6D1A9D147C2EECE585E2B7D1723B43604B1FA7C.
- E4: Quarto DOCX render exits 0. Available output and embedded figures checked; pagination remains unverified because render_docx.py requires missing LibreOffice. No visual pagination claim is made.
- Final E-series ledger: 4 met, 0 unmet, 0 abandoned; DOCX pagination limitation disclosed. No local server started.
