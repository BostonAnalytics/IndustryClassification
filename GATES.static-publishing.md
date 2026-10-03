# Static publishing gates

Scope: Display analysis code without execution, publish saved assets, and add interactive aggregate exploration.

- [x] G1: Saved interactive assets and all aggregate tables match source hashes and ship with local dependencies.
  CHECK: python scripts/verify_static_assets.py
  EXPECT: STATIC ASSETS VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0: STATIC ASSETS VERIFIED; 19 tables and three Plotly views; hash negative control rejected. Git attributes preserve manifested bytes across checkouts.
- [x] G2: Dataset-independent Quarto render completes and all site links resolve.
  CHECK: .venv/Scripts/quarto.exe render
  EXPECT: Output created:
  EVIDENCE: PowerShell, repository root, exit 0: Output created: _site/index.html (12 pages). Bundled renderer used outside sandbox after Windows launcher failures. Existing saved aggregates used; no raw-data scan or model execution.
- [x] G3: Site links and displayed sample/Spark code remain valid.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0: SITE VERIFIED, SAMPLE VERIFIED, SPARK TEACHING VERIFIED. Rendered explorer contains three frames, 19 search inputs and 19 tables. Browser local-file URL blocked by policy; visual interaction testing remains unverified. No local server or public deployment performed.
