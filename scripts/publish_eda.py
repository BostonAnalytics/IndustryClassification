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

This descriptive analysis uses the saved Jobs_2026 aggregates [@jobs2026]. It examines selection, available career evidence, normalized role labels and skills before interpreting the predictive results. All career percentages use the {n} selected postings unless another denominator is stated. Figures describe recorded advertisements, not live vacancies or population employment.

### Selection and units of analysis

![Sequential posting filters before industry-and-title career selection or employer aggregation. Bar lengths use all {ledger['source_rows']:,} source records as the denominator; labels give retained counts.](images/eda-selection.png){{#fig-eda-selection fig-alt="Five horizontal bars show the number of records retained through date, country, industry and staffing filters." width=95%}}

The common filters retain {ledger['nonstaffing_or_unknown_rows']:,} of {ledger['source_rows']:,} records ({ledger['nonstaffing_or_unknown_rows']/ledger['source_rows']:.1%}). The explicit-US filter removes {ledger['non_us_or_unknown_country']:,} dated records; unknown country and non-US country are combined in the saved exclusion count. These exclusions describe selection, not proof that every excluded record is erroneous. The pipeline then branches: industry-and-title matching yields {n} career postings, while employer aggregation and eligibility rules yield {ledger['model_employers']} employers for classification. Those are different units and should not appear as consecutive steps in a single funnel.

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
