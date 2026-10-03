# Website acceptance gates

Scope: faithful explanatory reconstruction of the supplied paper, with course-requirement mapping and explicit empirical gaps. No new research results or public deployment claimed.

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
