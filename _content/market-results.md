The selected career sample contains **112 postings** dated 2026-01-15 through 2026-09-28. The scope is US healthcare data analysts in NAICS 62. Title matching includes data analyst, data analytics analyst, business intelligence analyst, BI analyst, clinical analyst and healthcare analyst phrases. Matching uses raw title, with clean title as fallback. This includes some clinical systems roles and can miss analyst titles phrased differently.

The benchmark uses the posting's supplied industry label. It does not filter on a model prediction. These are observed dataset counts, not estimates of all open jobs or currently live vacancies. Expiration and active-URL status were not used to define the cohort.

| Measure | Observed result | Interpretation |
|---|---|---|
| Hiring volume | 112 | Unique posting IDs; cross-ID reposts may remain |
| Salary with explicit USD and positive normalized amount | 3 / 112 | Too few for a headline salary estimate |
| Minimum experience field available | 63 / 112 | Supplied values; zero may encode unspecified experience |
| Recorded minimum of 0–2 years | 44 | Not a verified count of entry-level jobs |
| At least one listed skill | 105 / 112 | Empty skill lists remain in the denominator |

Source: local snapshot [@jobs2026], analyzed by this project's scripts; these observed counts are not findings of the 2017 paper.

## Work arrangement

| Arrangement | Postings | Share of selected sample |
|---|---|---|
| Unknown | 58 | 51.8% |
| Remote | 24 | 21.4% |
| Hybrid | 20 | 17.9% |
| Onsite | 10 | 8.9% |

![Work arrangement counts with missing status shown explicitly.](images/remote.png)

Unknown work arrangement is not onsite. The remote share is a lower bound on explicitly documented remote postings in this dataset, not a population estimate.

## Geography

![Leading standardized states, including the unknown or non-state category.](images/states.png)

Abbreviations and full state names were merged. Country-level strings such as USA and United States were placed in the unknown-or-non-state category. Counts use the supplied single state field; they do not resolve all multi-location postings. Missing geography limits comparisons.

## Salary and experience limits

Only 3 observations have both explicit USD currency and a positive normalized salary amount. The website withholds a headline median because this is below an analyst-selected minimum of 10 comparable observations. Missing currency is not assumed to be USD. Normalization factors and extracted salary evidence were not independently reviewed, so even the retained values require validation before salary advice.

The median supplied minimum-experience value is 0, but zero values cannot establish that employers accept beginners. Review original requirement text before making accessibility recommendations. Raw job descriptions are intentionally not republished by this website.

Download the [benchmark table](data/study/career_benchmark_table.csv), [state counts](data/study/states.csv), and [work-arrangement counts](data/study/remote.csv). Reproduce them with the script and input hashes listed on the study page.
