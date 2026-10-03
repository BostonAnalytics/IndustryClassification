## Exploratory data analysis

This descriptive analysis uses the saved Jobs_2026_US aggregates [@jobs2026]. It examines selection, available career evidence, normalized role labels and skills before interpreting the predictive results. All career percentages use the 112 selected postings unless another denominator is stated. Figures describe recorded advertisements, not live vacancies or population employment.

### Selection and units of analysis

![Sequential posting filters before industry-and-title career selection or employer aggregation. Bar lengths use all 815,193 source records as the denominator; labels give retained counts.](images/eda-selection.png){#fig-eda-selection fig-alt="Five horizontal bars show the number of records retained through date, country, industry and staffing filters." width=95%}

The common filters retain 352,567 of 815,193 records (43.2%). The explicit-US filter removes 0 dated records; unknown country and non-US country are combined in the saved exclusion count. These exclusions describe selection, not proof that every excluded record is erroneous. The pipeline then branches: industry-and-title matching yields 112 career postings, while employer aggregation and eligibility rules yield 362 employers for classification. Those are different units and should not appear as consecutive steps in a single funnel.

### Field coverage and missing evidence

![Availability of five career fields, with a common denominator of 112 postings. A positive salary with explicit USD passes the availability rule but is not independently validated compensation.](images/eda-coverage.png){#fig-eda-coverage fig-alt="Skills have the highest field coverage and explicit USD salary has the lowest; counts and percentages are printed beside each bar." width=95%}

| Evidence rule | Observed | Unavailable under rule | Coverage |
|---|---:|---:|---:|
| Nonempty skills | 105 | 7 | 93.8% |
| Recognized state | 70 | 42 | 62.5% |
| Nonnegative experience | 63 | 49 | 56.2% |
| Known work arrangement | 54 | 58 | 48.2% |
| Positive salary + USD | 3 | 109 | 2.7% |

Availability is field-specific: unavailable can mean missing, unrecognized or excluded by a validity rule. The fields can be missing in the same posting; these counts cannot be added to estimate incomplete records. Salary coverage supports withholding a distribution plot or salary ranking. Recorded experience values require review against requirement text, even when nonnegative.

### Role-label consistency

![Eight most frequent supplied TITLE_NAME labels in the career subset; ties are ordered alphabetically. Labels are reproduced for a data-quality check.](images/eda-roles.png){#fig-eda-roles fig-alt="Normalized labels include Data Scientists, Senior Data Analyst, Management Analysts and the unexpected label Actors." width=95%}

The saved table contains 67 distinct labels. The eight shown account for 41 of 112 postings; the other 59 labels account for 71. The career filter matches raw titles, with clean titles as fallback, whereas this chart uses supplied normalized titles. Labels such as Actors therefore signal records to inspect for disagreement; they do not establish that acting is a healthcare analytics pathway. Counts alone cannot determine whether the raw title, normalization or industry assignment is wrong. No records were relabeled or removed based on this plot.

### Skill frequencies and denominators

![Ten most frequently listed skills as percentages of all selected postings. Multiple skills can occur in one posting, so percentages need not sum to 100.](images/eda-skills.png){#fig-eda-skills fig-alt="SQL is the most frequently listed skill, followed by Tableau; each bar shows a posting count and percentage." width=95%}

SQL appears in 63 postings: 56.2% of all 112, or 60.0% of the 105 with nonempty skill lists. Keeping the 7 postings without skill lists in the primary denominator makes the coverage boundary visible. A missing list does not imply that a role requires no skills. These are marginal frequencies; no skill co-occurrence, correlations or causal training effects can be recovered from these aggregate tables.

### Interpretation and reproducibility

The sample provides stronger descriptive support for skill priorities than for compensation advice. Work-arrangement and state summaries below retain their unknown categories. Temporal trends, salary-by-location comparisons and multivariable EDA require additional row-level summaries; the saved aggregates cannot establish those relationships.

Run `python scripts/publish_eda.py` to regenerate these figures and tables from `run.json` and `market_skills.csv`, without refitting models. Download [selection counts](data/study/eda_selection.csv), [coverage](data/study/eda_coverage.csv), [role labels](data/study/eda_roles.csv) and [skill shares](data/study/eda_skills.csv). Input hashes are recorded in [the EDA manifest](data/study/eda_manifest.json).
