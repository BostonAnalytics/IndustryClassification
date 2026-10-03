## Local Jobs_2026 exploratory analysis

The analysis and EDA use `E:\Data\Jobs_2026` [@jobs2026]. This scan contains **2,350,355 rows across 97 posting partitions**. Only `jobs_2026_part_*.parquet` files are inputs; supporting exports and backups are excluded. The source is read locally; the repository contains aggregates and file hashes.

EDA describes raw rows before the healthcare study's filters. Duplicate IDs are counted but retained in these distributions. Posting-ID uniqueness does not rule out repeated advertisements with different IDs. Populated industry and skills fields are not independently verified labels.

| Measure | Observed value |
|---|---|
| Nonmissing unique IDs | 2,350,355 |
| Repeated-ID rows beyond first occurrence | 0 |
| Missing IDs | 0 |
| Earliest parsed posting date (UTC) | 2011-10-03 00:00:00+00:00 |
| Latest parsed posting date (UTC) | 2026-12-30 00:00:00+00:00 |
| Missing or unparseable dates | 45,104 |
| Dated January–September 2026, before other filters | 2,217,149 |

![Posting-year distribution across all source rows.](images/eda_years.png)

### Field coverage

Missingness covers the 17 fields consumed by the study. Missing means null or whitespace-only; strings such as `[]`, `Unknown` or `Unclassified` still count as populated. Full input schemas are recorded in the EDA manifest.

![Missingness across study fields, denominator all source rows.](images/eda_missingness.png)

| Field | Missing rows | Missing share |
|---|---|---|
| NORMALIZED_SALARY | 2,254,861 | 95.9% |
| TEXT_PAY_CURRENCY | 2,110,353 | 89.8% |
| MIN_YEARS_EXPERIENCE | 1,975,397 | 84.0% |
| NAICS2 | 1,885,763 | 80.2% |
| NAICS_2022_2 | 1,885,763 | 80.2% |
| PARSED_COUNTRY_ISO_ABBR | 360,091 | 15.3% |
| COMPANY_IS_STAFFING | 332,125 | 14.1% |
| STATE_NAME | 310,336 | 13.2% |
| REMOTE_TYPE_NAME | 235,365 | 10.0% |
| POSTED | 45,104 | 1.9% |
| TITLE_CLEAN | 651 | 0.0% |
| COMPANY_NAME | 33 | 0.0% |
| ID | 0 | 0.0% |
| TITLE_RAW | 0 | 0.0% |
| TITLE_NAME | 0 | 0.0% |
| SKILLS_NAME | 0 | 0.0% |
| SALARY_NORMALIZATION_STATUS | 0 | 0.0% |

### Industry, geography and work arrangement

The following tables show the ten most frequent categories, including missing where it ranks in the top ten. Every share uses all 2,350,355 source rows. Full distributions are saved as CSVs. Sector uses `NAICS_2022_2`, falling back to `NAICS2` only when blank; 1,242 nonempty values are outside the study's accepted sector vocabulary. States normalize US abbreviations and full names; other state values share an explicit unrecognized category. Remote labels are lowercased and `On-site` is merged with `Onsite`.


#### Sector codes

| Category | Rows | Share of source |
|---|---|---|
| (missing) | 1,885,763 | 80.2% |
| 62 | 79,458 | 3.4% |
| 44-45 | 54,882 | 2.3% |
| 54 | 54,562 | 2.3% |
| 23 | 50,455 | 2.1% |
| 31-33 | 46,557 | 2.0% |
| 52 | 38,283 | 1.6% |
| 61 | 31,504 | 1.3% |
| 48-49 | 29,927 | 1.3% |
| 51 | 29,149 | 1.2% |

#### Parsed country

| Category | Rows | Share of source |
|---|---|---|
| US | 875,972 | 37.3% |
| (missing) | 360,091 | 15.3% |
| DE | 317,861 | 13.5% |
| FR | 280,445 | 11.9% |
| NL | 106,035 | 4.5% |
| BE | 64,594 | 2.7% |
| AT | 49,408 | 2.1% |
| CH | 44,796 | 1.9% |
| SE | 39,985 | 1.7% |
| CA | 23,641 | 1.0% |

#### US states

| Category | Rows | Share of source |
|---|---|---|
| (missing or unrecognized) | 1,685,610 | 71.7% |
| California | 87,245 | 3.7% |
| Texas | 59,159 | 2.5% |
| New York | 51,057 | 2.2% |
| Florida | 34,928 | 1.5% |
| Virginia | 27,540 | 1.2% |
| Ohio | 25,461 | 1.1% |
| Illinois | 25,295 | 1.1% |
| Pennsylvania | 23,329 | 1.0% |
| North Carolina | 21,481 | 0.9% |

#### Work arrangement

| Category | Rows | Share of source |
|---|---|---|
| unknown | 1,778,971 | 75.7% |
| (missing) | 235,365 | 10.0% |
| onsite | 132,258 | 5.6% |
| remote | 110,411 | 4.7% |
| hybrid | 93,350 | 4.0% |

### Salary coverage and study boundary

There are **4,883 rows (0.2%)** with a finite positive normalized salary, explicitly USD currency, consistent with the healthcare study salary filter. These are annual-equivalent advertised amounts; they may include compensation beyond base pay. They are not observed earnings or a representative wage survey. Raw amounts with mixed or unknown pay periods are not pooled.

| Annual-equivalent USD measure | Amount |
|---|---|
| Minimum | 1.50 |
| 25th percentile | 75,920.00 |
| Median | 137,500.00 |
| 75th percentile | 205,000.00 |
| Maximum | 514,176,000.00 |

All input filenames, row counts and SHA-256 hashes match the saved healthcare study. The healthcare analysis further restricts dates, country, sector, staffing status and usable employer/title fields. Its employer model and analyst career sample have different units and denominators; the filtering ledger is in [the 2026 study](career_evaluation.qmd).

Reproduce with `python scripts/run_eda.py --data-dir E:/Data/Jobs_2026`. [EDA manifest](data/eda/run.json), [field missingness](data/eda/missingness.csv), [posting months](data/eda/posted_month.csv), [sector distribution](data/eda/sector.csv), [country distribution](data/eda/country.csv), [state distribution](data/eda/state.csv) and [work arrangements](data/eda/remote.csv) provide the aggregate evidence.

