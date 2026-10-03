## Research rationale

A career evaluation tool depends on the quality of the industry labels used to select its vacancies. If an employer is assigned to the wrong industry, a student can receive a misleading picture of sector-specific skills and opportunities. Employer-industry classification therefore serves as a data-quality task within a broader career product [@goindani2017].

The target reader is a student seeking a healthcare data analyst role. The product question is: **Which skills and work arrangements recur in the selected US healthcare analyst postings, and how reliably can posting-derived features identify healthcare employers for reviewing that analytical sample?** The primary focus is skill and career readiness. Salary and geography provide context where the observed coverage permits interpretation.

Healthcare is relevant to this pathway because its service organizations generate questions about data quality, reporting and operational decisions. In the analyzed sample, SQL and visualization tools occur frequently enough to support a concrete learning-priority discussion. This rationale concerns the observed sample; it does not establish that healthcare is the strongest industry for every analyst.

## Scope and research questions

The selected pathway is **healthcare data analysts**, including the documented analyst-title variants. The industry anchor is **NAICS 62, Health Care and Social Assistance**, whose official definition covers both healthcare and social-assistance establishments [@naics2022, sector 62]. Consequently, results should not be described as hospital-only findings.

Module 1 prefers NAICS 2022 codes at four or six digits when possible [@ad688m1]. This study retains the user's previously selected two-digit sector 62 to preserve the approved analysis. It is a disclosed scope deviation, not equivalent compliance with the finer-code preference. The implementation prefers `NAICS_2022_2` and falls back to `NAICS2`; that fallback also prevents a claim that every retained label is verified against the 2022 revision. A narrower industry study would require a new filter and rerun.

1. **RQ1, employer classification:** How do a linear SVM and GBDT compare on precision, recall and F1 for dataset-derived NAICS 62 employer labels under an employer-name-disjoint split?
2. **RQ2, career evidence:** Which skills, work arrangements and locations are observed among the selected US healthcare analyst postings from January through September 2026?
3. **RQ3, decision limits:** Which missing fields and label-quality issues prevent reliable salary, accessibility or personal skill-fit recommendations?

The classification task requires non-healthcare employers as a comparison class. That training sample does not expand the career product into an all-industry comparison. The career benchmark remains restricted to NAICS 62 and the selected pathway.

## Short literature review

Five sources establish the method, scope and interpretation of this study. This is a focused narrative review, not a systematic or exhaustive review.

**Employer-industry signals.** @goindani2017 aggregate titles and employer-name keywords to classify employers and flag disagreement with legacy labels. Their distinction between classification and error discovery motivates separate treatment of predictive agreement and independently reviewed label errors in this project.

**Broader error-detection features.** @chern2018 examine employer-industry errors using additional employer and job-description signals and compare SVM with random forest. That study supports exploring richer features, but it is a different experiment from the supplied 2017 SVM/GBDT paper. Its results are not substituted for the original paper's tables.

**Representativeness of job advertisements.** @tsvetkova2024 benchmark Lightcast vacancy distributions against official sources in four countries and find that representativeness differs across geographic, occupational and sectoral dimensions. Their evidence concerns Lightcast, not this Jobs_2026_US snapshot. It motivates caution about population claims and a future external benchmark; it does not supply a correction factor for our sample.

**Industry definition.** The 2022 NAICS manual defines the sector that bounds the career sample [@naics2022]. It classifies establishments by economic activity rather than by an employee's occupation. This distinction explains why a data analyst title alone cannot establish healthcare-industry membership.

**Reproducible implementation.** @pedregosa2011 describe scikit-learn as a general-purpose machine-learning library. The new study uses its estimators as an implementation adaptation. The software citation credits the library; actual versions, parameter choices and results are supported by the saved run manifest rather than by the 2011 paper.

Together, these sources motivate a limited contribution: a reproducible adaptation that connects employer-label checks to a dated, pathway-specific market benchmark. The study does not demonstrate an improvement over the original proprietary system or establish causal effects of skill acquisition on employment.

## Analytical expectations and design status

The analysis explores whether hiring profiles carry an industry signal and whether the career subset yields actionable skill priorities. These are retrospective organizing questions for an already executed exploratory study. They are not preregistered hypotheses. The limited holdout, noisy target labels and absence of participant ratings restrict the strength of the conclusions.

## Data fields and intended use

The following fields connect the project question to the local Jobs_2026_US snapshot [@jobs2026]. Their availability was established by inspecting the local schema; an API-schema equivalence is not assumed.

| Purpose | Fields used | Interpretation control |
|---|---|---|
| Cohort and duplicates | `ID`, `POSTED` | One retained row per ID; explicit date window |
| Career industry | `NAICS_2022_2`, `NAICS2` | Prefer 2022 field; exclude unknown codes |
| Employer grouping | `COMPANY_NAME`, `COMPANY_IS_STAFFING` | Case/whitespace normalization; unresolved aliases remain |
| Occupation and features | `TITLE_RAW`, `TITLE_CLEAN`, `TITLE_NAME` | Declared title matching; training-only vocabulary fitting |
| Skills | `SKILLS_NAME` | Decode lists and count a skill once per posting |
| Compensation | `NORMALIZED_SALARY`, `TEXT_PAY_CURRENCY`, `SALARY_NORMALIZATION_STATUS` | Explicit currency and coverage checks |
| Accessibility | `MIN_YEARS_EXPERIENCE` | Zero is not independently verified as entry level |
| Flexibility and location | `REMOTE_TYPE_NAME`, `STATE_NAME`, `PARSED_COUNTRY_ISO_ABBR` | Standardize categories and retain missingness |

The report follows a research-paper sequence: introduction and rationale, literature, data and methods, results, discussion, limitations and conclusion. The website exposes the same evidence through linked pages while retaining the course's career-product purpose [@ad688m1; @ad688m5].
