# Citation and Module 1 revision gates

Scope: reference.bib, linked citations, a five-source narrative review and research-paper framing. Existing user-selected NAICS 62 scope and analytical results preserved.

- [x] C1: Bibliographic records have source-supported metadata and source-specific claims.
  EVIDENCE: Twelve records in reference.bib; supplied paper, author-uploaded record, Springer, OECD, JMLR and official NAICS manual checked. docs/citation-audit.md distinguishes publisher-checked metadata, author-record DOI metadata with unverified live resolution, local dataset and local course sources. No missing page range or dataset DOI invented.
- [x] C2: Applicable Module 1 writing requirements are addressed and remaining deviations explicit.
  EVIDENCE: Shared introduction supplies target user, rationale, RQ1-RQ3, a five-source narrative review, sector justification, field map and exploratory status. Report adds abstract, methods, results, discussion and conclusion. Course page explicitly retains sector 62 versus preferred finer codes and user-authorized local execution versus EC2. No team, publication or personal-rating claims fabricated.
- [x] C3: Website and report build with resolved citations, bibliography targets and local links.
  CHECK: python scripts/verify_citations.py
  EXPECT: CITATIONS VERIFIED
  EVIDENCE: PowerShell, D:/Repositories/IndustryClassification, exit 0: 12 bibliography entries, five-source review, HTML targets and Word bibliography resolve. Negative missing-target control correctly fails. Quarto executable outside sandbox renders 15 pages and final_report.docx without citation warnings. verify_site.py passes. Prior visual layout limitation remains unchanged; no new visual verification claimed.
- [x] C4: Existing metrics remain unchanged and data checks pass.
  CHECK: python scripts/verify_study.py
  EXPECT: STUDY VERIFIED
  EVIDENCE: PowerShell, repository root, exit 0. Filter ledger, metrics and benchmark denominators reconcile. run.json SHA-256 before and after: E3D95C1408BD63D2FD440C7CD6D1A9D147C2EECE585E2B7D1723B43604B1FA7C. git diff --check passes. No analytical refit performed.
