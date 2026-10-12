Aggregate refresh: **2026-10-12 UTC**. Full published snapshots; all 20 files per dataset.

| Dataset | Posting records | Distinct employer names | Source columns |
|---|---:|---:|---:|
| Global | **2,350,355** | **288,870** | 273 |
| US 2026 | **815,193** | **32,962** | 288 |

The US dataset overlaps the global dataset: **do not add their totals**. Employer counts are normalized names, not verified legal entities. Posting records retain duplicate advertisements and do not measure currently live vacancies.

## Industry groups are not job counts

A result around 200 can describe the number of industry categories. Each category can contain thousands of posting records. The explorer shows both measures separately.

### US classification coverage

**815,193 posting records** · **32,962 distinct employer names** · **20 verified files**

Snapshot: `us-repack20-20261011-v1`. All records are included; no title, industry, staffing, or model-training filter is applied.

| NAICS level | Industry groups | Classified posting records | Coverage | Missing codes |
|---|---:|---:|---:|---:|
| 4 | 238 | 263,862 | 32.4% | 551,331 |
| 5 | 260 | 144,209 | 17.7% | 670,984 |
| 6 | 255 | 93,911 | 11.5% | 721,282 |


## SEC evidence: source coverage and candidate matches

The full header audit inspected **32,110 filings**, extracting **30,200 usable filing observations** for **8,746 CIKs**. These describe historical filing entities, not the number of employers in the jobs dataset.

| Dataset | Job records with a candidate issuer | Share of records | Ambiguous job records |
|---|---:|---:|---:|
| Global | 3,202 | 0.14% | 11 |
| US 2026 | 2,898 | 0.36% | 11 |

**Candidate matches are not verified employer links.** They use exact normalized filed names and filings dated no later than the posting. No confirmed employer CIK or job classification is inferred from a name match. These preview results have not been written into the published job snapshots.

The SEC reference import is complete locally. Azure migration and production job enrichment remain pending; this site reports published data and the separate matching preview.

## Posting dates in the US snapshot

| Posting month | Records |
|---|---:|
| 2026-01 | 2,187 |
| 2026-02 | 2,941 |
| 2026-03 | 5,256 |
| 2026-04 | 9,600 |
| 2026-05 | 29,794 |
| 2026-06 | 230,366 |
| 2026-07 | 66,492 |
| 2026-08 | 129,591 |
| 2026-09 | 324,234 |
| 2026-10 | 14,725 |
| 2026-11 | 4 |
| 2026-12 | 3 |

**Date-quality flag:** 7 records have posting months later than this refresh month. They remain in the source totals and should be reviewed.

Posting dates describe source records, not confirmed hiring activity or job liveness.

[Download coverage evidence](data/overview/coverage.json) · [Global snapshot evidence](data/global/snapshot.json) · [US industry explorer](naics_explorer.qmd)

## Useful field coverage in US records

| Field | Populated records | Share of US records |
|---|---:|---:|
| City name | 771,204 | 94.60% |
| Metro area | 41,895 | 5.14% |
| Detailed occupation code | 341,517 | 41.89% |
| Salary lower bound | 130,951 | 16.06% |
| Salary upper bound | 127,465 | 15.64% |
| Archived posting HTML | 67,561 | 8.29% |
| Employer website | 139 | 0.02% |
| Employer description | 2 | 0.00% |
| Employer careers page | 195 | 0.02% |
| Recorded liveness-check time | 41,137 | 5.05% |

Populated means a value is present in the source coverage export; it does not prove accuracy. A recorded liveness check is not evidence that the job is open today. Missing employer and location detail remains visible rather than being inferred.
