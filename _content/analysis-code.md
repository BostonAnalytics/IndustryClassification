## publish_eda.py

[Download source](scripts/publish_eda.py)

````python
"""Publish descriptive EDA from existing aggregates, without accessing raw records."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/study'
FIG = ROOT / 'images'


def write_csv(name, rows):
    with (OUT / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def bars(labels, values, title, xlabel, filename, annotations, percent=False):
    fig, ax = plt.subplots(figsize=(9, max(3.4, len(labels) * .43 + 1.5)))
    positions = list(range(len(labels)))
    ax.barh(positions, values, color='#087e8b', height=.64)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    for pos, value, label in zip(positions, values, annotations):
        ax.annotate(label, (value, pos), xytext=(5, 0), textcoords='offset points', va='center', fontsize=9)
    ax.set_xlim(0, 125 if percent else max(values) * 1.25)
    if percent:
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.xaxis.set_major_formatter(PercentFormatter())
    ax.set_title(title, loc='left', pad=18, fontweight='bold')
    ax.set_xlabel(xlabel)
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='x', alpha=.15)
    fig.tight_layout()
    fig.savefig(FIG / filename, dpi=180, bbox_inches='tight')
    plt.close(fig)


def main():
    d = json.loads((OUT / 'run.json').read_text(encoding='utf-8'))
    c, ledger = d['career'], d['ledger']
    n = c['postings']
    assert n > 0
    stages = [('Source records', 'source_rows'), ('Jan–Sep 2026', 'period_rows'),
              ('Explicit US country', 'us_rows'), ('Recognized industry', 'sector_known_rows'),
              ('Not flagged staffing', 'nonstaffing_or_unknown_rows')]
    selection = [{'stage': label, 'postings': ledger[key],
                  'share_source': ledger[key] / ledger['source_rows']} for label, key in stages]
    write_csv('eda_selection.csv', selection)
    bars([r['stage'] for r in selection], [100*r['share_source'] for r in selection],
         'Sample selection before the career and employer branches', 'Share of all source records',
         'eda-selection.png', [f"{r['postings']:,}" for r in selection], percent=True)

    coverage = [('Nonempty skills', c['skills_observed']),
                ('Recognized state', n-c['counts']['states'].get('Unknown or non-state', 0)),
                ('Nonnegative experience', c['experience_observed']),
                ('Known work arrangement', n-c['counts']['remote'].get('Unknown', 0)),
                ('Positive salary + USD', c['salary_usd_observed'])]
    coverage_rows = [{'field': label, 'observed': count, 'unavailable': n-count,
                      'denominator': n, 'share_observed': count/n} for label, count in coverage]
    write_csv('eda_coverage.csv', coverage_rows)
    bars([r['field'] for r in coverage_rows], [100*r['share_observed'] for r in coverage_rows],
         f'Coverage of career evidence ({n} selected postings)', 'Share meeting each availability rule',
         'eda-coverage.png', [f"{r['observed']}/{n} ({r['share_observed']:.1%})" for r in coverage_rows], percent=True)

    roles = sorted(c['counts']['roles'].items(), key=lambda item: (-item[1], item[0]))
    top = roles[:8]
    role_rows = [{'role': label, 'postings': count, 'share_all_postings': count/n} for label, count in top]
    write_csv('eda_roles.csv', role_rows)
    bars([r['role'] for r in role_rows], [r['postings'] for r in role_rows],
         'Most frequent supplied normalized role labels', 'Selected postings (top eight labels only)',
         'eda-roles.png', [str(r['postings']) for r in role_rows])

    with (OUT / 'market_skills.csv').open(encoding='utf-8', newline='') as handle:
        skills = sorted(csv.DictReader(handle), key=lambda r: (-int(r['postings']), r['skill']))[:10]
    skill_rows = [{'skill': r['skill'], 'postings': int(r['postings']),
                   'share_all_postings': int(r['postings'])/n,
                   'share_with_skills': int(r['postings'])/c['skills_observed']} for r in skills]
    write_csv('eda_skills.csv', skill_rows)
    bars([r['skill'] for r in skill_rows], [100*r['share_all_postings'] for r in skill_rows],
         'Most frequently listed skills', f'Share of all {n} selected postings; skills can overlap',
         'eda-skills.png', [f"{r['postings']} ({r['share_all_postings']:.1%})" for r in skill_rows], percent=True)

    coverage_table = '\n'.join(f"| {r['field']} | {r['observed']} | {r['unavailable']} | {r['share_observed']:.1%} |" for r in coverage_rows)
    sql = next(r for r in skill_rows if r['skill'] == 'SQL (Programming Language)')
    text = f'''## Exploratory data analysis

This descriptive analysis uses the saved Jobs_2026_US aggregates [@jobs2026]. It examines selection, available career evidence, normalized role labels and skills before interpreting the predictive results. All career percentages use the {n} selected postings unless another denominator is stated. Figures describe recorded advertisements, not live vacancies or population employment.

### Selection and units of analysis

![Sequential posting filters before industry-and-title career selection or employer aggregation. Bar lengths use all {ledger['source_rows']:,} source records as the denominator; labels give retained counts.](images/eda-selection.png){{#fig-eda-selection fig-alt="Five horizontal bars show the number of records retained through date, country, industry and staffing filters." width=95%}}

The common filters retain {ledger['nonstaffing_or_unknown_rows']:,} of {ledger['source_rows']:,} records ({ledger['nonstaffing_or_unknown_rows']/ledger['source_rows']:.1%}). The explicit-US filter removes {ledger.get('non_us_or_unknown_country', 0):,} dated records; unknown country and non-US country are combined in the saved exclusion count. These exclusions describe selection, not proof that every excluded record is erroneous. The pipeline then branches: industry-and-title matching yields {n} career postings, while employer aggregation and eligibility rules yield {ledger['model_employers']} employers for classification. Those are different units and should not appear as consecutive steps in a single funnel.

### Field coverage and missing evidence

![Availability of five career fields, with a common denominator of {n} postings. A positive salary with explicit USD passes the availability rule but is not independently validated compensation.](images/eda-coverage.png){{#fig-eda-coverage fig-alt="Skills have the highest field coverage and explicit USD salary has the lowest; counts and percentages are printed beside each bar." width=95%}}

| Evidence rule | Observed | Unavailable under rule | Coverage |
|---|---:|---:|---:|
{coverage_table}

Availability is field-specific: unavailable can mean missing, unrecognized or excluded by a validity rule. The fields can be missing in the same posting; these counts cannot be added to estimate incomplete records. Salary coverage supports withholding a distribution plot or salary ranking. Recorded experience values require review against requirement text, even when nonnegative.

### Role-label consistency

![Eight most frequent supplied TITLE_NAME labels in the career subset; ties are ordered alphabetically. Labels are reproduced for a data-quality check.](images/eda-roles.png){{#fig-eda-roles fig-alt="Normalized labels include Data Scientists, Senior Data Analyst, Management Analysts and the unexpected label Actors." width=95%}}

The saved table contains {len(roles)} distinct labels. The eight shown account for {sum(count for _, count in top)} of {n} postings; the other {len(roles)-len(top)} labels account for {n-sum(count for _, count in top)}. The career filter matches raw titles, with clean titles as fallback, whereas this chart uses supplied normalized titles. Labels such as Actors therefore signal records to inspect for disagreement; they do not establish that acting is a healthcare analytics pathway. Counts alone cannot determine whether the raw title, normalization or industry assignment is wrong. No records were relabeled or removed based on this plot.

### Skill frequencies and denominators

![Ten most frequently listed skills as percentages of all selected postings. Multiple skills can occur in one posting, so percentages need not sum to 100.](images/eda-skills.png){{#fig-eda-skills fig-alt="SQL is the most frequently listed skill, followed by Tableau; each bar shows a posting count and percentage." width=95%}}

SQL appears in {sql['postings']} postings: {sql['share_all_postings']:.1%} of all {n}, or {sql['share_with_skills']:.1%} of the {c['skills_observed']} with nonempty skill lists. Keeping the {n-c['skills_observed']} postings without skill lists in the primary denominator makes the coverage boundary visible. A missing list does not imply that a role requires no skills. These are marginal frequencies; no skill co-occurrence, correlations or causal training effects can be recovered from these aggregate tables.

### Interpretation and reproducibility

The sample provides stronger descriptive support for skill priorities than for compensation advice. Work-arrangement and state summaries below retain their unknown categories. Temporal trends, salary-by-location comparisons and multivariable EDA require additional row-level summaries; the saved aggregates cannot establish those relationships.

Run `python scripts/publish_eda.py` to regenerate these figures and tables from `run.json` and `market_skills.csv`, without refitting models. Download [selection counts](data/study/eda_selection.csv), [coverage](data/study/eda_coverage.csv), [role labels](data/study/eda_roles.csv) and [skill shares](data/study/eda_skills.csv). Input hashes are recorded in [the EDA manifest](data/study/eda_manifest.json).
'''
    (ROOT / '_content/eda-results.md').write_text(text, encoding='utf-8')
    manifest = {'inputs': {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest()
                            for name in ['run.json', 'market_skills.csv']},
                'matplotlib': matplotlib.__version__, 'career_denominator': n,
                'figures': ['eda-selection.png', 'eda-coverage.png', 'eda-roles.png', 'eda-skills.png']}
    (OUT/'eda_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('EDA PUBLISHED: four figures and four source tables')


if __name__ == '__main__':
    main()

````

## publish_interactive.py

[Download source](scripts/publish_interactive.py)

````python
"""Export browser-ready charts, tables and visible code from saved aggregates only."""
import csv
import hashlib
import html
import json
from pathlib import Path

import plotly
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'images/interactive'
OUT = ROOT / 'data/interactive'
INPUTS = {}


def rows(name):
    path = ROOT / name
    INPUTS[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def export(fig, name, title):
    fig.update_layout(template='plotly_white', title=title, font_size=14,
                      margin=dict(l=65, r=30, t=90, b=70), height=520)
    fig.write_json(OUT / f'{name}.json')
    fig.write_html(FIG / f'{name}.html', include_plotlyjs='directory',
                   div_id=name, config={'responsive': True, 'displaylogo': False,
                                        'topojsonURL': './'})
    return f'''\n### {title}

<iframe src="images/interactive/{name}.html" title="{html.escape(title)}" width="100%" height="550" loading="lazy" style="border:0"></iframe>

[Open chart](images/interactive/{name}.html) · [Download figure data](data/interactive/{name}.json)
'''


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ('data/multiclass/run.json', '_content/multiclass-results.md', 'images/multiclass-confusion.png'):
        INPUTS[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    # Always refresh the shared bundle when the local Plotly version changes.
    (FIG / 'plotly.min.js').write_text(get_plotlyjs(), encoding='utf-8')
    assert (FIG / 'usa_110m.json').is_file(), 'US geometry must be present before exporting'
    parts = ['## Interactive charts\n']
    months = sorted(rows('data/eda/posted_month.csv'), key=lambda r: r['value'])
    fig = go.Figure(go.Bar(x=[r['value'] for r in months], y=[int(r['rows']) for r in months],
                          marker_color='#087e8b'))
    fig.update_layout(yaxis_title='Source records', xaxis_title='Posting month', xaxis_type='category')
    parts.append(export(fig, 'months', 'Posting months · full source snapshot'))
    parts.append('All source records, including dates outside the January–September study window. Counts are advertisements, not employment estimates.\n')
    skills = rows('data/study/eda_skills.csv')[::-1]
    fig = go.Figure(go.Bar(x=[int(r['postings']) for r in skills], y=[r['skill'] for r in skills],
                          orientation='h', marker_color='#087e8b'))
    fig.update_layout(xaxis_title='Selected career postings (skills may overlap)', yaxis_automargin=True)
    parts.append(export(fig, 'skills', 'Most listed skills · healthcare career cohort'))
    parts.append('The denominator is the full selected career cohort; missing skill lists remain in that denominator.\n')
    states = rows('data/eda/state.csv')
    names = 'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|')
    codes = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
    mapping = dict(zip(names, codes))
    located = [r for r in states if r['value'] in mapping]
    unknown = sum(int(r['rows']) for r in states if r['value'] not in mapping)
    fig = go.Figure(go.Choropleth(locations=[mapping[r['value']] for r in located],
        z=[int(r['rows']) for r in located], text=[r['value'] for r in located],
        locationmode='USA-states', colorscale='Teal', colorbar_title='Records',
        hovertemplate='%{text}: %{z:,} records<extra></extra>'))
    fig.update_geos(scope='usa')
    parts.append(export(fig, 'states', 'US posting locations · full source snapshot'))
    parts.append(f'{unknown:,} missing or unrecognized state records are excluded from the map and retained in the source table. Colors show raw counts, not population-adjusted rates.\n')
    parts.append('## Searchable aggregate tables\n\nFilter any table by typing. CSV downloads preserve the complete table. Source-wide, career-cohort and historical comparison tables retain their separate folders and denominators.\n')
    for index, path in enumerate(sorted((ROOT / 'data').rglob('*.csv'))):
        name = path.relative_to(ROOT).as_posix()
        table = rows(name)
        if not table:
            continue
        fields = list(table[0])
        header = ''.join(f'<th scope="col">{html.escape(key)}</th>' for key in fields)
        body = ''.join('<tr>' + ''.join(f'<td>{html.escape(row[key])}</td>' for key in fields) + '</tr>' for row in table)
        # A standalone HTML table is also a portable export, usable outside Quarto.
        markup = f'<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'
        filename = name.removeprefix('data/').replace('/', '-').removesuffix('.csv') + '.html'
        (OUT / filename).write_text('<!doctype html><meta charset="utf-8"><title>' + html.escape(name) + '</title>' + markup, encoding='utf-8')
        parts.append(f'\n### {name}\n\n[CSV]({name}) · [HTML table](data/interactive/{filename})\n\n'
                     f'<label for="filter-{index}">Filter {html.escape(name)}</label>\n'
                     f'<input id="filter-{index}" type="search" class="aggregate-filter" data-table="table-{index}">\n'
                     f'<div id="table-{index}" class="aggregate-table">{markup}</div>\n')
    parts.append('''
<script>
document.querySelectorAll('.aggregate-filter').forEach(input => {
  input.addEventListener('input', () => {
    const query = input.value.toLocaleLowerCase();
    document.querySelectorAll('#' + input.dataset.table + ' tbody tr').forEach(row => {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
    });
  });
});
</script>
''')
    (ROOT / '_content/interactive-results.md').write_text('\n'.join(parts), encoding='utf-8')
    code = []
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        name = path.relative_to(ROOT).as_posix()
        INPUTS[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        code.append(f'## {path.name}\n\n[Download source]({name})\n\n````python\n{path.read_text(encoding="utf-8")}\n````\n')
    (ROOT / '_content/analysis-code.md').write_text('\n'.join(code), encoding='utf-8')
    assets = sorted([*FIG.glob('*'), *OUT.glob('*'), ROOT / '_content/interactive-results.md', ROOT / '_content/analysis-code.md'])
    manifest = {'plotly': plotly.__version__, 'inputs': INPUTS,
                'geometry_source': 'https://cdn.plot.ly/un/usa_110m.json',
                'outputs': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in assets if p.name != 'manifest.json'}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('INTERACTIVE EXPORTED: charts, map, searchable tables and complete source')


if __name__ == '__main__':
    main()

````

## publish_multiclass.py

[Download source](scripts/publish_multiclass.py)

````python
"""Publish the additional experiment from saved aggregates, without source access."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/multiclass'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join('---' for _ in headers) + '|'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]) + '\n'


def main():
    d = json.loads((OUT / 'run.json').read_text(encoding='utf-8'))
    support, classes = d['class_support'], d['classes']
    selected = next(m for m in d['models'] if m['model'] == d['selected_model'])
    metrics, per_class, confusion = [], [], []
    for m in d['models']:
        report = m['test_report']
        metrics.append({'model': m['model'], 'validation_macro_f1': m.get('validation_macro_f1'),
                        'test_macro_f1': report['macro avg']['f1-score'],
                        'test_weighted_f1': report['weighted avg']['f1-score'],
                        'test_accuracy': m['accuracy'], 'test_balanced_accuracy': report['macro avg']['recall']})
        for i, sector in enumerate(classes):
            per_class.append({'model': m['model'], 'sector': sector, **report[sector]})
            for j, predicted in enumerate(classes):
                confusion.append({'model': m['model'], 'actual_sector': sector, 'predicted_sector': predicted,
                                  'employers': m['confusion_matrix'][i][j]})
    for name, rows in [('metrics', metrics), ('per_class', per_class), ('confusion', confusion)]:
        pd.DataFrame(rows).to_csv(OUT / f'{name}.csv', index=False)
    cm = np.array(selected['confusion_matrix'])
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(cm / cm.sum(axis=1, keepdims=True), cmap='Blues', vmin=0, vmax=1)
    ax.set(xticks=range(len(classes)), yticks=range(len(classes)), xticklabels=classes,
           yticklabels=classes, xlabel='Predicted NAICS sector', ylabel='Dataset-derived NAICS sector',
           title=f'{selected["model"]}: test employer counts')
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, str(cm[i, j]), ha='center', va='center',
                    color='white' if cm[i, j] / cm[i].sum() > .5 else 'black')
    fig.tight_layout()
    fig.savefig(ROOT / 'images/multiclass-confusion.png', dpi=180)
    plt.close(fig)
    baseline = metrics[-1]['test_macro_f1']
    excluded = [r for r in support if not r['included']]
    included = [r for r in support if r['included']]
    result = selected['test_report']
    comparison = d['comparison_with_saved_binary']
    provenance = ('Source file hashes match the saved healthcare experiment.' if comparison['exact_snapshot_match'] else
                  f"Source file hashes differ from the saved healthcare experiment in {comparison['changed_partition_hashes']} partitions. "
                  'The current dataset documents a NAICS hierarchy repair, while the healthcare results retain their earlier input manifest. '
                  'Equal row counts do not establish an identical snapshot; this extension is evaluated separately.')
    text = f'''## Multiclass industry classification

The additional experiment predicts one broad NAICS sector per employer. It extends the employer-name and job-title feature design in @goindani2017 beyond separate industry-membership questions. The healthcare career benchmark and the binary experiments retain their original scope.

### Sector definitions and coverage

The input contains {d['ledger']['source_rows']:,} records in {len(d['files'])} Jobs_2026_US partitions. {provenance} The January–September 2026, US, staffing, employer-name and normalized-title filters apply before employer aggregation. Codes 31, 32 and 33 map to manufacturing (31–33); 44 and 45 to retail trade (44–45); and 48 and 49 to transportation and warehousing (48–49). These mappings change {d['ledger']['sector_normalized_rows']:,} posting labels in the current input, which already uses combined sectors, before computing employer dominance. Missing and invalid sectors are excluded, not treated as a learnable industry.

Employers require at least 20 retained postings and an 80% dominant-sector share. After normalization, {d['ledger']['eligible_employers']:,} employers satisfy these rules. A sector requires at least {d['minimum_class_employers']} eligible employers to enter the experiment. This support rule retains {len(classes)} sectors and {d['ledger']['model_employers']:,} employers; {d['ledger']['excluded_low_support_employers']} eligible employers belong to sectors below the threshold. There is no employer cap. Labels describe broad sectors and remain unadjudicated dataset labels.

'''
    text += table(['NAICS', 'Industry', 'Employers'], [[r['sector'], r['industry'], r['eligible_employers']] for r in included])
    text += '\nExcluded sectors (eligible employer counts): ' + '; '.join(f'{r["sector"]} {r["industry"]} ({r["eligible_employers"]})' for r in excluded) + '.\n'
    text += '''
### Employer partitions and features

Within each retained class, employers are ordered by SHA-256 of the seed 2017 and normalized employer name. The first floor(70%) form training, the next employers up to floor(80%) form validation, and the remainder form testing. Each employer belongs to exactly one partition. Normalized names do not resolve corporate aliases, so related entities may still cross partitions. The class-support rule is set before feature fitting; it uses label counts to define the study population.

'''
    text += table(['NAICS', 'Train', 'Validation', 'Test'], [[r['sector'], r['train'], r['validation'], r['test']] for r in included])
    text += f'''
The partitions contain {d['splits']['train']} training, {d['splits']['validation']} validation and {d['splits']['test']} test employers. For each class, title and employer-word significance/frequency thresholds are calculated against the other training classes; the union of those selected vocabularies supplies {d['features']['count']} features. This replaces the healthcare-only positive-class feature selection. Titles retain the 1% within-employer share cutoff. Validation and test employers contribute neither vocabulary nor thresholds. Zero-feature employers remain in evaluation: {d['features']['zero_vectors_by_split']['train']} training, {d['features']['zero_vectors_by_split']['validation']} validation and {d['features']['zero_vectors_by_split']['test']} test.

### Model selection and held-out results

Scikit-learn implementations [@pedregosa2011] compare linear SVM, logistic regression, random forest and multiclass GBDT on identical partitions. SVM and logistic regression search C = 0.1, 1 and 10 with balanced class weights; random forest uses 200 trees and maximum depths 5 or unrestricted with balanced class weights; GBDT uses 100 boosting stages and tree depths 2 or 3 with default learning rate 0.1. GBDT uses unweighted training. Random states are fixed at 2017. Hyperparameters and then the model family are selected by validation macro-F1, with ties resolved by the listed order. Models are not refitted on validation data. The baseline always predicts the most frequent training class.

Macro-F1 gives each retained sector equal weight. Weighted-F1 and accuracy describe the observed test mix; balanced accuracy averages sector recall. Zero-denominator precision or F1 is recorded as zero. The validation-selected model is {selected['model']}, with test macro-F1 {result['macro avg']['f1-score']:.3f}, compared with {baseline:.3f} for the training-majority baseline. This is a separate endpoint from healthcare-positive F1, so scores cannot be read as a direct improvement over the binary experiment.

'''
    text += table(['Model', 'Valid. macro-F1', 'Test macro-F1', 'Weighted-F1', 'Accuracy', 'Bal. accuracy'],
                  [[r['model'], '—' if r['validation_macro_f1'] is None else f'{r["validation_macro_f1"]:.3f}',
                    *[f'{r[k]:.3f}' for k in ('test_macro_f1', 'test_weighted_f1', 'test_accuracy', 'test_balanced_accuracy')]] for r in metrics])
    text += f'\nPer-sector test results for the validation-selected {selected["model"]}:\n\n'
    text += table(['NAICS', 'Precision', 'Recall', 'F1', 'Test employers'],
                  [[s, *[f'{result[s][k]:.3f}' for k in ('precision', 'recall', 'f1-score')], int(result[s]['support'])] for s in classes])
    missed = [s for s in classes if result[s]['recall'] == 0]
    if missed:
        text += '\nThe selected model recovered no test employers in sector(s) ' + ', '.join(missed) + '. This limits its use for filtering those industries.\n'
    text += '''
![Confusion matrix for the validation-selected model. Cells show employer counts; color is normalized within each actual-sector row. Sector names appear in the coverage table.](images/multiclass-confusion.png){width=85%}

### Interpretation and limits

This experiment measures agreement across the supported broad industries. The predictions cover only retained sectors: an employer from an excluded sector would still be forced into one of these classes. No open-set detection or deployment inference is claimed. Rare sectors remain in the coverage report instead of being merged into an incoherent “other” class. The two-employer minimum validation support makes tuning sensitive to individual cases, and this single split does not establish stable sector-level performance. Independent label review, repeated employer-grouped evaluation and a later-period test remain necessary. Missing industry labels limit population coverage, and the results do not establish national hiring patterns.

The multiclass results do not replace the 112-posting healthcare career analysis or support personal skill-gap scores. Aggregate class support, metrics, per-sector results and all model confusion matrices accompany the source and run manifest.
'''
    (ROOT / '_content/multiclass-results.md').write_text(text, encoding='utf-8')
    print('MULTICLASS PUBLISHED: shared report section, four CSVs and confusion figure')


if __name__ == '__main__':
    main()

````

## publish_sample.py

[Download source](scripts/publish_sample.py)

````python
"""Execute the website's visible sample chunks; publish aggregate outputs only."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]

# Each string is both executed and displayed, so outputs cannot drift from code.
CHUNKS = [
    ('preparation', 'Load a reproducible posting sample', '''
from pathlib import Path
from collections import Counter
import hashlib
import json
import pandas as pd
import pyarrow.parquet as pq
from run_study import COLS, KNOWN_SECTORS, ROLE, clean

sample_fraction = 0.10
seed = 2017
files = sorted(data_dir.glob('jobs_2026_part_*.parquet'))
if not files:
    raise ValueError('No Jobs_2026_US posting partitions found')
parts, inputs = [], []
source_rows = 0
def selected(identifier):
    if pd.isna(identifier):
        return False
    key = f'{seed}:{identifier}'.encode('utf-8')
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big')
    return not sample or bucket < int(sample_fraction * 2**64)

for path in files:
    parquet = pq.ParquetFile(path)
    inputs.append({'file': path.name, 'rows': parquet.metadata.num_rows})
    for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
        frame = batch.to_pandas()
        source_rows += len(frame)
        parts.append(frame.loc[frame.ID.map(selected)])
jobs = pd.concat(parts, ignore_index=True)
sampled_rows = len(jobs)
jobs = jobs.drop_duplicates('ID', keep='first').copy()
print(f'sample={str(sample).lower()}, fraction={sample_fraction if sample else 1}, seed={seed}')
print(f'Partitions scanned: {len(files):,}; source rows: {source_rows:,}')
print(f'Selected rows: {sampled_rows:,}; unique posting IDs: {len(jobs):,}')
print('Schema preview (first 6 columns):')
print(jobs.dtypes.head(6).to_string())
'''),
    ('preparation', 'Apply the study filters', '''
ledger = {'sample_unique_ids': len(jobs)}
dates = pd.to_datetime(jobs.POSTED, errors='coerce', utc=True, format='mixed')
jobs = jobs.loc[(dates >= '2026-01-01') & (dates < '2026-10-01')].copy()
ledger['January–September 2026'] = len(jobs)
jobs = jobs.loc[jobs.PARSED_COUNTRY_ISO_ABBR.map(clean).str.upper().eq('US')].copy()
ledger['US'] = len(jobs)
jobs['sector'] = jobs.NAICS_2022_2.map(clean)
jobs['sector'] = jobs.sector.where(jobs.sector.ne(''), jobs.NAICS2.map(clean))
jobs = jobs.loc[jobs.sector.isin(KNOWN_SECTORS)].copy()
ledger['recognized sector'] = len(jobs)
jobs = jobs.loc[~jobs.COMPANY_IS_STAFFING.eq(1)].copy()
ledger['nonstaffing or unknown'] = len(jobs)
titles = jobs.TITLE_RAW.map(clean)
titles = titles.where(titles.ne(''), jobs.TITLE_CLEAN.map(clean))
career = jobs.loc[jobs.sector.eq('62') & titles.map(lambda title: bool(ROLE.search(title)))].copy()
ledger['healthcare analyst cohort'] = len(career)
print(pd.Series(ledger, name='Postings').to_string())
'''),
    ('market', 'Inspect coverage and work arrangements', '''
from run_study import STATE_MAP
import numpy as np

states = career.STATE_NAME.map(lambda value: STATE_MAP.get(clean(value).upper(), 'Unknown'))
remote = career.REMOTE_TYPE_NAME.map(lambda value: {
    'remote': 'Remote', 'hybrid': 'Hybrid', 'onsite': 'Onsite', 'on-site': 'Onsite'
}.get(clean(value).lower(), 'Unknown'))
salary = pd.to_numeric(career.NORMALIZED_SALARY, errors='coerce')
salary = salary.where(career.TEXT_PAY_CURRENCY.eq('USD') & salary.gt(0) & np.isfinite(salary))
experience = pd.to_numeric(career.MIN_YEARS_EXPERIENCE, errors='coerce')
coverage = pd.Series({'cohort postings': len(career), 'recognized state': states.ne('Unknown').sum(),
    'known work arrangement': remote.ne('Unknown').sum(), 'positive USD salary': salary.notna().sum(),
    'nonnegative experience': experience.ge(0).sum()}, name='Postings')
print(coverage.to_string())
print('Work arrangement counts:')
print(remote.value_counts().to_string())
print('State counts (first 5):')
print(states.value_counts().head(5).to_string())
'''),
    ('skills', 'Decode skills and calculate posting shares', '''
skills = Counter()
malformed = 0
for value in career.SKILLS_NAME:
    try:
        items = json.loads(clean(value) or '[]')
        if not isinstance(items, list):
            raise ValueError('Expected a skill list')
        skills.update({str(item).strip() for item in items if str(item).strip()})
    except (ValueError, TypeError):
        malformed += 1
skills_table = pd.DataFrame([
    {'skill': skill, 'postings': count, 'share': round(count / len(career), 4)}
    for skill, count in sorted(skills.items(), key=lambda item: (-item[1], item[0]))
], columns=['skill', 'postings', 'share'])
print(f'Denominator: {len(career)} cohort postings; malformed skill lists: {malformed}')
print(skills_table.head(10).to_string(index=False))
'''),
    ('evaluation', 'Check sample support before model fitting', '''
# Apply the existing employer eligibility rules to the sampled postings.
import re
employers = {}
for row in jobs.to_dict('records'):
    name = re.sub(r'\\s+', ' ', clean(row['COMPANY_NAME']).casefold())
    title = clean(row['TITLE_NAME']).casefold()
    if not name or name in ('unknown', 'unclassified') or not title or title == 'unclassified':
        continue
    employers.setdefault(name, Counter()).update([row['sector']])
eligible = [counts for counts in employers.values()
            if counts.total() >= 20 and counts.most_common(1)[0][1] / counts.total() >= .8]
support = Counter(int(counts.most_common(1)[0][0] == '62') for counts in eligible)
print(f'Eligible employers in this sample: {len(eligible)}')
print(f'Healthcare: {support[1]}; other sectors: {support[0]}')
print(f'Minimum split support met: {len(eligible) >= 50 and min(support[0], support[1]) >= 10}')
print('No classifier is fitted in this sample walkthrough.')
print('The model metrics below belong to the separate full-study run.')
'''),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--sample', choices=['true', 'false'], default='true')
    args = parser.parse_args()
    namespace = {'data_dir': args.data_dir, 'sample': args.sample == 'true'}
    pages = {}
    records = []
    for page, title, source in CHUNKS:
        code = textwrap.dedent(source).strip()
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exec(compile(code, f'<sample:{title}>', 'exec'), namespace)
        output = capture.getvalue().rstrip()
        records.append({'page': page, 'title': title, 'code': code, 'output': output})
        pages.setdefault(page, []).append(f'### {title}\n\n```python\n{code}\n```\n\nPartial output (computed from this run):\n\n```text\n{output}\n```\n')
    for page, sections in pages.items():
        intro = ('## Executed sample: code and partial output\n\n'
                 f'This walkthrough uses `sample={args.sample}` on the local Jobs_2026_US partitions. '
                 'With sampling enabled, SHA-256 of seed 2017 and posting ID selects approximately 10% of IDs across all partitions; '
                 'missing IDs are excluded and duplicates keep their first occurrence. This scans every partition but retains only selected rows. '
                 'These descriptive sample results are separate from the full-study tables below. '
                 'Code is shown expanded; outputs are captured from that exact code by '
                 '`scripts/publish_sample.py`. Only aggregates and a schema preview are published. '
                 'Run chunks in page order: preparation, market, skills, evaluation.\n\n')
        if page == 'preparation':
            intro += (f'Run from the repository root: `python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026_US --sample={args.sample}`, then `quarto render`. '
                      'For interactive execution, add `scripts` to `sys.path`, set `data_dir = Path("E:/Data/Jobs_2026_US")` '
                      f'and `sample = {namespace["sample"]}` before the first chunk.\n\n')
        (ROOT / '_content' / f'sample-{page}.md').write_text(intro + '\n'.join(sections), encoding='utf-8')
    result = {'source_directory': args.data_dir.resolve().as_posix(), 'sample': namespace['sample'], 'fraction': .1 if namespace['sample'] else 1,
              'seed': 2017, 'source_rows': namespace['source_rows'], 'sampled_rows': namespace['sampled_rows'],
              'inputs': namespace['inputs'], 'ledger': namespace['ledger'], 'chunks': records,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out = ROOT / 'data' / 'sample'
    out.mkdir(exist_ok=True)
    (out / 'run.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'SAMPLE PUBLISHED: {result["sampled_rows"]:,} sampled rows; {len(namespace["career"])} career postings')


if __name__ == '__main__':
    main()

````

## publish_spark_teaching.py

[Download source](scripts/publish_spark_teaching.py)

````python
"""Publish executable source excerpts and a notebook from one PySpark script."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'scripts/run_spark_study.py').read_text(encoding='utf-8')
tree = ast.parse(source)
functions = {n.name: ast.get_source_segment(source, n)
             for n in tree.body if isinstance(n, ast.FunctionDef)}
imports = source[source.index('import argparse'):source.index('def prepare')].strip()
sections = [
    ('Load, clean and filter postings', ['prepare'],
     'The input is a set of Parquet posting partitions. The code selects only the fields needed for employer classification, parses dates in UTC, applies the January–September window, requires US geography and a recognized sector, and excludes explicitly marked staffing records. Missing staffing status is retained. Blank employer names and titles cannot contribute to employer features. Duplicate IDs cause an error rather than an arbitrary choice between conflicting records.'),
    ('Aggregate employers and split before learning features', ['employers_and_splits'],
     'Each employer is one observation. At least 20 usable postings and an 80% dominant-sector share are required. The binary target is 1 for NAICS 62 and 0 for other recognized sectors. Within each class, a seeded hash orders employer keys for a reproducible 70/10/20 split. This prevents one normalized employer key from appearing in both training and test data. Different names for the same organization remain an unresolved source of leakage.'),
    ('Construct title shares and employer-name indicators', ['feature_rows'],
     'A title feature equals its posting count divided by all usable postings for that employer. Name-word features are binary indicators. Industry codes define the target and are excluded from the predictor vector. For example, 30 occurrences of a title among 100 employer postings give a title-share value of 0.30.'),
    ('Fit vocabulary on training employers', ['fit_vocabulary', 'vectorize'],
     'For each candidate, significance is positive-class frequency divided by total training frequency. Candidates need more than one positive occurrence. Median significance and frequency thresholds are applied separately to title and name features; if fewer than 50 survive, the frequency threshold falls to the first quartile. Title shares below 1% are removed. Spark uses exact observed quantiles here, which can differ from NumPy interpolated quantiles. The vocabulary is frozen before validation and test vectors are built. An unseen title contributes no new column. Zero means the employer lacks a selected feature, not that its industry is unknown.'),
    ('Specify the classification algorithms', ['candidates'],
     'The following constructors cover the nine classification families in the Spark DataFrame classification guide [@sparkclassification]. Every model receives the same nonnegative feature vectors. Two parameter settings per family illustrate validation-based selection; this small search does not establish a globally optimal model.'),
    ('Select settings and evaluate held-out employers', ['binary_metrics', 'evaluate'],
     'Only training employers fit model parameters. Validation positive-class F1 selects the first best setting in the declared candidate order. The selected model is tested once without refitting. Confusion matrices use rows for observed labels and columns for predictions: [[TN, FP], [FN, TP]]. Precision is TP/(TP+FP), recall is TP/(TP+FN), and F1 is 2TP/(2TP+FP+FN). Undefined ratios are reported as zero. Accuracy is shown beside F1 because the two answer different questions. The majority baseline is learned from training labels; the all-positive baseline reveals how much recall can be obtained without discrimination.'),
]
intro = '''## Analysis design and execution

The measured SVM and GBDT results elsewhere in this report were produced with scikit-learn. This PySpark implementation is a separate comparison using the same source partitions and employer-level feature concept. Its hash-based split, quantile convention, regularization settings and estimator implementations differ, so its scores must be reported separately. Spark's `regParam` is not substituted directly for scikit-learn's `C`.

The complete [Python script](scripts/run_spark_study.py) and [Jupyter notebook](notebooks/pyspark_classification.ipynb) expose the steps below. The script reads an authorized copy of the source data and writes aggregate results to a separate directory. Source postings are not redistributed. PySpark 4.2.0 is pinned in the repository requirements.

```bash
spark-submit --master local[2] --conf spark.ui.enabled=false scripts/run_spark_study.py --data-dir /path/to/Jobs_2026_US --output-dir data/spark-study
```

## Libraries and feature scope

'''
text = intro + '```python\n' + imports + '\n```\n'
cells = [{'cell_type': 'markdown', 'metadata': {}, 'source': [
    '# Employer classification in PySpark\n',
    'Run on your authorized Jobs_2026_US copy. This notebook generates a separate Spark experiment; published scikit-learn scores are not notebook outputs.\n']}]

def code_cell(code):
    return {'cell_type': 'code', 'metadata': {}, 'execution_count': None,
            'outputs': [], 'source': code.splitlines(keepends=True)}

cells.append(code_cell(imports))
for heading, names, prose in sections:
    text += '\n## ' + heading + '\n\n' + prose + '\n\n'
    cells.append({'cell_type': 'markdown', 'metadata': {},
                  'source': ['## ' + heading + '\n', prose]})
    for name in names:
        text += '```python\n' + functions[name] + '\n```\n\n'
        cells.append(code_cell(functions[name]))

text += '''## What each classifier tests

| Classifier | Role in the comparison | Important constraint |
|---|---|---|
| Logistic regression | Linear probability model | Default prediction threshold is 0.5 |
| Decision tree | A small set of feature splits | Depth limits complexity |
| Random forest | Average over randomized trees | More trees increase computation |
| Gradient-boosted trees | Sequentially improve tree predictions | Spark GBT classification is binary |
| Linear SVM | Maximum-margin linear separation | Binary; balanced training weights; no calibrated probabilities |
| Naive Bayes | Conditional-independence baseline | Multinomial variant needs nonnegative features; title shares are a modeling approximation |
| Multilayer perceptron | Nonlinear neural network | Input width equals feature count; output width equals two classes |
| One-vs-rest logistic | Demonstrate a multiclass reduction | Redundant for this binary task; two logistic classifiers are fitted |
| Factorization machine | Model pairwise feature interactions | More latent factors increase capacity |

Source for available estimator families and constraints: @sparkclassification. The comparison uses the binary healthcare task; it does not claim to test every variant of every estimator or the older RDD API.

## Run the workflow

The entry point connects the stages, prints filtering counts and each model's evaluation, and records versions, settings, split support and input hashes. A failed run does not write a new completed manifest.

'''
text += '```python\n' + functions['main'] + '\n\nif __name__ == "__main__":\n    main()\n```\n'
cells.append(code_cell('''data_dir = Path('/path/to/Jobs_2026_US')
files = sorted(data_dir.glob('jobs_2026_part_*.parquet'))
assert files, 'Set data_dir to an authorized copy of the posting partitions'
spark = (SparkSession.builder.appName('HealthcareClassificationNotebook')
         .config('spark.sql.session.timeZone', 'UTC')
         .config('spark.sql.shuffle.partitions', '4').getOrCreate())
try:
    jobs, ledger = prepare(spark, files)
    print(json.dumps(ledger, indent=2))
    employers, support = employers_and_splits(jobs)
    print(json.dumps(support, indent=2))
    long = feature_rows(jobs, employers).cache()
    vocabulary, thresholds = fit_vocabulary(long)
    matrix = vectorize(long, employers, vocabulary).cache()
    results = evaluate(matrix, len(vocabulary))
    print(json.dumps(results, indent=2))
finally:
    spark.stop()
'''))
run_path = ROOT / 'data/spark-study/run.json'
text += '\n## Spark execution evidence\n\n'
if run_path.exists():
    run = json.loads(run_path.read_text(encoding='utf-8'))
    text += f"The completed PySpark {run['version']} run processed {run['ledger']['source_rows']:,} source rows and fitted {run['feature_count']} feature columns. The [Spark manifest](data/spark-study/run.json) records the inputs, partition sizes, candidate settings and measured results.\n\n"
    text += 'The processing counts below are computed by the Spark functions above.\n\n```text\n'
    text += json.dumps(run['ledger'], indent=2) + '\n```\n\n'
    text += '| Partition | Other employers | NAICS 62 employers |\n|---|---:|---:|\n'
    for split in ['train', 'validation', 'test']:
        counts = {int(r['label']): r['count'] for r in run['splits'] if r['split'] == split}
        text += f"| {split} | {counts[0]} | {counts[1]} |\n"
    text += '\n| Model | Precision (NAICS 62) | Recall | F1 | Accuracy |\n|---|---:|---:|---:|---:|\n'
    for r in run['models']:
        text += f"| {r['model']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | {r['accuracy']:.3f} |\n"
    text += '\nConfusion counts use TN (true negatives), FP (false positives), FN (false negatives) and TP (true positives).\n\n| Model | TN | FP | FN | TP |\n|---|---:|---:|---:|---:|\n'
    for r in run['models']:
        (tn, fp), (fn, tp) = r['confusion_matrix']
        text += f"| {r['model']} | {tn} | {fp} | {fn} | {tp} |\n"
    best = max((r for r in run['models'] if 'validation_f1' in r), key=lambda r: r['validation_f1'])
    text += f"\n{best['model']} achieved the highest validation F1 ({best['validation_f1']:.3f}) in this small search; its held-out F1 was {best['f1']:.3f}. This comparison is exploratory. A single small holdout cannot establish a stable ordering of algorithm families. The counts expose missed healthcare employers and false inclusions that F1 alone obscures. The original scikit-learn and Spark holdouts contain different employers; differences between their scores cannot be attributed solely to the software engine.\n"
    cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': [
        '## Recorded command-line run\n',
        'These aggregate results were generated by the companion script, not by executing the saved notebook cells.\n',
        '```json\n' + json.dumps({'ledger': run['ledger'], 'splits': run['splits'],
            'results': [{k: v for k,v in r.items() if k != 'trials'} for r in run['models']]}, indent=2) + '\n```']})
else:
    text += 'No completed Spark result manifest accompanies this version. The code specifies the experiment; the numerical SVM and GBDT results in the Results section belong to the scikit-learn run.\n'
(ROOT / '_content/spark-walkthrough.md').write_text(text, encoding='utf-8')
(ROOT / 'notebooks').mkdir(exist_ok=True)
(ROOT / 'notebooks/pyspark_classification.ipynb').write_text(json.dumps({
    'cells': cells, 'metadata': {'kernelspec': {'display_name': 'Python 3',
    'language': 'python', 'name': 'python3'}}, 'nbformat': 4, 'nbformat_minor': 5}, indent=2), encoding='utf-8')
print('SPARK TEACHING PUBLISHED')

````

## publish_study.py

[Download source](scripts/publish_study.py)

````python
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
The pipeline read **{ledger['source_rows']:,} rows in {len(d['files'])} posting partitions** from the local snapshot [@jobs2026] and selected January–September 2026 observations. All input files have recorded SHA-256 hashes. No posting ID appeared twice in this input snapshot.

{table(['Filter stage','Remaining postings'],[(label,f"{ledger[key]:,}") for key,label in [('source_rows','All source rows'),('period_rows','Dated January–September 2026'),('us_rows','Parsed country explicitly US'),('sector_known_rows','Valid sector code available'),('nonstaffing_or_unknown_rows','Not explicitly marked as staffing'),('employer_model_postings','Employer name and normalized title available')]])}

Unknown country and unknown sector are exclusions, not negative industry labels. Staffing status that is missing is retained. The date, sector and staffing filters reduce the US-only source, so the retained sample is not representative of all Jobs_2026_US records or all US hiring.

## Employer sample and split

There are {ledger['employers_before_filters']:,} employer-name groups before employer-level filters. Of these, {ledger['employers_below_20']:,} have fewer than 20 eligible postings. A further {ledger['employers_without_dominant_sector']:,} lack a sector covering at least 80% of their postings. The model therefore uses **{ledger['model_employers']:,} employers**, below the paper's 10,000-employer target; {ledger['eligible_exactly_consistent']} have exactly consistent sector labels.

{table(['Partition','Employers','NAICS 62','Other'],[(s,v['employers'],v['positive'],v['negative']) for s,v in d['splits'].items()])}

The split uses seed {d['seed']} and stratification, with zero shared employer-name keys across partitions. It is 70/10/20 up to integer rounding. Exact company-name case and whitespace normalization is used; aliases and subsidiaries may still appear as separate entities. This is weaker than the paper's proprietary entity normalization.

## Model results on the held-out employers

{table(['Model','Precision for NAICS 62','Recall','F1','Accuracy'],[(m['model'],f"{m['test_report']['1']['precision']:.3f}",f"{m['test_report']['1']['recall']:.3f}",f"{m['test_report']['1']['f1-score']:.3f}",f"{m['test_report']['accuracy']:.3f}") for m in d['models']])}

![Confusion matrices on held-out employers. Rows are dataset-derived labels and columns are model predictions.](images/confusion.png)

These metrics measure agreement with dataset-derived sector labels, not independently verified employer truth. GBDT misses {d['models'][1]['confusion_matrix'][1][0]} of the {d['splits']['test']['positive']} healthcare employers, with {d['models'][1]['confusion_matrix'][0][1]} false positives among {d['splits']['test']['negative']} other employers. This small sample cannot establish perfect precision in deployment. The all-positive baseline has F1 {d['models'][3]['test_report']['1']['f1-score']:.3f}, compared with GBDT's {d['models'][1]['test_report']['1']['f1-score']:.3f}; ranking models on F1 alone would conceal their very different precision and recall.

For a career product, predicted healthcare labels could narrow an employer-review queue, but the missed healthcare employers would make automatic exclusion costly. Retain existing labels and review disagreements before changing the career sample. No manually adjudicated undefined-employer labels are available, so the paper's utility scores cannot be reproduced here.

## Training and feature details

Vocabulary thresholds are learned from the training employers only. The selected vocabulary contains {d['features']['titles']} title candidates and {d['features']['name_words']} name words. After the 1% within-employer filter, the fitted matrix has {d['features']['matrix_columns']} observed columns; candidates absent from all training feature vectors are dropped.

The linear SVM tests C = 0.1, 1 and 10 with balanced class penalties. GBDT tests depths 2 and 3 with 100 estimators and learning rate 0.1. Each model is chosen by validation F1, then evaluated on the test partition without refitting. Exact configurations, validation scores, versions and full classification reports are in [run.json](data/study/run.json).

## Differences from the paper

The reference design is @goindani2017; the implementation uses scikit-learn [@pedregosa2011].

This is an exploratory adaptation: a 2026 dataset, one industry, US-only observations, scikit-learn LinearSVC and GBDT, validation-based tuning instead of the paper's reported cross-validation, and normalized employer-name unigrams without all raw name variants. Name-word frequency counts employers containing the word. The 80% dominant-sector rule is an explicit adaptation for inconsistent posting-level labels. The final study is not a preregistered confirmatory replication.

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

Source: local snapshot [@jobs2026], analyzed by this project's scripts; these observed counts are not findings of the 2017 paper.

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

Download the full [market skill table](data/study/market_skills.csv). Source: local snapshot [@jobs2026], analyzed by this project. Skills retain the dataset's names rather than applying a newly invented synonym taxonomy. Frequency supports a market-skills benchmark; it does not measure required proficiency or any individual's gap.
''')
print('STUDY PAGES GENERATED')

````

## render_figures.py

[Download source](scripts/render_figures.py)

````python
"""Regenerate website/report figures from saved aggregates, without model fitting."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from run_study import bar_chart, FIG

ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/study/run.json').read_text())
c=d['career']['counts']
bar_chart(list(c['states'])[:10],list(c['states'].values())[:10],'Healthcare analyst postings by state','Postings in the selected sample','states.png')
bar_chart(list(c['remote']),list(c['remote'].values()),'Reported work arrangement','Postings in the selected sample','remote.png')
with (ROOT/'data/study/market_skills.csv').open(newline='',encoding='utf-8') as f: skills=list(csv.DictReader(f))[:12]
bar_chart([r['skill'] for r in skills],[int(r['postings']) for r in skills],'Most frequently listed skills',f"Postings mentioning skill; denominator = {d['career']['postings']} selected postings",'skills.png')
fig,axes=plt.subplots(1,2,figsize=(9,4))
for ax,result in zip(axes,d['models'][:2]):
    matrix=np.array(result['confusion_matrix'])
    ax.imshow(matrix,cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>matrix.max()/2 else '#102b3f')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Other','NAICS 62'],yticklabels=['Other','NAICS 62'],xlabel='Predicted',ylabel='Dataset label',title=result['model'])
fig.tight_layout(); fig.savefig(FIG/'confusion.png',dpi=180,bbox_inches='tight'); plt.close(fig)
print('FIGURES GENERATED')

````

## run_eda.py

[Download source](scripts/run_eda.py)

````python
"""Profile local Jobs_2026_US posting partitions; export only aggregate evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from run_study import COLS, KNOWN_SECTORS, STATE_MAP, bar_chart

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'eda'
MISSING = '(missing)'


def strings(series):
    return series.astype('string').fillna('').str.strip()


def table(headers, rows):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join(['---'] * len(headers)) + '|'] +
                     ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('E:/Data/Jobs_2026_US'))
    args = parser.parse_args()
    files = sorted(args.data_dir.glob('jobs_2026_part_*.parquet'))
    if not files:
        parser.error('No jobs_2026_part_*.parquet files found')
    counts = Counter()
    missing = Counter()
    distributions = {k: Counter() for k in ['posted_year', 'posted_month', 'country',
                                           'sector', 'state', 'remote', 'staffing']}
    manifest, salaries = [], []
    seen = set()
    date_min = date_max = None
    for file in files:
        parquet = pq.ParquetFile(file)
        absent = set(COLS) - set(parquet.schema_arrow.names)
        if absent:
            raise ValueError(f'{file.name}: missing required columns {sorted(absent)}')
        with file.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest.append({'file': file.name, 'rows': parquet.metadata.num_rows,
                         'bytes': file.stat().st_size, 'sha256': digest,
                         'schema': {f.name: str(f.type) for f in parquet.schema_arrow}})
        for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
            frame = batch.to_pandas()
            counts['source_rows'] += len(frame)
            text = {col: strings(frame[col]) for col in COLS}
            missing.update({col: int(text[col].eq('').sum()) for col in COLS})
            ids = frame['ID'].dropna()
            counts['missing_id'] += int(frame['ID'].isna().sum())
            before = len(seen)
            seen.update(ids.tolist())
            counts['duplicate_id'] += len(ids) - (len(seen) - before)
            dates = pd.to_datetime(frame['POSTED'], errors='coerce', utc=True, format='mixed')
            counts['invalid_or_missing_date'] += int(dates.isna().sum())
            if dates.notna().any():
                lo, hi = dates.min(), dates.max()
                date_min = lo if date_min is None else min(lo, date_min)
                date_max = hi if date_max is None else max(hi, date_max)
            counts['january_september_2026_rows'] += int(
                ((dates >= '2026-01-01') & (dates < '2026-10-01')).sum())
            sector = text['NAICS_2022_2'].where(text['NAICS_2022_2'].ne(''), text['NAICS2'])
            counts['invalid_nonempty_sector'] += int((sector.ne('') & ~sector.isin(KNOWN_SECTORS)).sum())
            state = text['STATE_NAME'].str.upper().map(STATE_MAP).fillna('(missing or unrecognized)')
            remote = text['REMOTE_TYPE_NAME'].str.casefold().replace({'on-site': 'onsite'})
            values = {'posted_year': dates.dt.strftime('%Y').fillna(MISSING),
                      'posted_month': dates.dt.strftime('%Y-%m').fillna(MISSING),
                      'country': text['PARSED_COUNTRY_ISO_ABBR'].str.upper(),
                      'sector': sector, 'state': state, 'remote': remote,
                      'staffing': text['COMPANY_IS_STAFFING']}
            for key, series in values.items():
                distributions[key].update(series.replace('', MISSING).value_counts().to_dict())
            salary = pd.to_numeric(frame['NORMALIZED_SALARY'], errors='coerce')
            usable = (np.isfinite(salary) & salary.gt(0) & text['TEXT_PAY_CURRENCY'].eq('USD'))
            salaries.extend(salary[usable].tolist())
        print(f'Profiled {file.name}', flush=True)
    counts['unique_nonmissing_ids'] = len(seen)
    counts['usable_annual_usd_salary_rows'] = len(salaries)
    quantiles = ({str(q): float(np.quantile(salaries, q)) for q in [0, .25, .5, .75, 1]}
                 if salaries else {})
    study = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    fingerprints = lambda rows: {(r['file'], r['rows'], r['sha256']) for r in rows}
    matches = fingerprints(manifest) == fingerprints(study['files'])
    result = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'source_directory': str(args.data_dir.resolve()),
              'file_pattern': 'jobs_2026_part_*.parquet',
              'unit': 'raw posting rows before study exclusions; duplicates retained',
              'counts': dict(counts), 'date_min': str(date_min), 'date_max': str(date_max),
              'missingness_definition': 'null or whitespace-only; encoded empty lists and unknown labels are not null',
              'profiled_columns': COLS, 'missing': dict(missing),
              'distributions': distributions, 'annual_usd_salary_quantiles': quantiles,
              'study_manifest_matches': matches, 'files': manifest}
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'images').mkdir(exist_ok=True)
    (OUT / 'run.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    n = counts['source_rows']
    coverage = pd.DataFrame([{'column': c, 'missing_rows': missing[c],
                             'present_rows': n - missing[c], 'missing_share': missing[c] / n}
                            for c in COLS]).sort_values('missing_rows', ascending=False)
    coverage.to_csv(OUT / 'missingness.csv', index=False)
    for key, values in distributions.items():
        pd.DataFrame([{'value': v, 'rows': count, 'share_source_rows': count / n}
                      for v, count in values.most_common()]).to_csv(OUT / f'{key}.csv', index=False)
    bar_chart(coverage['column'].tolist(), (coverage['missing_share'] * 100).tolist(),
              'Missingness in fields used by the study', '% of all source rows', 'eda_missingness.png')
    years = sorted(distributions['posted_year'].items())
    bar_chart([v for v, _ in years], [c for _, c in years],
              'Posting dates in Jobs_2026_US', 'Source rows (before exclusions)', 'eda_years.png')
    sections = [f'''## Local Jobs_2026_US exploratory analysis

The analysis and EDA use the Jobs_2026_US snapshot [@jobs2026]. This scan contains **{n:,} rows across {len(files)} posting partitions**. Only `jobs_2026_part_*.parquet` files are inputs; supporting exports and backups are excluded. The repository contains aggregates and file hashes.

EDA describes raw rows before the healthcare study's filters. Duplicate IDs are counted but retained in these distributions. Posting-ID uniqueness does not rule out repeated advertisements with different IDs. Populated industry and skills fields are not independently verified labels.

{table(['Measure', 'Observed value'], [('Nonmissing unique IDs', f"{len(seen):,}"), ('Repeated-ID rows beyond first occurrence', f"{counts['duplicate_id']:,}"), ('Missing IDs', f"{counts['missing_id']:,}"), ('Earliest parsed posting date (UTC)', str(date_min)), ('Latest parsed posting date (UTC)', str(date_max)), ('Missing or unparseable dates', f"{counts['invalid_or_missing_date']:,}"), ('Dated January–September 2026, before other filters', f"{counts['january_september_2026_rows']:,}")])}

![Posting-year distribution across all source rows.](images/eda_years.png)

### Field coverage

Missingness covers the {len(COLS)} fields consumed by the study. Missing means null or whitespace-only; strings such as `[]`, `Unknown` or `Unclassified` still count as populated. Full input schemas are recorded in the EDA manifest.

![Missingness across study fields, denominator all source rows.](images/eda_missingness.png)

{table(['Field', 'Missing rows', 'Missing share'], [(r.column, f'{r.missing_rows:,}', f'{r.missing_share:.1%}') for r in coverage.itertuples()])}

### Industry, geography and work arrangement

The following tables show the ten most frequent categories, including missing where it ranks in the top ten. Every share uses all {n:,} source rows. Full distributions are saved as CSVs. Sector uses `NAICS_2022_2`, falling back to `NAICS2` only when blank; {counts['invalid_nonempty_sector']:,} nonempty values are outside the study's accepted sector vocabulary. States normalize US abbreviations and full names; other state values share an explicit unrecognized category. Remote labels are lowercased and `On-site` is merged with `Onsite`.
''']
    for key, label in [('sector', 'Sector codes'), ('country', 'Parsed country'),
                       ('state', 'US states'), ('remote', 'Work arrangement')]:
        sections.append(f"#### {label}\n\n" + table(['Category', 'Rows', 'Share of source'],
                         [(v, f'{c:,}', f'{c/n:.1%}') for v, c in distributions[key].most_common(10)]))
    sections.append(f'''### Salary coverage and study boundary

There are **{len(salaries):,} rows ({len(salaries)/n:.1%})** with a finite positive normalized salary, explicitly USD currency, consistent with the healthcare study salary filter. These are annual-equivalent advertised amounts; they may include compensation beyond base pay. They are not observed earnings or a representative wage survey. Raw amounts with mixed or unknown pay periods are not pooled.

{table(['Annual-equivalent USD measure', 'Amount'], [(label, f"{quantiles[str(q)]:,.2f}") for q, label in [(0, 'Minimum'), (.25, '25th percentile'), (.5, 'Median'), (.75, '75th percentile'), (1, 'Maximum')]]) if salaries else 'No rows satisfy the salary definition.'}

{'All input filenames, row counts and SHA-256 hashes match the saved healthcare study.' if matches else '**The EDA inputs differ from the saved healthcare study. Re-run the study before interpreting them as the same snapshot.**'} The healthcare analysis further restricts dates, country, sector, staffing status and usable employer/title fields. Its employer model and analyst career sample have different units and denominators; the filtering ledger is in [the 2026 study](career_evaluation.qmd).

The [EDA manifest](data/eda/run.json), [field missingness](data/eda/missingness.csv), [posting months](data/eda/posted_month.csv), [sector distribution](data/eda/sector.csv), [country distribution](data/eda/country.csv), [state distribution](data/eda/state.csv) and [work arrangements](data/eda/remote.csv) provide the aggregate evidence.
''')
    (ROOT / '_content/source-eda-results.md').write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
    print(f'EDA COMPLETE: {n:,} rows; {len(files)} partitions; study manifest matches={matches}')


if __name__ == '__main__':
    main()


````

## run_multiclass.py

[Download source](scripts/run_multiclass.py)

````python
"""Additional multiclass experiment; source records and employer identities stay private."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import platform
import re

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq
import sklearn
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.svm import LinearSVC

from run_study import clean, tokens, select_vocab

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/multiclass'
SECTORS = {
    '11': 'Agriculture, forestry, fishing and hunting',
    '21': 'Mining, quarrying, and oil and gas extraction',
    '22': 'Utilities', '23': 'Construction', '31-33': 'Manufacturing',
    '42': 'Wholesale trade', '44-45': 'Retail trade',
    '48-49': 'Transportation and warehousing', '51': 'Information',
    '52': 'Finance and insurance', '53': 'Real estate and rental and leasing',
    '54': 'Professional, scientific and technical services',
    '55': 'Management of companies and enterprises',
    '56': 'Administrative/support and waste management/remediation services',
    '61': 'Educational services', '62': 'Health care and social assistance',
    '71': 'Arts, entertainment and recreation',
    '72': 'Accommodation and food services',
    '81': 'Other services (except public administration)',
    '92': 'Public administration',
}
COMBINED = {**dict.fromkeys(['31', '32', '33'], '31-33'),
            **dict.fromkeys(['44', '45'], '44-45'),
            **dict.fromkeys(['48', '49'], '48-49')}
COLS = ['ID', 'POSTED', 'COMPANY_NAME', 'TITLE_NAME', 'PARSED_COUNTRY_ISO_ABBR',
        'NAICS_2022_2', 'NAICS2', 'COMPANY_IS_STAFFING']


def normalize_sector(value):
    value = clean(value)
    value = COMBINED.get(value, value)
    return value if value in SECTORS else None


def read_employers(data_dir):
    files = sorted(data_dir.glob('jobs_2026_part_*.parquet'))
    if not files:
        raise ValueError('No source partitions found')
    ledger, seen, manifests = Counter(), set(), []
    employers = defaultdict(lambda: {'count': 0, 'titles': Counter(), 'sectors': Counter()})
    for path in files:
        parquet = pq.ParquetFile(path)
        with path.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        manifests.append({'file': path.name, 'bytes': path.stat().st_size,
                          'rows': parquet.metadata.num_rows, 'sha256': digest})
        for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
            dates = pd.to_datetime(batch.column('POSTED').to_pylist(), errors='coerce', utc=True, format='mixed')
            for row, date in zip(batch.to_pylist(), dates):
                ledger['source_rows'] += 1
                if row['ID'] is None:
                    ledger['missing_id'] += 1
                    continue
                if row['ID'] in seen:
                    raise ValueError('Duplicate posting ID; resolve source ordering before analysis')
                seen.add(row['ID'])
                ledger['unique_id_rows'] += 1
                if pd.isna(date) or not (pd.Timestamp('2026-01-01', tz='UTC') <= date < pd.Timestamp('2026-10-01', tz='UTC')):
                    ledger['outside_period_or_unknown_date'] += 1
                    continue
                ledger['period_rows'] += 1
                if clean(row['PARSED_COUNTRY_ISO_ABBR']).upper() != 'US':
                    ledger['non_us_or_unknown_country'] += 1
                    continue
                ledger['us_rows'] += 1
                raw_sector = clean(row['NAICS_2022_2']) or clean(row['NAICS2'])
                sector = normalize_sector(raw_sector)
                if sector is None:
                    ledger['missing_or_invalid_sector'] += 1
                    continue
                ledger['sector_known_rows'] += 1
                ledger['sector_normalized_rows'] += sector != raw_sector
                if row['COMPANY_IS_STAFFING'] == 1:
                    ledger['staffing_excluded'] += 1
                    continue
                ledger['nonstaffing_or_unknown_rows'] += 1
                name = re.sub(r'\s+', ' ', clean(row['COMPANY_NAME']).casefold())
                title = clean(row['TITLE_NAME']).casefold()
                if name in ('', 'unknown', 'unclassified') or title in ('', 'unknown', 'unclassified'):
                    ledger['missing_employer_or_title'] += 1
                    continue
                e = employers[name]
                e['count'] += 1
                e['titles'][title] += 1
                e['sectors'][sector] += 1
                ledger['employer_model_postings'] += 1
        print(f'Read {path.name}: {ledger["source_rows"]:,} rows', flush=True)
    return employers, ledger, manifests


def make_splits(employers, minimum_class=20):
    """Require 20 employers per class before splitting, giving at least 14/2/4."""
    if minimum_class < 20:
        raise ValueError('At least 20 employers per class are required')
    groups = defaultdict(list)
    ledger = Counter(employers_before_filters=len(employers))
    for name, e in employers.items():
        sector, count = e['sectors'].most_common(1)[0]
        if e['count'] < 20:
            ledger['employers_below_20'] += 1
        elif count / e['count'] < .8:
            ledger['employers_without_dominant_sector'] += 1
        else:
            groups[sector].append(name)
    classes = sorted(s for s, names in groups.items() if len(names) >= minimum_class)
    if len(classes) < 3:
        raise ValueError('Fewer than three sectors meet the declared class-support threshold')
    names, labels, split_indices, support = [], [], defaultdict(list), []
    for sector in sorted(SECTORS):
        members = sorted(groups[sector], key=lambda n: (hashlib.sha256(('2017:' + n).encode()).hexdigest(), n))
        row = {'sector': sector, 'industry': SECTORS[sector], 'eligible_employers': len(members),
               'included': sector in classes, 'train': 0, 'validation': 0, 'test': 0}
        if sector in classes:
            for rank, name in enumerate(members):
                split = 'train' if rank < int(.7 * len(members)) else ('validation' if rank < int(.8 * len(members)) else 'test')
                split_indices[split].append(len(names))
                names.append(name)
                labels.append(sector)
                row[split] += 1
        support.append(row)
    ledger['eligible_employers'] = sum(len(v) for v in groups.values())
    ledger['excluded_low_support_employers'] = ledger['eligible_employers'] - len(names)
    ledger['model_employers'] = len(names)
    return names, np.array(labels), {k: np.array(v) for k, v in split_indices.items()}, support, ledger


def build_features(employers, names, y, train):
    """Union of training-only one-versus-rest vocabularies extends the paper's filter."""
    all_t, all_w = Counter(), Counter()
    pos_t, pos_w = defaultdict(Counter), defaultdict(Counter)
    for i in train:
        e = employers[names[i]]
        all_t.update(e['titles'])
        all_w.update(tokens(names[i]))
        pos_t[y[i]].update(e['titles'])
        pos_w[y[i]].update(tokens(names[i]))
    titles, words, thresholds = set(), set(), {}
    for label in sorted(set(y[train])):
        thresholds[label] = {}
        for kind, total, positive, target in [('titles', all_t, pos_t[label], titles), ('words', all_w, pos_w[label], words)]:
            if any(c > 1 for c in positive.values()):
                vocab, rule = select_vocab(total, positive)
                target.update(vocab)
                thresholds[label][kind] = rule | {'selected': len(vocab)}
            else:
                thresholds[label][kind] = {'selected': 0, 'reason': 'No token occurs more than once in this training class'}
    rows = []
    for name in names:
        e = employers[name]
        row = {'t:' + t: n / e['count'] for t, n in e['titles'].items() if t in titles and n / e['count'] >= .01}
        row.update({'w:' + w: 1. for w in tokens(name) & words})
        rows.append(row)
    vectorizer = DictVectorizer()
    vectorizer.fit([rows[i] for i in train])
    if not vectorizer.feature_names_:
        raise ValueError('No training features survived selection')
    return vectorizer.transform(rows), vectorizer, thresholds


def evaluate(y, pred, classes):
    return {'test_report': classification_report(y, pred, labels=classes, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(y, pred, labels=classes).tolist(),
            'accuracy': float(np.mean(y == pred))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--minimum-class-employers', type=int, default=20)
    args = parser.parse_args()
    employers, ledger, files = read_employers(args.data_dir)
    names, y, splits, support, filters = make_splits(employers, args.minimum_class_employers)
    ledger.update(filters)
    classes = sorted(set(y))
    # Integer targets avoid mixed numeric/range-string coercion in estimators.
    class_array = np.array(classes)
    encoded_y = np.searchsorted(class_array, y)
    print(f'Class support: {[(r["sector"], r["eligible_employers"], r["included"]) for r in support]}', flush=True)
    train, valid, test = [splits[s] for s in ('train', 'validation', 'test')]
    assert len(set(names)) == len(names)
    assert set(train).isdisjoint(valid) and set(train).isdisjoint(test) and set(valid).isdisjoint(test)
    X, vectorizer, thresholds = build_features(employers, names, y, train)
    families = [
        ('Linear SVM', [LinearSVC(C=c, class_weight='balanced', random_state=2017, max_iter=20000) for c in [.1, 1, 10]]),
        ('Logistic regression', [LogisticRegression(C=c, class_weight='balanced', random_state=2017, max_iter=3000) for c in [.1, 1, 10]]),
        ('Random forest', [RandomForestClassifier(n_estimators=200, max_depth=d, class_weight='balanced', random_state=2017, n_jobs=1) for d in [5, None]]),
        ('GBDT', [GradientBoostingClassifier(n_estimators=100, max_depth=d, random_state=2017) for d in [2, 3]]),
    ]
    models = []
    for name, candidates in families:
        trials, best_score, best = [], -1, None
        for model in candidates:
            model.fit(X[train], encoded_y[train])
            score = f1_score(y[valid], class_array[model.predict(X[valid])], labels=classes, average='macro', zero_division=0)
            trials.append({'params': model.get_params(), 'validation_macro_f1': float(score)})
            if score > best_score:
                best_score, best = score, model
        result = {'model': name, 'validation_macro_f1': float(best_score), 'trials': trials,
                  'selected_params': best.get_params(), **evaluate(y[test], class_array[best.predict(X[test])], classes)}
        models.append(result)
        print(f'{name}: validation macro-F1={best_score:.3f}; test macro-F1={result["test_report"]["macro avg"]["f1-score"]:.3f}', flush=True)
    majority = sorted(Counter(y[train]), key=lambda c: (-Counter(y[train])[c], c))[0]
    models.append({'model': 'Training majority', 'majority_sector': majority,
                   **evaluate(y[test], np.repeat(majority, len(test)), classes)})
    # Select the family by validation only; test metrics do not enter selection.
    selected = max(models[:-1], key=lambda m: m['validation_macro_f1'])['model']
    binary_path = ROOT / 'data/study/run.json'
    binary = json.loads(binary_path.read_text(encoding='utf-8'))
    old_files = {f['file']: f for f in binary['files']}
    snapshot_comparison = {
        'binary_manifest_sha256': hashlib.sha256(binary_path.read_bytes()).hexdigest(),
        'same_file_names_and_rows': [(f['file'], f['rows']) for f in files] == [(f['file'], f['rows']) for f in binary['files']],
        'changed_partition_hashes': sum(f['sha256'] != old_files.get(f['file'], {}).get('sha256') for f in files),
        'exact_snapshot_match': files == binary['files'],
    }
    result = {'source_directory': str(args.data_dir.resolve()), 'files': files,
              'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                           'pyarrow': pyarrow.__version__, 'sklearn': sklearn.__version__},
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'feature_helper_sha256': hashlib.sha256((ROOT / 'scripts/run_study.py').read_bytes()).hexdigest(),
              'minimum_class_employers': args.minimum_class_employers, 'ledger': dict(ledger),
              'comparison_with_saved_binary': snapshot_comparison,
              'classes': classes, 'class_support': support, 'employer_overlap': 0,
              'splits': {s: len(ix) for s, ix in splits.items()},
              'split_rule': 'Within-class SHA256(2017:normalized employer), floor 70%/80% boundaries; no cap',
              'features': {'count': X.shape[1], 'thresholds': thresholds,
                           'zero_vectors_by_split': {s: int(np.sum(X[ix].getnnz(axis=1) == 0)) for s, ix in splits.items()}},
              'models': models, 'selected_model': selected}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'run.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    pd.DataFrame(support).to_csv(OUT / 'class_support.csv', index=False)
    print(f'MULTICLASS COMPLETE: {len(classes)} classes; {len(names)} employers; selected {selected}')


if __name__ == '__main__':
    main()

````

## run_spark_study.py

[Download source](scripts/run_spark_study.py)

````python
"""Employer-level PySpark classification; publish aggregate evidence only."""

import argparse
import hashlib
import json
from pathlib import Path

import pyspark
from pyspark.sql import SparkSession, Window, functions as F
from pyspark.ml.classification import (
    LogisticRegression,
    DecisionTreeClassifier,
    RandomForestClassifier,
    GBTClassifier,
    LinearSVC,
    NaiveBayes,
    MultilayerPerceptronClassifier,
    OneVsRest,
    FMClassifier,
)
from pyspark.ml.feature import VectorAssembler

SECTORS = (
    "11 21 22 23 31 32 33 31-33 42 44 45 44-45 48 49 48-49 "
    "51 52 53 54 55 56 61 62 71 72 81 92"
).split()


def prepare(spark, files):
    raw = spark.read.parquet(*[str(p) for p in files])
    columns = [
        "ID",
        "POSTED",
        "COMPANY_NAME",
        "TITLE_NAME",
        "PARSED_COUNTRY_ISO_ABBR",
        "NAICS_2022_2",
        "NAICS2",
        "COMPANY_IS_STAFFING",
    ]
    raw = raw.select(*columns).cache()
    ledger = {"source_rows": raw.count()}
    # Conflicting duplicate IDs need an explicit source ordering rule.
    unique = raw.filter(F.col("ID").isNotNull()).dropDuplicates(["ID"])
    ledger["unique_id_rows"] = unique.count()
    if (
        raw.filter(F.col("ID").isNotNull()).count()
        != ledger["unique_id_rows"]
    ):
        raise ValueError(
            "Duplicate IDs found; resolve source order before analysis"
        )
    dated = unique.withColumn(
        "date", F.to_date(F.try_to_timestamp("POSTED"))
    )
    dated = dated.filter(
        (F.col("date") >= "2026-01-01") & (F.col("date") < "2026-10-01")
    )
    ledger["period_rows"] = dated.count()
    us = dated.filter(
        F.upper(F.trim("PARSED_COUNTRY_ISO_ABBR")) == "US"
    )
    ledger["us_rows"] = us.count()
    sector = F.when(
        F.length(F.trim("NAICS_2022_2")) > 0, F.trim("NAICS_2022_2")
    ).otherwise(F.trim("NAICS2"))
    known = us.withColumn("sector", sector).filter(
        F.col("sector").isin(SECTORS)
    )
    ledger["sector_known_rows"] = known.count()
    jobs = known.filter(
        ~F.coalesce(F.col("COMPANY_IS_STAFFING") == 1, F.lit(False))
    )
    ledger["nonstaffing_or_unknown_rows"] = jobs.count()
    jobs = (
        jobs.withColumn(
            "employer",
            F.regexp_replace(
                F.lower(F.trim("COMPANY_NAME")), r"\s+", " "
            ),
        )
        .withColumn("title", F.lower(F.trim("TITLE_NAME")))
        .filter(
            F.col("employer").isNotNull()
            & ~F.col("employer").isin("", "unknown", "unclassified")
        )
        .filter(
            F.col("title").isNotNull()
            & ~F.col("title").isin("", "unclassified")
        )
        .select("employer", "title", "sector")
        .cache()
    )
    ledger["employer_model_postings"] = jobs.count()
    raw.unpersist()
    return jobs, ledger


def employers_and_splits(jobs):
    totals = jobs.groupBy("employer").agg(
        F.count("*").alias("postings")
    )
    counts = jobs.groupBy("employer", "sector").count()
    dominant = (
        counts.withColumn(
            "rank",
            F.row_number().over(
                Window.partitionBy("employer").orderBy(
                    F.desc("count"), "sector"
                )
            ),
        )
        .filter("rank = 1")
        .join(totals, "employer")
        .filter(
            (F.col("postings") >= 20)
            & (F.col("count") / F.col("postings") >= 0.8)
        )
        .withColumn("label", (F.col("sector") == "62").cast("double"))
        .orderBy(F.desc("postings"), "employer")
        .limit(10000)
        .select("employer", "postings", "label")
    )
    # Rank within class by a seeded hash; no posting can cross employer splits.
    order = Window.partitionBy("label").orderBy(
        F.sha2(F.concat(F.lit("2017:"), F.col("employer")), 256),
        "employer",
    )
    size = Window.partitionBy("label")
    split = (
        dominant.withColumn("rank", F.row_number().over(order))
        .withColumn("class_n", F.count("*").over(size))
        .withColumn(
            "split",
            F.when(
                F.col("rank") <= F.floor(0.7 * F.col("class_n")),
                "train",
            )
            .when(
                F.col("rank") <= F.floor(0.8 * F.col("class_n")),
                "validation",
            )
            .otherwise("test"),
        )
        .select("employer", "postings", "label", "split")
        .cache()
    )
    support = [
        r.asDict()
        for r in split.groupBy("split", "label").count().collect()
    ]
    if len(support) != 6 or any(r["count"] < 2 for r in support):
        raise ValueError(
            "Every split needs at least two employers of each class"
        )
    return split, support


def feature_rows(jobs, employers):
    titles = (
        jobs.groupBy("employer", "title")
        .count()
        .join(employers, "employer")
        .withColumn("feature", F.concat(F.lit("t:"), F.col("title")))
        .withColumn("value", F.col("count") / F.col("postings"))
    )
    words = (
        employers.withColumn(
            "word",
            F.explode(
                F.array_distinct(
                    F.split(
                        F.regexp_replace("employer", "[^a-z]+", " "),
                        " ",
                    )
                )
            ),
        )
        .filter(F.length("word") > 0)
        .withColumn("feature", F.concat(F.lit("w:"), F.col("word")))
        .withColumn("value", F.lit(1.0))
        .withColumn("count", F.lit(1))
    )
    cols = ["employer", "label", "split", "feature", "value", "count"]
    return titles.select(*cols).unionByName(words.select(*cols))


def fit_vocabulary(long):
    # Frequency counts postings for titles, employers for name words.
    stats = (
        long.filter("split = 'train'")
        .groupBy("feature")
        .agg(
            F.sum("count").alias("frequency"),
            F.sum(
                F.when(F.col("label") == 1, F.col("count")).otherwise(0)
            ).alias("positive"),
        )
        .filter("positive > 1")
        .withColumn(
            "significance", F.col("positive") / F.col("frequency")
        )
    )
    vocab, thresholds = [], {}
    for prefix in ["t:", "w:"]:
        part = stats.filter(F.col("feature").startswith(prefix)).cache()
        if not part.count():
            raise ValueError("No training vocabulary for " + prefix)
        s = part.approxQuantile("significance", [0.5], 0)[0]
        f = part.approxQuantile("frequency", [0.5], 0)[0]
        selected = part.filter(
            (F.col("significance") >= s) & (F.col("frequency") >= f)
        )
        if selected.count() < 50:
            f = part.approxQuantile("frequency", [0.25], 0)[0]
            selected = part.filter(
                (F.col("significance") >= s) & (F.col("frequency") >= f)
            )
        vocab.extend(
            r.feature for r in selected.select("feature").collect()
        )
        thresholds[prefix] = {"significance": s, "frequency": f}
        part.unpersist()
    # Remove title columns absent after the within-employer cutoff in training.
    active = long.filter(
        (F.col("value") >= 0.01) & (F.col("split") == "train")
    )
    observed = {
        r.feature for r in active.select("feature").distinct().collect()
    }
    return sorted(set(vocab) & observed), thresholds


def vectorize(long, employers, vocabulary):
    if not vocabulary:
        raise ValueError("Empty training feature matrix")
    # Bound the driver vocabulary by the fitted training features, not raw rows.
    wide = (
        long.filter(F.col("value") >= 0.01)
        .groupBy("employer")
        .pivot("feature", vocabulary)
        .sum("value")
    )
    # Safe column aliases avoid interpreting dots in title names as nested fields.
    aliases = ["x" + str(i) for i in range(len(vocabulary))]
    wide = wide.toDF("employer", *aliases)
    matrix = employers.join(wide, "employer", "left").fillna(
        0.0, subset=aliases
    )
    return VectorAssembler(
        inputCols=aliases, outputCol="features"
    ).transform(matrix)


def candidates(dimension):
    # Two small validation candidates per family keep the example tractable.
    return {
        "Logistic regression": [
            LogisticRegression(regParam=r, maxIter=100)
            for r in [0.01, 0.1]
        ],
        "Decision tree": [
            DecisionTreeClassifier(maxDepth=d, seed=2017)
            for d in [2, 3]
        ],
        "Random forest": [
            RandomForestClassifier(numTrees=100, maxDepth=d, seed=2017)
            for d in [2, 3]
        ],
        "GBT": [
            GBTClassifier(
                maxIter=100, maxDepth=d, stepSize=0.1, seed=2017
            )
            for d in [2, 3]
        ],
        "Linear SVM": [
            LinearSVC(regParam=r, maxIter=100, weightCol="weight")
            for r in [0.01, 0.1]
        ],
        "Naive Bayes": [
            NaiveBayes(smoothing=s, modelType="multinomial")
            for s in [0.5, 1.0]
        ],
        "Multilayer perceptron": [
            MultilayerPerceptronClassifier(
                layers=[dimension, h, 2], maxIter=100, seed=2017
            )
            for h in [8, 16]
        ],
        "One-vs-rest logistic": [
            OneVsRest(
                classifier=LogisticRegression(regParam=r, maxIter=100),
                parallelism=1,
            )
            for r in [0.01, 0.1]
        ],
        "Factorization machine": [
            FMClassifier(
                factorSize=k, maxIter=100, stepSize=0.01, seed=2017
            )
            for k in [4, 8]
        ],
    }


def binary_metrics(predictions):
    counts = {
        (int(r.label), int(r.prediction)): r["count"]
        for r in predictions.groupBy("label", "prediction")
        .count()
        .collect()
    }
    tn, fp = counts.get((0, 0), 0), counts.get((0, 1), 0)
    fn, tp = counts.get((1, 0), 0), counts.get((1, 1), 0)
    total = tn + fp + fn + tp
    if not total:
        raise ValueError("Empty evaluation partition")
    return {
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "accuracy": (tp + tn) / total,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "support": total,
    }


def evaluate(matrix, dimension):
    train = matrix.filter("split = 'train'").cache()
    validation = matrix.filter("split = 'validation'").cache()
    test = matrix.filter("split = 'test'").cache()
    class_counts = {
        int(r.label): r["count"]
        for r in train.groupBy("label").count().collect()
    }
    n = sum(class_counts.values())
    train = train.withColumn(
        "weight",
        F.when(
            F.col("label") == 1, n / (2 * class_counts[1])
        ).otherwise(n / (2 * class_counts[0])),
    ).cache()
    results = []
    for name, options in candidates(dimension).items():
        trials, best, best_score = [], None, -1.0
        for estimator in options:
            model = estimator.fit(train)
            score = binary_metrics(model.transform(validation))["f1"]
            params = {
                p.name: str(v)
                for p, v in estimator.extractParamMap().items()
            }
            trials.append(
                {"parameters": params, "validation_f1": score}
            )
            if score > best_score:
                best, best_score = model, score
        result = {
            "model": name,
            "validation_f1": best_score,
            "trials": trials,
            **binary_metrics(best.transform(test)),
        }
        results.append(result)
        print(json.dumps(result), flush=True)
    majority = max(class_counts, key=class_counts.get)
    for name, value in [
        ("Training majority", majority),
        ("All positive", 1),
    ]:
        results.append(
            {
                "model": name,
                **binary_metrics(
                    test.withColumn("prediction", F.lit(float(value)))
                ),
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(args.data_dir.glob("jobs_2026_part_*.parquet"))
    if not files:
        parser.error("No posting partitions found")
    spark = (
        SparkSession.builder.appName("HealthcareEmployerClassification")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    try:
        jobs, ledger = prepare(spark, files)
        print("FILTER LEDGER " + json.dumps(ledger), flush=True)
        employers, support = employers_and_splits(jobs)
        long = feature_rows(jobs, employers).cache()
        vocabulary, thresholds = fit_vocabulary(long)
        matrix = vectorize(long, employers, vocabulary).cache()
        results = evaluate(matrix, len(vocabulary))
        manifest = {
            "engine": "pyspark",
            "version": pyspark.__version__,
            "seed": 2017,
            "split_method": "within-class SHA256 rank 70/10/20",
            "ledger": ledger,
            "splits": support,
            "feature_count": len(vocabulary),
            "thresholds": thresholds,
            "models": results,
            "files": [],
        }
        for path in files:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
            manifest["files"].append(
                {"file": path.name, "sha256": digest}
            )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "run.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        print("SPARK STUDY COMPLETE", flush=True)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

````

## run_study.py

[Download source](scripts/run_study.py)

````python
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
    run = {'source_directory': args.data_dir.resolve().as_posix(), 'seed':2017,'period':['2026-01-01','2026-09-30'],'minimum_label_share':args.minimum_label_share,'versions':{'python':platform.python_version(),'pandas':pd.__version__,'pyarrow':pyarrow.__version__,'sklearn':sklearn.__version__},
           'files':manifests,'ledger':dict(ledger),'role_regex':ROLE.pattern,'splits':splits,
           'features':{'titles':len(titles),'name_words':len(words),'matrix_columns':X.shape[1], 'title_thresholds':title_thresholds,'name_thresholds':name_thresholds},
           'models':model_results,'career':summary,'employer_overlap':0}
    (OUT/'run.json').write_text(json.dumps(run,indent=2,allow_nan=False),encoding='utf-8')
    print('STUDY COMPLETE',json.dumps({'ledger':dict(ledger),'splits':splits,'career_postings':len(df)}),flush=True)

if __name__ == '__main__':
    main()

````

## verify_citations.py

[Download source](scripts/verify_citations.py)

````python
"""Verify resolved Quarto citation targets and the report bibliography."""
from html.parser import HTMLParser
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]

class Citations(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.cites, self.targets = set(), set(), set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        self.cites.update(a.get('data-cites', '').split())
        if a.get('href', '').startswith('#ref-'): self.targets.add(a['href'][1:])

def verify_page(html, keys):
    parser = Citations(); parser.feed(html)
    for key in parser.cites:
        assert key in keys, f'Unknown key {key}'
        assert 'ref-'+key in parser.ids, f'Missing bibliography target {key}'
    assert parser.targets <= parser.ids, 'Broken citation link'
    return parser.cites

def main():
    entries = re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,', (ROOT/'reference.bib').read_text(encoding='utf-8'))
    assert entries and len(entries) == len(set(entries)), 'Empty or duplicate bibliography keys'
    keys = set(entries)
    used = set()
    for page in (ROOT/'_site').glob('*.html'):
        used.update(verify_page(page.read_text(encoding='utf-8'), keys))
    core = {'goindani2017','chern2018','tsvetkova2024','naics2022','pedregosa2011'}
    intro = (ROOT/'_site/introduction.html').read_text(encoding='utf-8')
    assert core <= verify_page(intro, keys), 'Missing literature-review citations'
    catalog = Citations(); catalog.feed((ROOT/'_site/references.html').read_text(encoding='utf-8'))
    assert {'ref-'+k for k in keys} <= catalog.ids, 'Incomplete central bibliography'
    # A bibliography catalog may retain uncited records; every actual citation must resolve.
    assert core <= used, 'Required literature sources are not cited'
    with ZipFile(ROOT/'final_report.docx') as archive:
        doc = ET.fromstring(archive.read('word/document.xml'))
        ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text = ' '.join(n.text or '' for n in doc.findall('.//w:t',ns))
        for term in ['References','Goindani','Chern','Tsvetkova','Pedregosa','0.717','0.553']:
            assert term in text, f'Report missing {term}'
        assert not re.search(r'@(goindani2017|chern2018|tsvetkova2024|naics2022|pedregosa2011)',text)
        refs = text[text.rfind('References'):]
        for title in ['Automatically Detecting Errors','Scikit-learn','North American Industry Classification']:
            assert title.lower() in refs.lower(), f'Missing generated report reference: {title}'
        for phrase in ['Exploratory data analysis', 'Role-label consistency', 'Field coverage']:
            assert phrase in text, f'Missing report EDA section: {phrase}'
        for name in ['eda-selection.png','eda-coverage.png','eda-roles.png','eda-skills.png']:
            expected_image = (ROOT/'images'/name).read_bytes()
            assert any(archive.read(p) == expected_image for p in archive.namelist() if p.startswith('word/media/')), f'Missing report figure: {name}'
    # Negative control: a citation whose reference target is absent must fail.
    try:
        verify_page('<span data-cites="goindani2017"></span>',keys)
    except AssertionError:
        pass
    else:
        raise AssertionError('Broken citation negative control was incorrectly accepted')
    print(f'CITATIONS VERIFIED: {len(keys)} bibliography entries; five-source review; HTML targets and Word bibliography resolve')

if __name__ == '__main__':
    main()

````

## verify_eda.py

[Download source](scripts/verify_eda.py)

````python
"""Reconcile published EDA with the saved study and inspect its integration."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/study'
d = json.loads((OUT/'run.json').read_text())
c = d['career']; n = c['postings']
def rows(name):
    with (OUT/name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

manifest = json.loads((OUT/'eda_manifest.json').read_text())
for name, digest in manifest['inputs'].items():
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest() == digest, 'Stale EDA source'
for row, key in zip(rows('eda_selection.csv'), ['source_rows','period_rows','us_rows','sector_known_rows','nonstaffing_or_unknown_rows'], strict=True):
    assert int(row['postings']) == d['ledger'][key]
    assert math.isclose(float(row['share_source']), int(row['postings'])/d['ledger']['source_rows'])
expected = [c['skills_observed'],n-c['counts']['states'].get('Unknown or non-state',0),c['experience_observed'],n-c['counts']['remote'].get('Unknown',0),c['salary_usd_observed']]
for row, count in zip(rows('eda_coverage.csv'), expected, strict=True):
    assert int(row['observed']) == count
    assert int(row['observed'])+int(row['unavailable']) == int(row['denominator']) == n
    assert math.isclose(float(row['share_observed']), count/n)
for row in rows('eda_roles.csv'):
    assert c['counts']['roles'][row['role']] == int(row['postings'])
    assert math.isclose(float(row['share_all_postings']), int(row['postings'])/n)
original = {r['skill']:int(r['postings']) for r in rows('market_skills.csv')}
for row in rows('eda_skills.csv'):
    assert original[row['skill']] == int(row['postings'])
    assert math.isclose(float(row['share_all_postings']), int(row['postings'])/n)
    assert math.isclose(float(row['share_with_skills']), int(row['postings'])/c['skills_observed'])
for name in manifest['figures']:
    assert (ROOT/'images'/name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert name in (ROOT/'_content/eda-results.md').read_text(encoding='utf-8')
for name in ['market_baseline.qmd','final_report.qmd']:
    assert 'include _content/eda-results.md' in (ROOT/name).read_text()
expected_pages = {'index','introduction','data_preparation','market_baseline','skill_gap_analysis','career_evaluation','pyspark_analysis','interactive','analysis_code','final_recommendations','references','ai-disclosure','final_report'}
assert {p.stem for p in ROOT.glob('*.qmd')} == expected_pages
print('EDA VERIFIED: source hashes, counts, denominators, four PNGs and thirteen QMD sources including PySpark analysis and interactive exports')

````

## verify_multiclass.py

[Download source](scripts/verify_multiclass.py)

````python
"""Verify saved multiclass evidence using only the standard library."""
import csv
import argparse
import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def verify(d):
    binary = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    comparison = d['comparison_with_saved_binary']
    assert comparison['binary_manifest_sha256'] == hashlib.sha256((ROOT / 'data/study/run.json').read_bytes()).hexdigest()
    assert comparison['exact_snapshot_match'] == (d['files'] == binary['files'])
    assert comparison['same_file_names_and_rows'] == ([(f['file'], f['rows']) for f in d['files']] == [(f['file'], f['rows']) for f in binary['files']])
    old_files = {f['file']: f for f in binary['files']}
    assert comparison['changed_partition_hashes'] == sum(f['sha256'] != old_files.get(f['file'], {}).get('sha256') for f in d['files'])
    assert d['script_sha256'] == hashlib.sha256((ROOT / 'scripts/run_multiclass.py').read_bytes()).hexdigest()
    assert d['feature_helper_sha256'] == hashlib.sha256((ROOT / 'scripts/run_study.py').read_bytes()).hexdigest()
    ledger = d['ledger']
    assert sum(f['rows'] for f in d['files']) == ledger['source_rows']
    assert ledger['source_rows'] == ledger['unique_id_rows'] + ledger.get('missing_id', 0)
    for total, kept, excluded in [('unique_id_rows', 'period_rows', 'outside_period_or_unknown_date'),
                                  ('period_rows', 'us_rows', 'non_us_or_unknown_country'),
                                  ('us_rows', 'sector_known_rows', 'missing_or_invalid_sector'),
                                  ('sector_known_rows', 'nonstaffing_or_unknown_rows', 'staffing_excluded'),
                                  ('nonstaffing_or_unknown_rows', 'employer_model_postings', 'missing_employer_or_title')]:
        assert ledger[total] == ledger[kept] + ledger.get(excluded, 0)
    assert ledger['employers_before_filters'] == ledger.get('employers_below_20', 0) + ledger.get('employers_without_dominant_sector', 0) + ledger['eligible_employers']
    assert ledger['eligible_employers'] == ledger['model_employers'] + ledger['excluded_low_support_employers']
    assert d['employer_overlap'] == 0
    assert len(d['classes']) >= 3
    included = {r['sector']: r for r in d['class_support'] if r['included']}
    assert sorted(included) == d['classes']
    assert sum(r['eligible_employers'] for r in d['class_support']) == ledger['eligible_employers']
    for row in d['class_support']:
        assert row['included'] == (row['eligible_employers'] >= d['minimum_class_employers'])
        if row['included']:
            assert row['train'] == int(.7 * row['eligible_employers'])
            assert row['validation'] == int(.8 * row['eligible_employers']) - row['train']
            assert row['test'] == row['eligible_employers'] - row['train'] - row['validation']
            assert min(row[s] for s in ('train', 'validation', 'test')) >= 2
        else:
            assert row['train'] + row['validation'] + row['test'] == 0
    for split, count in d['splits'].items():
        assert count == sum(r[split] for r in included.values())
    assert sum(d['splits'].values()) == ledger['model_employers']
    for model in d['models']:
        cm, report = model['confusion_matrix'], model['test_report']
        k = len(d['classes'])
        assert len(cm) == k and all(len(row) == k for row in cm)
        assert all(isinstance(n, int) and n >= 0 for row in cm for n in row)
        n = sum(map(sum, cm))
        assert n == d['splits']['test']
        values = []
        for i, label in enumerate(d['classes']):
            tp, actual, predicted = cm[i][i], sum(cm[i]), sum(row[i] for row in cm)
            assert actual == included[label]['test']
            expected = {'precision': tp / predicted if predicted else 0,
                        'recall': tp / actual, 'f1-score': 2 * tp / (actual + predicted), 'support': actual}
            for key, value in expected.items():
                assert math.isclose(report[label][key], value, abs_tol=1e-12), (model['model'], label, key)
            values.append(expected)
        for key in ('precision', 'recall', 'f1-score'):
            assert math.isclose(report['macro avg'][key], sum(v[key] for v in values) / k, abs_tol=1e-12)
            assert math.isclose(report['weighted avg'][key], sum(v[key] * v['support'] for v in values) / n, abs_tol=1e-12)
        assert math.isclose(model['accuracy'], sum(cm[i][i] for i in range(k)) / n)
        if 'trials' in model:
            trial = max(model['trials'], key=lambda t: t['validation_macro_f1'])
            assert model['selected_params'] == trial['params']
            assert model['validation_macro_f1'] == trial['validation_macro_f1']
    assert d['selected_model'] == max(d['models'][:-1], key=lambda m: m['validation_macro_f1'])['model']
    baseline = d['models'][-1]
    assert baseline['model'] == 'Training majority'
    majority = sorted(included, key=lambda c: (-included[c]['train'], c))[0]
    assert baseline['majority_sector'] == majority
    j = d['classes'].index(majority)
    assert all(all(n == 0 for i, n in enumerate(row) if i != j) for row in baseline['confusion_matrix'])
    with (ROOT / 'data/multiclass/class_support.csv').open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(d['class_support'])
    for row, expected in zip(rows, d['class_support']):
        assert row == {k: str(v) for k, v in expected.items()}


def verify_publication(d):
    def rows(name):
        with (ROOT / f'data/multiclass/{name}.csv').open(newline='', encoding='utf-8') as handle:
            return list(csv.DictReader(handle))
    metrics = rows('metrics')
    assert len(metrics) == len(d['models'])
    for r, model in zip(metrics, d['models']):
        assert r['model'] == model['model']
        for column, expected in [('test_macro_f1', model['test_report']['macro avg']['f1-score']),
                                 ('test_weighted_f1', model['test_report']['weighted avg']['f1-score']),
                                 ('test_accuracy', model['accuracy']),
                                 ('test_balanced_accuracy', model['test_report']['macro avg']['recall'])]:
            assert math.isclose(float(r[column]), expected)
    per_class = rows('per_class')
    confusion = rows('confusion')
    assert len(per_class) == len(d['models']) * len(d['classes'])
    assert len(confusion) == len(d['models']) * len(d['classes']) ** 2
    for model in d['models']:
        for sector in d['classes']:
            r = next(r for r in per_class if r['model'] == model['model'] and r['sector'] == sector)
            for key in ('precision', 'recall', 'f1-score', 'support'):
                assert math.isclose(float(r[key]), model['test_report'][sector][key])
        actual = {(r['actual_sector'], r['predicted_sector']): int(r['employers']) for r in confusion if r['model'] == model['model']}
        assert [[actual[a, b] for b in d['classes']] for a in d['classes']] == model['confusion_matrix']
    html = (ROOT / '_site/multiclass_analysis.html').read_text(encoding='utf-8')
    with ZipFile(ROOT / 'final_report.docx') as archive:
        xml = ET.fromstring(archive.read('word/document.xml'))
        text = ' '.join(n.text or '' for n in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        assert any(archive.read(p) == (ROOT / 'images/multiclass-confusion.png').read_bytes()
                   for p in archive.namelist() if p.startswith('word/media/'))
    selected = next(m for m in d['models'] if m['model'] == d['selected_model'])
    for artifact in (html, text):
        for phrase in ('Multiclass industry classification', d['selected_model'],
                       f"{selected['test_report']['macro avg']['f1-score']:.3f}",
                       'Transportation and warehousing (9)', 'Finance and insurance'):
            assert phrase in artifact, phrase
        if not d['comparison_with_saved_binary']['exact_snapshot_match']:
            assert 'Source file hashes differ' in artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--published', action='store_true')
    args = parser.parse_args()
    d = json.loads((ROOT / 'data/multiclass/run.json').read_text(encoding='utf-8'))
    verify(d)
    corrupt = json.loads(json.dumps(d))
    corrupt['models'][0]['confusion_matrix'][0][0] += 1
    try:
        verify(corrupt)
    except AssertionError:
        pass
    else:
        raise AssertionError('Verifier accepted a corrupted confusion matrix')
    corrupt = json.loads(json.dumps(d))
    corrupt['comparison_with_saved_binary']['exact_snapshot_match'] = not d['comparison_with_saved_binary']['exact_snapshot_match']
    try:
        verify(corrupt)
    except AssertionError:
        pass
    else:
        raise AssertionError('Verifier accepted a false snapshot match')
    if args.published:
        verify_publication(d)
    print(f'MULTICLASS VERIFIED: {len(d["classes"])} classes; source hashes, exclusions, splits, metrics and corrupt-data control pass')


if __name__ == '__main__':
    main()

````

## verify_sample.py

[Download source](scripts/verify_sample.py)

````python
"""Check the saved sample execution against visible HTML, without a server."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'preparation': 'data_preparation', 'market': 'market_baseline',
         'skills': 'skill_gap_analysis', 'evaluation': 'career_evaluation'}


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def verify(result, site):
    assert result['sample'] is True
    assert result['fraction'] == .1 and result['seed'] == 2017
    study = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    assert result['source_directory'] == study['source_directory']
    assert {(r['file'], r['rows']) for r in result['inputs']} == {(r['file'], r['rows']) for r in study['files']}
    assert result['script_sha256'] == hashlib.sha256((ROOT / 'scripts/publish_sample.py').read_bytes()).hexdigest()
    assert sum(item['rows'] for item in result['inputs']) == result['source_rows']
    assert 0 < result['sampled_rows'] < result['source_rows']
    counts = list(result['ledger'].values())
    assert all(a >= b for a, b in zip(counts, counts[1:])) and counts[-1] > 0
    for chunk in result['chunks']:
        html = (site / (PAGES[chunk['page']] + '.html')).read_text(encoding='utf-8')
        parser = Text()
        parser.feed(html)
        visible = ''.join(parser.parts)
        assert chunk['title'] in visible
        assert 'sourceCode python' in html, 'Missing highlighted Python chunk'
        for line in chunk['code'].splitlines() + chunk['output'].splitlines():
            assert line.strip() in visible, f'Missing displayed code/output: {line}'


if __name__ == '__main__':
    result = json.loads((ROOT / 'data/sample/run.json').read_text(encoding='utf-8'))
    verify(result, ROOT / '_site')
    # A known bad output must fail, proving the output check is active.
    result['chunks'][0]['output'] += '\nINTENTIONALLY_MISSING_SAMPLE_OUTPUT'
    try:
        verify(result, ROOT / '_site')
    except AssertionError:
        pass
    else:
        raise AssertionError('Negative control did not fail')
    print('SAMPLE VERIFIED: all 5 code chunks and partial outputs visible; negative control rejected')

````

## verify_site.py

[Download source](scripts/verify_site.py)

````python
"""Verify generated local page/resource links without starting a web server."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import csv

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = 'href' if tag in ('a', 'link') else 'src'
        if key in attrs:
            self.links.append(attrs[key])

def verify():
    errors = []
    sources = [p for p in ROOT.glob('*.qmd') if p.name != 'final_report.qmd']
    for source in sources:
        if not (SITE / source.with_suffix('.html').name).is_file():
            errors.append(f'Missing rendered page: {source.name}')
    pages = list(SITE.glob('*.html'))
    expected_pages = {p.with_suffix('.html').name for p in sources}
    assert {p.name for p in pages} == expected_pages, 'Stale or unexpected rendered pages remain'
    for page in SITE.rglob('*.html'):
        parser = Links()
        html = page.read_text(encoding='utf-8')
        parser.feed(html)
        if '{{< include' in html:
            errors.append(f'Unresolved include: {page.name}')
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            target = SITE / path.lstrip('/') if path.startswith('/') else page.parent / path
            if not target.exists():
                errors.append(f'{page.name}: missing {path}')
    for name, count in [('classification', 10), ('utility', 4)]:
        with (ROOT / 'data' / f'{name}.csv').open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == count, name
        for row in rows:
            for key, value in row.items():
                if key not in ('industry', 'system', 'source'):
                    assert 0 <= float(value) <= 1, (name, row)
    # Published assets must match the exports, including scripts and map geometry.
    import hashlib
    import json
    manifest = json.loads((ROOT / 'data/interactive/manifest.json').read_text(encoding='utf-8'))
    for name, digest in {**manifest['inputs'], **manifest['outputs']}.items():
        if name.startswith('_content/'):
            continue
        target = SITE / name
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            errors.append(f'Missing or altered published asset: {name}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'SITE VERIFIED: {len(pages)} HTML pages; local resources resolve; published metric CSVs valid')

if __name__ == '__main__':
    verify()

````

## verify_source_eda.py

[Download source](scripts/verify_source_eda.py)

````python
"""Reconcile source EDA aggregates against local partitions and study evidence."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('E:/Data/Jobs_2026_US'))
    args = parser.parse_args()
    out = ROOT / 'data/eda'
    data = json.loads((out / 'run.json').read_text(encoding='utf-8'))
    study = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    files = {f.name: f for f in args.data_dir.glob('jobs_2026_part_*.parquet')}
    assert files and set(files) == {f['file'] for f in data['files']}
    assert len(files) == len(data['files'])
    total = 0
    for record in data['files']:
        file = files[record['file']]
        parquet = pq.ParquetFile(file)
        assert parquet.metadata.num_rows == record['rows']
        assert file.stat().st_size == record['bytes']
        assert {f.name: str(f.type) for f in parquet.schema_arrow} == record['schema']
        with file.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['sha256']
        total += record['rows']
    counts = data['counts']
    assert Path(data['source_directory']).resolve() == args.data_dir.resolve()
    assert Path(study['source_directory']).resolve() == args.data_dir.resolve()
    if args.data_dir.name == 'Jobs_2026_US':
        assert data['distributions']['country'] == {'US': total}
        assert data['distributions']['posted_year'] == {'2026': total}
    assert total == counts['source_rows']
    assert total == counts['unique_nonmissing_ids'] + counts['duplicate_id'] + counts['missing_id']
    for key, distribution in data['distributions'].items():
        assert sum(distribution.values()) == total, key
        with (out / f'{key}.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert {r['value']: int(r['rows']) for r in rows} == distribution
        assert all(math.isclose(float(r['share_source_rows']), int(r['rows']) / total) for r in rows)
    with (out / 'missingness.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert {r['column'] for r in rows} == set(data['profiled_columns'])
    for row in rows:
        assert int(row['missing_rows']) == data['missing'][row['column']]
        assert int(row['present_rows']) + int(row['missing_rows']) == total
        assert math.isclose(float(row['missing_share']), int(row['missing_rows']) / total)
    signatures = lambda records: {(r['file'], r['rows'], r['sha256']) for r in records}
    assert data['study_manifest_matches'] == (signatures(data['files']) == signatures(study['files']))
    assert data['study_manifest_matches'], 'Refresh study and EDA: input snapshots differ'
    assert counts['duplicate_id'] == study['ledger'].get('duplicate_id', 0)
    assert counts['missing_id'] == study['ledger'].get('missing_id', 0)
    if counts['duplicate_id'] == counts['missing_id'] == 0:
        assert counts['january_september_2026_rows'] == study['ledger']['period_rows']
    print(f'EDA VERIFIED: {total:,} rows; hashes, schemas, aggregate denominators and study snapshot reconcile')


if __name__ == '__main__':
    main()

````

## verify_spark_teaching.py

[Download source](scripts/verify_spark_teaching.py)

````python
"""Check actual Spark evidence, code excerpts and notebook syntax without servers."""
import ast
import json
from pathlib import Path
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'scripts/run_spark_study.py').read_text(encoding='utf-8')
tree = ast.parse(source)
walkthrough = (ROOT / '_content/spark-walkthrough.md').read_text(encoding='utf-8')
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        assert ast.get_source_segment(source, node) in walkthrough, node.name
notebook = json.loads((ROOT / 'notebooks/pyspark_classification.ipynb').read_text(encoding='utf-8'))
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        ast.parse(''.join(cell['source']))
run = json.loads((ROOT / 'data/spark-study/run.json').read_text(encoding='utf-8'))
original = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
assert run['engine'] == 'pyspark'
assert len(run['models']) == 11
assert len({r['model'] for r in run['models']}) == 11
assert {r['file']: r['sha256'] for r in run['files']} == {
    r['file']: r['sha256'] for r in original['files']}
for key, value in run['ledger'].items():
    assert value == original['ledger'][key], (key, value)
assert sum(r['count'] for r in run['splits']) == original['ledger']['model_employers']
test_n = sum(r['count'] for r in run['splits'] if r['split'] == 'test')
for r in run['models']:
    (tn, fp), (fn, tp) = r['confusion_matrix']
    assert tn + fp + fn + tp == r['support'] == test_n
    expected = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
    assert abs(r['f1'] - expected) < 1e-12
    if 'trials' in r:
        assert r['validation_f1'] == max(t['validation_f1'] for t in r['trials'])
    assert all(0 <= r[k] <= 1 for k in ['precision', 'recall', 'f1', 'accuracy'])
for filename in ['index.qmd', 'final_report.qmd', 'career_evaluation.qmd',
                 '_content/research-framing.md']:
    text = (ROOT / filename).read_text(encoding='utf-8').lower()
    for phrase in ["user's request", 'user selected', 'approved analysis',
                   'connect claims to one bibtex', 'standup records',
                   'preserve this distinction', 'submission boundaries']:
        assert phrase not in text, (filename, phrase)

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

parser = VisibleText()
parser.feed((ROOT / '_site/pyspark_analysis.html').read_text(encoding='utf-8'))
visible = ''.join(parser.parts)
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        for line in ast.get_source_segment(source, node).splitlines():
            assert line.strip() in visible, ('Missing rendered code', line)
with ZipFile(ROOT / 'final_report.docx') as archive:
    doc = ET.fromstring(archive.read('word/document.xml'))
    report = ''.join(n.text or '' for n in doc.iter(
        '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
for text in [visible, report]:
    for r in run['models']:
        assert r['model'] in text, ('Missing published model', r['model'])
        assert f"{r['f1']:.3f}" in text, ('Missing published metric', r['model'])
    for name in ['prepare', 'fit_vocabulary', 'candidates', 'binary_metrics']:
        assert 'def ' + name in text
print('SPARK TEACHING VERIFIED: 9 classifier families, 2 baselines, matching source hashes and filter counts; source excerpts and notebook syntax checked')

````

## verify_static_assets.py

[Download source](scripts/verify_static_assets.py)

````python
"""Check committed exports with Python's standard library; never read raw inputs."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_hash(path, expected):
    assert path.is_file(), f'Missing saved asset: {path}'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Stale export: {path}'


def main():
    manifest = json.loads((ROOT / 'data/interactive/manifest.json').read_text(encoding='utf-8'))
    for group in ('inputs', 'outputs'):
        for name, digest in manifest[group].items():
            verify_hash(ROOT / name, digest)
    # Positive control proves stale-file detection can reject incorrect hashes.
    try:
        verify_hash(ROOT / '_quarto.yml', '0' * 64)
    except AssertionError:
        pass
    else:
        raise AssertionError('Hash checker accepted a corrupt asset')
    config = (ROOT / '_quarto.yml').read_text(encoding='utf-8')
    for setting in ('enabled: false', 'eval: false', 'echo: true', 'code-fold: false'):
        assert setting in config, setting
    for source in [*ROOT.glob('*.qmd'), *(ROOT / '_content').glob('*.md')]:
        text = source.read_text(encoding='utf-8')
        assert not re.search(r'^\s*(?:#\|\s*)?(?:enabled|eval):\s*true\b', text, re.M), source
        assert not re.search(r'^\s*(?:#\|\s*)?echo:\s*false\b', text, re.M), source
    for name in ('months', 'skills', 'states'):
        chart = json.loads((ROOT / f'data/interactive/{name}.json').read_text(encoding='utf-8'))
        assert chart['data'], name
        html = (ROOT / f'images/interactive/{name}.html').read_text(encoding='utf-8')
        assert 'src="plotly.min.js"' in html, name
        assert 'https://cdn.plot.ly' not in html, name
    geometry = json.loads((ROOT / 'images/interactive/usa_110m.json').read_text(encoding='utf-8'))
    assert geometry['type'] == 'Topology' and 'subunits' in geometry['objects']
    csvs = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'data').rglob('*.csv')}
    assert csvs <= manifest['inputs'].keys(), 'An aggregate table has no exported version'
    code = (ROOT / '_content/analysis-code.md').read_text(encoding='utf-8')
    for path in (ROOT / 'scripts').glob('*.py'):
        assert path.read_text(encoding='utf-8') in code, f'Incomplete source display: {path}'
    print(f'STATIC ASSETS VERIFIED: {len(csvs)} tables; 3 Plotly charts; all input/output hashes match')


if __name__ == '__main__':
    main()

````

## verify_study.py

[Download source](scripts/verify_study.py)

````python
"""Independently reconcile saved aggregate counts and model metrics."""
import csv
import json
from pathlib import Path
import math
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/study/run.json').read_text())
l=d['ledger']
assert sum(f['rows'] for f in d['files'])==l['source_rows']
assert len({f['file'] for f in d['files']})==len(d['files'])
assert all(len(f['sha256'])==64 for f in d['files'])
assert l['source_rows']==l['unique_id_rows']+l.get('duplicate_id',0)+l.get('missing_id',0)
for total,kept,excluded in [('unique_id_rows','period_rows','outside_period_or_unknown_date'),('period_rows','us_rows','non_us_or_unknown_country'),('us_rows','sector_known_rows','missing_or_invalid_sector'),('sector_known_rows','nonstaffing_or_unknown_rows','staffing_excluded'),('nonstaffing_or_unknown_rows','employer_model_postings','missing_employer_or_title')]:
    assert l[total]==l[kept]+l.get(excluded,0),total
assert l['employers_before_filters']==l['employers_below_20']+l['employers_without_dominant_sector']+l['eligible_employers_before_cap']
assert sum(s['employers'] for s in d['splits'].values())==l['model_employers']
assert d['employer_overlap']==0
for m in d['models']:
    (tn,fp),(fn,tp)=m['confusion_matrix']
    assert tn+fp==d['splits']['test']['negative']
    assert fn+tp==d['splits']['test']['positive']
    expected={'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'f1-score':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0}
    for metric,value in expected.items(): assert math.isclose(value,m['test_report']['1'][metric])
for values in d['career']['counts'].values(): assert sum(values.values())==d['career']['postings']
with (ROOT/'data/study/market_skills.csv').open(newline='',encoding='utf-8') as f:
    for row in csv.DictReader(f): assert math.isclose(int(row['postings'])/d['career']['postings'],float(row['share_all_scope_postings']))
print('STUDY VERIFIED: filter ledger reconciles; metrics match confusion counts; benchmark denominators reconcile')

````
