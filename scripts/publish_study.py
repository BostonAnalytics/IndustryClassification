"""Generate evidence-backed Quarto includes from the saved run, without re-fitting."""
import json
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT/'data/study/run.json').read_text())
c, ledger = d['career'], d['ledger']

def write(name, text):
    (ROOT/'_content'/name).write_text(text.strip()+'\n',encoding='utf-8')

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])

write('study-results.md',f'''
The pipeline read **{ledger['source_rows']:,} rows in {len(d['files'])} posting partitions** and selected January–September 2026 observations. All input files have recorded SHA-256 hashes. No posting ID appeared twice in this input snapshot.

{table(['Filter stage','Remaining postings'],[(label,f"{ledger[key]:,}") for key,label in [('source_rows','All source rows'),('period_rows','Dated January–September 2026'),('us_rows','Parsed country explicitly US'),('sector_known_rows','Valid sector code available'),('nonstaffing_or_unknown_rows','Not explicitly marked as staffing'),('employer_model_postings','Employer name and normalized title available')]])}

Unknown country and unknown sector are exclusions, not negative industry labels. Staffing status that is missing is retained. The geographic and sector filters remove much of the source data, so the retained sample is not representative of all Jobs_2026 records or all US hiring.

## Employer sample and split

There are {ledger['employers_before_filters']:,} employer-name groups before employer-level filters. Of these, {ledger['employers_below_20']:,} have fewer than 20 eligible postings. A further {ledger['employers_without_dominant_sector']:,} lack a sector covering at least 80% of their postings. The model therefore uses **{ledger['model_employers']:,} employers**, below the paper's 10,000-employer target; {ledger['eligible_exactly_consistent']} have exactly consistent sector labels.

{table(['Partition','Employers','NAICS 62','Other'],[(s,v['employers'],v['positive'],v['negative']) for s,v in d['splits'].items()])}

The split uses seed {d['seed']} and stratification, with zero shared employer-name keys across partitions. It is 70/10/20 up to integer rounding. Exact company-name case and whitespace normalization is used; aliases and subsidiaries may still appear as separate entities. This is weaker than the paper's proprietary entity normalization.

## Model results on the held-out employers

{table(['Model','Precision for NAICS 62','Recall','F1','Accuracy'],[(m['model'],f"{m['test_report']['1']['precision']:.3f}",f"{m['test_report']['1']['recall']:.3f}",f"{m['test_report']['1']['f1-score']:.3f}",f"{m['test_report']['accuracy']:.3f}") for m in d['models']])}

![Confusion matrices on held-out employers. Rows are dataset-derived labels and columns are model predictions.](images/confusion.png)

These metrics measure agreement with dataset-derived sector labels, not independently verified employer truth. The GBDT misses 17 of the 35 healthcare employers while predicting no false positives among 38 other employers in this holdout. That small sample cannot establish perfect precision in deployment. The all-positive baseline has F1 0.648, close to GBDT's 0.679; ranking models on F1 alone would conceal their very different precision and recall.

For a career product, predicted healthcare labels could narrow an employer-review queue, but the missed healthcare employers would make automatic exclusion costly. Retain existing labels and review disagreements before changing the career sample. No manually adjudicated undefined-employer labels are available, so the paper's utility scores cannot be reproduced here.

## Training and feature details

Vocabulary thresholds are learned from the training employers only. The selected vocabulary contains {d['features']['titles']} title candidates and {d['features']['name_words']} name words. After the 1% within-employer filter, the fitted matrix has {d['features']['matrix_columns']} observed columns; candidates absent from all training feature vectors are dropped.

The linear SVM tests C = 0.1, 1 and 10 with balanced class penalties. GBDT tests depths 2 and 3 with 100 estimators and learning rate 0.1. Each model is chosen by validation F1, then evaluated on the test partition without refitting. Exact configurations, validation scores, versions and full classification reports are in [run.json](data/study/run.json).

## Differences from the paper

This is an exploratory adaptation: a 2026 dataset, one industry, US-only observations, scikit-learn LinearSVC and GBDT, validation-based tuning instead of the paper's reported cross-validation, and normalized employer-name unigrams without all raw name variants. Name-word frequency counts employers containing the word. The 80% dominant-sector rule is an explicit adaptation for inconsistent posting-level labels. A preliminary unrestricted-year, exact-consistency run exposed data-quality problems; its results are superseded. The final study is not a preregistered confirmatory replication.

Industry fields may themselves derive from title or employer heuristics. Their provenance has not been independently audited. Label circularity, unresolved aliases, cohort selection and noisy titles limit the meaning of predictive agreement. A temporal holdout and independent label review remain future validation work.
''')

write('market-results.md',f'''
The selected career sample contains **{c['postings']} postings** dated {c['date_min'][:10]} through {c['date_max'][:10]}. The scope is US healthcare data analysts in NAICS 62. Title matching includes data analyst, data analytics analyst, business intelligence analyst, BI analyst, clinical analyst and healthcare analyst phrases. Matching uses raw title, with clean title as fallback. This includes some clinical systems roles and can miss analyst titles phrased differently.

The benchmark uses the posting's supplied industry label. It does not filter on a model prediction. These are observed dataset counts, not estimates of all open jobs or currently live vacancies. Expiration and active-URL status were not used to define the cohort.

{table(['Measure','Observed result','Interpretation'],[
('Hiring volume',str(c['postings']),'Unique posting IDs; cross-ID reposts may remain'),
('Salary with explicit USD and positive normalized amount',f"{c['salary_usd_observed']} / {c['postings']}",'Too few for a headline salary estimate'),
('Minimum experience field available',f"{c['experience_observed']} / {c['postings']}",'Supplied values; zero may encode unspecified experience'),
('Recorded minimum of 0–2 years',str(c['entry_0_to_2_years']),'Not a verified count of entry-level jobs'),
('At least one listed skill',f"{c['skills_observed']} / {c['postings']}",'Empty skill lists remain in the denominator')])}

## Work arrangement

{table(['Arrangement','Postings','Share of selected sample'],[(k,v,f'{v/c["postings"]:.1%}') for k,v in c['counts']['remote'].items()])}

![Work arrangement counts with missing status shown explicitly.](images/remote.png)

Unknown work arrangement is not onsite. The remote share is a lower bound on explicitly documented remote postings in this dataset, not a population estimate.

## Geography

![Leading standardized states, including the unknown or non-state category.](images/states.png)

Abbreviations and full state names were merged. Country-level strings such as USA and United States were placed in the unknown-or-non-state category. Counts use the supplied single state field; they do not resolve all multi-location postings. Missing geography limits comparisons.

## Salary and experience limits

Only {c['salary_usd_observed']} observations have both explicit USD currency and a positive normalized salary amount. The website withholds a headline median because this is below an analyst-selected minimum of 10 comparable observations. Missing currency is not assumed to be USD. Normalization factors and extracted salary evidence were not independently reviewed, so even the retained values require validation before salary advice.

The median supplied minimum-experience value is {c['experience_median']:.0f}, but zero values cannot establish that employers accept beginners. Review original requirement text before making accessibility recommendations. Raw job descriptions are intentionally not republished by this website.

Download the [benchmark table](data/study/career_benchmark_table.csv), [state counts](data/study/states.csv), and [work-arrangement counts](data/study/remote.csv). Reproduce them with the script and input hashes listed on the study page.
''')
with (ROOT/'data/study/market_skills.csv').open(encoding='utf-8',newline='') as f:
    rows=list(csv.DictReader(f))
write('skills-results.md',f'''
Across {c['postings']} selected healthcare analyst postings, {c['skills_observed']} have a nonempty skills list. Skills are decoded from the supplied JSON arrays and counted once per posting. The denominator includes all {c['postings']} postings; a missing list does not prove that the job needs no skills.

{table(['Skill','Postings','Share of all selected postings'],[(r['skill'],r['postings'],f"{float(r['share_all_scope_postings']):.1%}") for r in rows[:12]])}

![Most frequently listed skills in the selected healthcare analyst sample.](images/skills.png)

Download the full [market skill table](data/study/market_skills.csv). Skills retain the dataset's names rather than applying a newly invented synonym taxonomy. Frequency supports a market-skills benchmark; it does not measure required proficiency or any individual's gap.
''')
print('STUDY PAGES GENERATED')
