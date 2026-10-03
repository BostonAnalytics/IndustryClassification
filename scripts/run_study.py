"""Run the Jobs_2026 adaptation; publish aggregates only. No servers or API calls."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq
import sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'study'
FIG = ROOT / 'images'
ROLE = re.compile(r'\b(data analyst|data analytics analyst|business intelligence analyst|bi analyst|clinical analyst|healthcare analyst|health care analyst)\b', re.I)
COLS = ['ID','POSTED','COMPANY_NAME','COMPANY_IS_STAFFING','TITLE_NAME','TITLE_RAW','TITLE_CLEAN',
        'NAICS_2022_2','NAICS2','SKILLS_NAME','REMOTE_TYPE_NAME','MIN_YEARS_EXPERIENCE',
        'NORMALIZED_SALARY','TEXT_PAY_CURRENCY','SALARY_NORMALIZATION_STATUS',
        'STATE_NAME','PARSED_COUNTRY_ISO_ABBR']
STATE_NAMES = 'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|')
STATE_CODES = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
STATE_MAP = dict(zip(STATE_CODES, STATE_NAMES)) | {n.upper(): n for n in STATE_NAMES}
KNOWN_SECTORS = set('11 21 22 23 31 32 33 31-33 42 44 45 44-45 48 49 48-49 51 52 53 54 55 56 61 62 71 72 81 92'.split())

def clean(value):
    return '' if value is None or pd.isna(value) else str(value).strip()

def tokens(name):
    return set(re.findall(r'[a-z]+', name.lower()))

def select_vocab(all_counts, positive_counts):
    candidates = [t for t in all_counts if positive_counts[t] > 1]
    if not candidates:
        raise ValueError('No candidate features after positive-frequency filter')
    sig = {t: positive_counts[t] / all_counts[t] for t in candidates}
    s_threshold = float(np.median(list(sig.values())))
    f_threshold = float(np.median([all_counts[t] for t in candidates]))
    chosen = {t for t in candidates if sig[t] >= s_threshold and all_counts[t] >= f_threshold}
    if len(chosen) < 50:
        f_threshold = float(np.quantile([all_counts[t] for t in candidates], .25))
        chosen = {t for t in candidates if sig[t] >= s_threshold and all_counts[t] >= f_threshold}
    return chosen, {'significance_threshold': s_threshold, 'frequency_threshold': f_threshold}

def bar_chart(labels, values, title, xlabel, filename):
    fig, ax = plt.subplots(figsize=(8, max(3, len(labels)*.42)))
    ax.barh(labels[::-1], values[::-1], color='#087e8b')
    ax.set_title(title, loc='left', pad=15, fontweight='bold')
    ax.set_xlabel(xlabel)
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / filename, bbox_inches='tight')
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--minimum-label-share', type=float, default=.8)
    args = parser.parse_args()
    if not .5 < args.minimum_label_share <= 1:
        parser.error('--minimum-label-share must be greater than .5 and at most 1')
    files = sorted(args.data_dir.glob('jobs_2026_part_*.parquet'))
    if not files:
        raise SystemExit('No jobs_2026_part_*.parquet files found')
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(exist_ok=True)
    ledger = Counter()
    seen = set()
    employers = defaultdict(lambda: {'titles': Counter(), 'sectors': Counter(), 'count': 0})
    career = []
    manifests = []
    for file in files:
        parquet = pq.ParquetFile(file)
        missing = set(COLS)-set(parquet.schema_arrow.names)
        if missing:
            raise ValueError(f'{file.name}: missing {sorted(missing)}')
        manifests.append({'file': file.name, 'bytes': file.stat().st_size, 'rows': parquet.metadata.num_rows,
                          'sha256': hashlib.file_digest(file.open('rb'), 'sha256').hexdigest()})
        for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
            # Batch date parsing handles heterogeneous timestamp strings without per-row overhead.
            dates = pd.to_datetime(batch.column('POSTED').to_pylist(), errors='coerce', utc=True, format='mixed')
            for row, posted in zip(batch.to_pylist(), dates):
                ledger['source_rows'] += 1
                identifier = row['ID']
                if identifier is None:
                    ledger['missing_id'] += 1
                    continue
                if identifier in seen:
                    ledger['duplicate_id'] += 1
                    continue
                seen.add(identifier)
                ledger['unique_id_rows'] += 1
                if pd.isna(posted) or not (pd.Timestamp('2026-01-01',tz='UTC') <= posted < pd.Timestamp('2026-10-01',tz='UTC')):
                    ledger['outside_period_or_unknown_date'] += 1
                    continue
                ledger['period_rows'] += 1
                if clean(row['PARSED_COUNTRY_ISO_ABBR']).upper() != 'US':
                    ledger['non_us_or_unknown_country'] += 1
                    continue
                ledger['us_rows'] += 1
                sector = clean(row['NAICS_2022_2']) or clean(row['NAICS2'])
                if sector not in KNOWN_SECTORS:
                    ledger['missing_or_invalid_sector'] += 1
                    continue
                ledger['sector_known_rows'] += 1
                if row['COMPANY_IS_STAFFING'] == 1:
                    ledger['staffing_excluded'] += 1
                    continue
                ledger['nonstaffing_or_unknown_rows'] += 1
                raw = clean(row['TITLE_RAW']) or clean(row['TITLE_CLEAN'])
                if sector == '62' and ROLE.search(raw):
                    career.append({k: row[k] for k in COLS if k not in ('ID','COMPANY_NAME','COMPANY_IS_STAFFING')})
                name = re.sub(r'\s+', ' ', clean(row['COMPANY_NAME']).casefold())
                title = clean(row['TITLE_NAME']).casefold()
                if not name or name in ('unknown','unclassified') or not title or title == 'unclassified':
                    ledger['missing_employer_or_title'] += 1
                    continue
                e = employers[name]
                e['count'] += 1
                e['titles'][title] += 1
                e['sectors'][sector] += 1
                ledger['employer_model_postings'] += 1
        print(f'Read {file.name}: {ledger["source_rows"]:,} rows', flush=True)

    ledger['employers_before_filters'] = len(employers)
    eligible = []
    for name, e in employers.items():
        if e['count'] < 20:
            ledger['employers_below_20'] += 1
        elif e['sectors'].most_common(1)[0][1] / e['count'] < args.minimum_label_share:
            ledger['employers_without_dominant_sector'] += 1
        else:
            eligible.append(name)
            ledger['eligible_exactly_consistent'] += len(e['sectors']) == 1
    eligible.sort(key=lambda n: (-employers[n]['count'], n))
    ledger['eligible_employers_before_cap'] = len(eligible)
    names = eligible[:10000]
    ledger['model_employers'] = len(names)
    y = np.array([int(employers[n]['sectors'].most_common(1)[0][0] == '62') for n in names])
    if len(names) < 50 or min(Counter(y).values()) < 10 or len(set(y)) < 2:
        raise ValueError('Insufficient employers or class support for stratified model evaluation')
    indices = np.arange(len(names))
    train, rest = train_test_split(indices, test_size=.3, random_state=2017, stratify=y)
    valid, test = train_test_split(rest, test_size=2/3, random_state=2017, stratify=y[rest])
    assert not (set(train)&set(valid) or set(train)&set(test) or set(valid)&set(test))
    counts_t, pos_t, counts_w, pos_w = Counter(), Counter(), Counter(), Counter()
    for idx in train:
        name = names[idx]
        e = employers[name]
        counts_t.update(e['titles'])
        counts_w.update(tokens(name))
        if y[idx]:
            pos_t.update(e['titles'])
            pos_w.update(tokens(name))
    titles, title_thresholds = select_vocab(counts_t, pos_t)
    words, name_thresholds = select_vocab(counts_w, pos_w)
    features = []
    for name in names:
        e = employers[name]
        vector = {'t:'+t: count/e['count'] for t,count in e['titles'].items()
                  if t in titles and count/e['count'] >= .01}
        vector.update({'w:'+w: 1. for w in tokens(name)&words})
        features.append(vector)
    vectorizer = DictVectorizer(sparse=True)
    vectorizer.fit([features[i] for i in train])
    X = vectorizer.transform(features)
    model_results = []
    predictions = {}
    for model_name, options in [
        ('Linear SVM', [LinearSVC(C=c, class_weight='balanced', random_state=2017, max_iter=20000) for c in [.1,1,10]]),
        ('GBDT', [GradientBoostingClassifier(n_estimators=100, max_depth=d, learning_rate=.1, random_state=2017) for d in [2,3]])]:
        best = None
        trials = []
        for model in options:
            model.fit(X[train], y[train])
            score = f1_score(y[valid], model.predict(X[valid]), zero_division=0)
            trials.append({'params': model.get_params(), 'validation_f1': score})
            if best is None or score > best[0]:
                best = (score, model)
        pred = best[1].predict(X[test])
        predictions[model_name] = pred
        model_results.append({'model': model_name, 'validation_f1': best[0], 'trials': trials,
                              'test_report': classification_report(y[test], pred, output_dict=True, zero_division=0),
                              'confusion_matrix': confusion_matrix(y[test], pred, labels=[0,1]).tolist()})
    for name, pred in [('Majority negative', np.zeros(len(test), dtype=int)), ('All positive', np.ones(len(test), dtype=int))]:
        model_results.append({'model': name, 'test_report': classification_report(y[test], pred, output_dict=True, zero_division=0),
                              'confusion_matrix': confusion_matrix(y[test], pred, labels=[0,1]).tolist()})
    splits = {name: {'employers': len(ix), 'positive': int(y[ix].sum()), 'negative': int(len(ix)-y[ix].sum())}
              for name,ix in [('train',train),('validation',valid),('test',test)]}
    df = pd.DataFrame(career)
    if df.empty:
        raise ValueError('No healthcare analyst postings matched the declared scope')
    skills = Counter()
    malformed_skills = 0
    skills_observed = 0
    for value in df.SKILLS_NAME:
        try:
            items = json.loads(clean(value) or '[]')
            if not isinstance(items,list):
                raise ValueError('Expected list')
            items = {str(x).strip() for x in items if str(x).strip()}
            skills.update(items)
            skills_observed += bool(items)
        except (ValueError, TypeError):
            malformed_skills += 1
    skills_table = pd.DataFrame([{'skill':s,'postings':c,'share_all_scope_postings':c/len(df)} for s,c in skills.most_common()])
    skills_table.to_csv(OUT/'market_skills.csv', index=False)
    counts = {}
    df['STATE_NAME'] = df.STATE_NAME.map(lambda v: STATE_MAP.get(clean(v).upper(), 'Unknown or non-state'))
    df['REMOTE_TYPE_NAME'] = df.REMOTE_TYPE_NAME.map(lambda v: {'remote':'Remote','hybrid':'Hybrid','onsite':'Onsite','on-site':'Onsite'}.get(clean(v).lower(), 'Unknown'))
    for key,column in [('roles','TITLE_NAME'),('states','STATE_NAME'),('remote','REMOTE_TYPE_NAME')]:
        count = df[column].map(lambda v: clean(v) or 'Unknown').value_counts()
        count.rename_axis(key).reset_index(name='postings').to_csv(OUT/f'{key}.csv',index=False)
        counts[key] = {str(k):int(v) for k,v in count.items()}
    exp = pd.to_numeric(df.MIN_YEARS_EXPERIENCE, errors='coerce')
    exp = exp.where(exp >= 0)
    salary = pd.to_numeric(df.NORMALIZED_SALARY, errors='coerce')
    salary = salary.where((df.TEXT_PAY_CURRENCY == 'USD') & (salary > 0) & np.isfinite(salary))
    dates = pd.to_datetime(df.POSTED, errors='coerce', utc=True, format='mixed')
    summary = {'postings': len(df), 'date_min': str(dates.min()), 'date_max': str(dates.max()),
               'unknown_dates': int(dates.isna().sum()), 'salary_usd_observed': int(salary.notna().sum()),
               'salary_usd_median': None if salary.notna().sum()==0 else float(salary.median()),
               'salary_usd_q25': None if salary.notna().sum()==0 else float(salary.quantile(.25)),
               'salary_usd_q75': None if salary.notna().sum()==0 else float(salary.quantile(.75)),
               'salary_statuses': {str(k):int(v) for k,v in df.SALARY_NORMALIZATION_STATUS.fillna('Unknown').value_counts().items()},
               'experience_observed': int(exp.notna().sum()), 'experience_median': float(exp.median()) if exp.notna().any() else None,
               'entry_0_to_2_years': int(exp.between(0,2).sum()), 'skills_observed': skills_observed,
               'malformed_skill_rows': malformed_skills, 'counts': counts}
    pd.DataFrame([summary | {'counts': json.dumps(counts), 'salary_statuses':json.dumps(summary['salary_statuses'])}]).to_csv(OUT/'career_benchmark_table.csv', index=False)
    bar_chart(list(counts['states'])[:10],list(counts['states'].values())[:10], 'Healthcare analyst postings by state','Postings in the selected sample','states.png')
    bar_chart(list(counts['remote']),list(counts['remote'].values()), 'Reported work arrangement','Postings in the selected sample','remote.png')
    top_skills = skills.most_common(12)
    bar_chart([s for s,c in top_skills],[c for s,c in top_skills], 'Most frequently listed skills','Postings mentioning skill; missing skills retained in denominator','skills.png')
    fig, axes = plt.subplots(1,2,figsize=(9,4))
    for ax, result in zip(axes, model_results[:2]):
        matrix = np.array(result['confusion_matrix'])
        ax.imshow(matrix,cmap='Blues')
        for i in range(2):
            for j in range(2):
                ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>matrix.max()/2 else '#102b3f')
        ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Other','NAICS 62'],yticklabels=['Other','NAICS 62'],xlabel='Predicted',ylabel='Dataset label',title=result['model'])
    fig.tight_layout(); fig.savefig(FIG/'confusion.png'); plt.close(fig)
    run = {'seed':2017,'period':['2026-01-01','2026-09-30'],'minimum_label_share':args.minimum_label_share,'versions':{'python':platform.python_version(),'pandas':pd.__version__,'pyarrow':pyarrow.__version__,'sklearn':sklearn.__version__},
           'files':manifests,'ledger':dict(ledger),'role_regex':ROLE.pattern,'splits':splits,
           'features':{'titles':len(titles),'name_words':len(words),'matrix_columns':X.shape[1], 'title_thresholds':title_thresholds,'name_thresholds':name_thresholds},
           'models':model_results,'career':summary,'employer_overlap':0}
    (OUT/'run.json').write_text(json.dumps(run,indent=2,allow_nan=False),encoding='utf-8')
    print('STUDY COMPLETE',json.dumps({'ledger':dict(ledger),'splits':splits,'career_postings':len(df)}),flush=True)

if __name__ == '__main__':
    main()
