# US source migration

- [x] G1: Recompute study from E:/Data/Jobs_2026_US and reconcile metrics and counts.
  CHECK: python scripts/verify_study.py
  EXPECT: STUDY VERIFIED
  EVIDENCE: PowerShell; D:/Repositories/IndustryClassification; exit 0; ledger and confusion metrics reconcile; 815193 rows, 82 partitions, 112 career postings, 362 employers.
- [x] G2: Recompute source and cohort EDA with matching input hashes.
  CHECK: python scripts/verify_source_eda.py --data-dir E:/Data/Jobs_2026_US
  EXPECT: EDA VERIFIED
  EVIDENCE: PowerShell; repository root; exit 0; 815193 rows, hashes, schemas and study snapshot reconcile. verify_eda.py also exits 0; country US and year 2026 cover every source row.
- [x] G3: Rebuild website and report with US source descriptions and refreshed sample=true outputs.
  CHECK: python scripts/verify_sample.py
  EXPECT: SAMPLE VERIFIED
  EVIDENCE: PowerShell; repository root; exit 0; all five chunks and outputs visible, negative control rejected. Quarto rendered nine pages and final_report.docx, exits 0. Sample selects 81163 rows and 7 career postings.
- [x] G4: Verify site links and report citations after rendering.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
  EVIDENCE: PowerShell; repository root; exit 0; nine HTML pages and local resources verified. verify_citations.py exits 0 with 13 bibliography entries and resolved HTML/Word references.
