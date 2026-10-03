## Local Jobs_2026_US exploratory analysis

The analysis and EDA use the Jobs_2026_US snapshot [@jobs2026]. This scan contains **815,193 rows across 82 posting partitions**. Only `jobs_2026_part_*.parquet` files are inputs; supporting exports and backups are excluded. The repository contains aggregates and file hashes.

EDA describes raw rows before the healthcare study's filters. Duplicate IDs are counted but retained in these distributions. Posting-ID uniqueness does not rule out repeated advertisements with different IDs. Populated industry and skills fields are not independently verified labels.

| Measure | Observed value |
|---|---|
| Nonmissing unique IDs | 815,193 |
| Repeated-ID rows beyond first occurrence | 0 |
| Missing IDs | 0 |
| Earliest parsed posting date (UTC) | 2026-01-01 00:00:00+00:00 |
| Latest parsed posting date (UTC) | 2026-12-05 00:00:00+00:00 |
| Missing or unparseable dates | 0 |
| Dated January–September 2026, before other filters | 800,461 |

![Posting-year distribution across all source rows.](images/eda_years.png)

### Field coverage

Missingness covers the 17 fields consumed by the study. Missing means null or whitespace-only; strings such as `[]`, `Unknown` or `Unclassified` still count as populated. Full input schemas are recorded in the EDA manifest.

![Missingness across study fields, denominator all source rows.](images/eda_missingness.png)

| Field | Missing rows | Missing share |
|---|---|---|
| NORMALIZED_SALARY | 734,925 | 90.2% |
| TEXT_PAY_CURRENCY | 635,962 | 78.0% |
| MIN_YEARS_EXPERIENCE | 514,273 | 63.1% |
| NAICS2 | 453,997 | 55.7% |
| NAICS_2022_2 | 453,997 | 55.7% |
| COMPANY_IS_STAFFING | 226,174 | 27.7% |
| REMOTE_TYPE_NAME | 167,132 | 20.5% |
| STATE_NAME | 156,978 | 19.3% |
| TITLE_CLEAN | 66 | 0.0% |
| COMPANY_NAME | 2 | 0.0% |
| ID | 0 | 0.0% |
| POSTED | 0 | 0.0% |
| TITLE_NAME | 0 | 0.0% |
| TITLE_RAW | 0 | 0.0% |
| SKILLS_NAME | 0 | 0.0% |
| SALARY_NORMALIZATION_STATUS | 0 | 0.0% |
| PARSED_COUNTRY_ISO_ABBR | 0 | 0.0% |

### Industry, geography and work arrangement

The following tables show the ten most frequent categories, including missing where it ranks in the top ten. Every share uses all 815,193 source rows. Full distributions are saved as CSVs. Sector uses `NAICS_2022_2`, falling back to `NAICS2` only when blank; 849 nonempty values are outside the study's accepted sector vocabulary. States normalize US abbreviations and full names; other state values share an explicit unrecognized category. Remote labels are lowercased and `On-site` is merged with `Onsite`.


#### Sector codes

| Category | Rows | Share of source |
|---|---|---|
| (missing) | 453,997 | 55.7% |
| 62 | 66,881 | 8.2% |
| 44-45 | 48,720 | 6.0% |
| 54 | 38,460 | 4.7% |
| 23 | 37,449 | 4.6% |
| 31-33 | 37,415 | 4.6% |
| 52 | 26,336 | 3.2% |
| 61 | 23,856 | 2.9% |
| 48-49 | 23,480 | 2.9% |
| 51 | 20,724 | 2.5% |

#### Parsed country

| Category | Rows | Share of source |
|---|---|---|
| US | 815,193 | 100.0% |

#### US states

| Category | Rows | Share of source |
|---|---|---|
| (missing or unrecognized) | 208,253 | 25.5% |
| California | 76,281 | 9.4% |
| Texas | 54,960 | 6.7% |
| New York | 45,876 | 5.6% |
| Florida | 32,599 | 4.0% |
| Virginia | 25,584 | 3.1% |
| Ohio | 23,916 | 2.9% |
| Illinois | 23,175 | 2.8% |
| Pennsylvania | 21,460 | 2.6% |
| North Carolina | 19,724 | 2.4% |

#### Work arrangement

| Category | Rows | Share of source |
|---|---|---|
| unknown | 448,911 | 55.1% |
| (missing) | 167,132 | 20.5% |
| onsite | 98,300 | 12.1% |
| remote | 52,653 | 6.5% |
| hybrid | 48,197 | 5.9% |

### Salary coverage and study boundary

There are **2,756 rows (0.3%)** with a finite positive normalized salary, explicitly USD currency, consistent with the healthcare study salary filter. These are annual-equivalent advertised amounts; they may include compensation beyond base pay. They are not observed earnings or a representative wage survey. Raw amounts with mixed or unknown pay periods are not pooled.

| Annual-equivalent USD measure | Amount |
|---|---|
| Minimum | 37.00 |
| 25th percentile | 76,138.40 |
| Median | 134,528.00 |
| 75th percentile | 205,000.00 |
| Maximum | 514,176,000.00 |

All input filenames, row counts and SHA-256 hashes match the saved healthcare study. The healthcare analysis further restricts dates, country, sector, staffing status and usable employer/title fields. Its employer model and analyst career sample have different units and denominators; the filtering ledger is in [the 2026 study](career_evaluation.qmd).

The [EDA manifest](data/eda/run.json), [field missingness](data/eda/missingness.csv), [posting months](data/eda/posted_month.csv), [sector distribution](data/eda/sector.csv), [country distribution](data/eda/country.csv), [state distribution](data/eda/state.csv) and [work arrangements](data/eda/remote.csv) provide the aggregate evidence.

