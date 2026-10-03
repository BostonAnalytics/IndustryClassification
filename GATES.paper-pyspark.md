# Paper and PySpark teaching revision

- [x] G1: Paper and core study pages use subject-matter prose without conversation or submission instructions.
  MANUAL: Revised public disclosure and study prose; extracted final Word text rejects removed prose and machine path. Detailed assistance history moved to docs/ai-assistance-history.md.
  EVIDENCE: PowerShell, D:/Repositories/IndustryClassification, final report text and published-byte comparison exits 0: FINAL REPORT VERIFIED.
- [x] G2: A downloadable PySpark workflow exposes preparation, employer aggregation, training-only features, all nine DataFrame classification families, validation and positive-class evaluation.
  CHECK: python scripts/verify_spark_teaching.py
  EXPECT: SPARK TEACHING VERIFIED
  EVIDENCE: PowerShell, repository root, exits 0. Complete Spark 4.2.0 run exits 0: SPARK STUDY COMPLETE. Nine families and two baselines; 815193 source rows; 362 employers; 424 features. Input hashes and processing counts match the original study. Rendered HTML and Word contain all models and scores; visible functions match executable source.
- [x] G3: Rebuild website and Word report with the same walkthrough and validate links, citations and existing evidence.
  CHECK: python scripts/verify_site.py
  EXPECT: SITE VERIFIED
  EVIDENCE: PowerShell, repository root, exits 0: 10 HTML pages. Citation, sample, cohort EDA, source EDA and original study checks all exit 0. Published DOCX bytes match rebuilt file. Changed-file whitespace check passes; unrelated pre-existing GATES.inline-analysis.md trailing blank line remains.
- [x] G4: Inspect rendered Word pages; record runtime validation separately from static validation and preserve existing measured results.
  MANUAL: LibreOffice renderer unavailable. Installed Word exports a valid 36-page PDF but reports COM disconnection on Close; PDF parsed and rendered independently with bundled pypdfium2. Reviewed all-page contact sheets and full-size classifier/results pages; corrected long code lines and confusion-table wrapping. Final source and publication verifications pass. Original scikit-learn metrics remain distinct from the completed Spark experiment.
