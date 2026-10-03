# Inline sample analysis

- [ ] G1: Execute displayed processing code on Jobs_2026 with sample=true and save only aggregate partial outputs, with reproducible sample provenance.
  CHECK: python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026 --sample=true
  EXPECT: SAMPLE PUBLISHED
- [ ] G2: Render visible code and corresponding outputs across preparation, market, skills and evaluation pages.
  CHECK: quarto render
  EXPECT: Output created
- [ ] G3: Verify rendered chunks, sample counts and all local site links.
  CHECK: python scripts/verify_sample.py
  EXPECT: SAMPLE VERIFIED
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
