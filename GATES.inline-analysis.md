# Inline sample analysis

- [x] G1: Execute displayed processing code on Jobs_2026 with sample=true and save only aggregate partial outputs, with reproducible sample provenance.
  CHECK: python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026 --sample=true
  EXPECT: SAMPLE PUBLISHED
  EVIDENCE: PowerShell; D:/Repositories/IndustryClassification; exit 0; SAMPLE PUBLISHED: 234,493 sampled rows; 7 career postings.
- [x] G2: Render visible code and corresponding outputs across preparation, market, skills and evaluation pages.
  CHECK: quarto render
  EXPECT: Output created
  EVIDENCE: PowerShell; D:/Repositories/IndustryClassification; exit 0; Output created: _site/index.html; 9 pages rendered.
- [x] G3: Verify rendered chunks, sample counts and all local site links.
  CHECK: python scripts/verify_sample.py
  EXPECT: SAMPLE VERIFIED
  EVIDENCE: PowerShell; D:/Repositories/IndustryClassification; exit 0; all 5 code chunks and partial outputs visible; negative control rejected.
- [x] G4: All generated local site links resolve.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
  EVIDENCE: PowerShell; D:/Repositories/IndustryClassification; exit 0; 9 HTML pages; local resources resolve; published metric CSVs valid.
