# Website acceptance gates

Scope: faithful paper reconstruction plus locally executed Jobs_2026 adaptation for healthcare data analysts in NAICS 62. User explicitly overrides the EC2 requirement. No public deployment claimed.

- [ ] G1: Paper methods and Tables I, IV-VII transcribed accurately, with limitations and source locators.
  MANUAL: Compare source PDF text and result tables against site source.
- [ ] G2: Quarto website renders successfully without a running server.
  CHECK: quarto render
  EXPECT: Output created
- [ ] G3: Required pages, source references and navigation resolve in generated HTML.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
- [ ] G4: Course mapping, reproducibility instructions and AI disclosure honestly state unavailable data and submission gaps.
  MANUAL: Review all course requirements against coverage page and final status.
- [ ] G5: Jobs_2026 study uses all posting partitions, employer-disjoint evaluation and saved observed career benchmarks with clear adaptations.
  MANUAL: Review run manifest, model metrics, split overlap assertions and generated study outputs.
