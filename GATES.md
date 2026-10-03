# Website acceptance gates

Scope: paper reconstruction plus local Jobs_2026 adaptation for healthcare data analysts in NAICS 62. User explicitly authorized local computation. No public deployment or personal skill assessment claimed.

- [x] G1: Paper methods and Tables I, IV-VII transcribed accurately, with limitations and source locators.
  EVIDENCE: Compared supplied PDF text to sources; visually inspected PDF page 4 Table IV; preserved Table II reconciliation discrepancies and distinguished classification from utility.
- [x] G2: Quarto website renders successfully without a running server.
  CHECK: "C:\Program Files\Quarto\bin\quarto.exe" render
  EXPECT: Output created
  EVIDENCE: PowerShell, D:/Repositories/IndustryClassification, outside sandbox, exit 0; final build renders 14 pages and reports Output created: _site/index.html. quarto.cmd path handling and sandbox subprocess failures required the installed executable directly.
- [x] G3: Required pages and local navigation/resources resolve in generated HTML.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0; SITE VERIFIED: 14 HTML pages; local resources resolve; published metric CSVs valid.
- [x] G4: Course mapping, reproducibility and AI disclosure honestly state empirical results and submission gaps.
  EVIDENCE: Reviewed final pages. M3/M03 substitution, local-over-EC2 authorization, absent personal ratings, proposed/uncomputed scorecard, missing human contribution/standup records and undeployed public site are disclosed. Word source and generated draft exist, with final metrics and four embedded PNG figures verified by OOXML inspection.
- [x] G5: Jobs_2026 study uses all posting partitions, employer-disjoint evaluation and saved observed career benchmarks.
  CHECK: python scripts/verify_study.py
  EXPECT: STUDY VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0. Final full run excludes 00/99, scans 97 hashed partitions and 2350355 rows; 362 model employers and 112 career postings. Split-disjointness assertion passed during execution. Independent aggregate checks reconcile filters, class support, confusion-matrix-derived precision/recall/F1 and benchmark denominators. Final GBDT F1 0.7169811321 and SVM F1 0.5531914894. Python syntax compilation and git diff --check pass.
- [ ] G6: Visual page-layout review for the website and Word report.
  EVIDENCE: Research charts inspected visually. Browser file URL policy blocks local website screenshots; no workaround or local server used. render_docx.py cannot run because LibreOffice soffice.exe is unavailable; Word draft visual layout is unverified.

ABANDON: G6 Browser local-file security policy and unavailable LibreOffice prevent layout review in this environment. Static site build/link checks and DOCX content/media checks pass, but they do not prove full visual layout quality.
