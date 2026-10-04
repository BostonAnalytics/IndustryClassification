# Multiclass industry experiment

Scope: Add an executed multiclass employer experiment to the paper and static website while retaining the healthcare analysis.

- [x] G1: Normalize broad sectors, expose class exclusions, split employers without overlap and fit features on training employers only.
  CHECK: python -m unittest discover -s tests -p test_multiclass.py
  EXPECT: OK
  EVIDENCE: PowerShell, repository root, Python C:/Program Files/Python312/python.exe, exit 0: four behavioral tests passed. The repository virtual environment lacks PyArrow; system Python provides the pinned study dependencies.
- [x] G2: Execute on Jobs_2026_US and independently reconcile class support, input provenance, confusion matrices and macro metrics.
  CHECK: python scripts/verify_multiclass.py
  EXPECT: MULTICLASS VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0: MULTICLASS COMPLETE and MULTICLASS VERIFIED. 815193 rows, 375 eligible employers, 328 retained in six sectors, 47 excluded; splits 227/32/69. All 82 input hashes differ from the preserved binary snapshot; this is recorded explicitly and false snapshot equality is rejected by a control. Random forest selected on validation macro-F1 0.316667; test macro-F1 0.376914 versus baseline 0.112179. Integer targets resolve estimator coercion of string NAICS codes.
- [x] G3: Publish measured results, class limitations, reproducible code and figures in the paper and website; preserve healthcare results.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0: SITE VERIFIED (13 HTML pages) and verify_multiclass.py --published. All local resources resolve; CSV metrics and both report/site narratives match run.json. Existing study, Spark and sample verifiers pass; git diff for data/study, data/spark-study and data/sample is empty. Published Word bytes equal the rebuilt report.
- [x] G4: Review paper output, refresh static exports, verify citations and record a brief AAR.
  MANUAL: Inspect generated output and changed-file diff; retain exact verification evidence.
  EVIDENCE: PowerShell, repository root, exit 0: STATIC ASSETS VERIFIED (23 tables), CITATIONS VERIFIED (14 entries), and CRLF-aware git diff --check. Quarto rebuilt the Word report; LibreOffice unavailable, installed Word exported a 40-page PDF (Close reported COM disconnection after successful export), independently rendered with bundled pypdfium2. Reviewed pages 31-34 showing class coverage, splits, model metrics and the confusion figure. A redundant website build collided with the first; the first exited 0 before final resource checks. Two concrete AAR lessons appended to LESSONS.md; no rule/config fixes proposed.
