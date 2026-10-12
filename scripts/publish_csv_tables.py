"""Build website tables from processed CSVs; stdlib-only Quarto pre-render hook."""
import csv
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def table(name, columns, caption, *, rows=None, limit=None):
    """Escape all cells, preserve codes as strings, and format only typed counts."""
    records = read_csv(name) if rows is None else rows
    records = records[:limit] if limit else records
    lines = [f'<table class="table csv-result" data-csv="{name}">',
             f'<caption>{html.escape(caption)}</caption>', '<thead><tr>']
    lines += [f'<th scope="col">{html.escape(label)}</th>' for _, label, _ in columns]
    lines.append('</tr></thead><tbody>')
    for row in records:
        cells = []
        for key, _, kind in columns:
            value = row[key]
            value = f'{int(value):,}' if kind == 'count' else f'{float(value):.1%}' if kind == 'share' else value
            cells.append(f'<td>{html.escape(str(value))}</td>')
        lines.append('<tr>' + ''.join(cells) + '</tr>')
    lines += ['</tbody></table>', f'<p><a href="{name}">Download the complete processed CSV</a></p>']
    return '\n'.join(lines)


def build():
    overview = json.loads((ROOT / 'data/overview/coverage.json').read_text())
    inputs = ['data/overview/coverage.json', 'data/naics/snapshot.json', 'data/global/snapshot.json']
    output = ROOT / 'data/overview/dataset_counts.csv'
    with output.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['dataset', 'job_postings', 'employer_names', 'release_id'])
        for name, folder in [('Jobs_2026_US', 'naics'), ('Jobs_2026', 'global')]:
            data = overview['datasets'][name]
            snapshot = json.loads((ROOT / f'data/{folder}/snapshot.json').read_text())
            assert data['counts'] == snapshot['counts'], 'Overview disagrees with source snapshot'
            writer.writerow([name, data['counts']['posting_records'], data['counts']['distinct_employer_names'], data['release_id']])
    summary = '## Full published datasets\n\n' + table('data/overview/dataset_counts.csv', [
        ('dataset', 'Dataset', 'text'), ('job_postings', 'Job postings', 'count'),
        ('employer_names', 'Distinct employer names', 'count'), ('release_id', 'Release', 'text')],
        'Complete releases; job postings and employer-name groups are separate units.')
    summary += '\n\nThe global and US datasets overlap; do not add their counts. Employer names are normalized name groups, not verified legal entities. Posting counts are recorded advertisements, not confirmed live vacancies.\n'
    total = overview['datasets']['Jobs_2026_US']['counts']['posting_records']
    summary += f'\nThe market tables below describe all **{total:,} US postings**. The paper’s healthcare analyst cohort and held-out employer samples are filtered research subsets.\n'
    market = ['## Full US release: market tables\n\nThese tables import the processed source-wide CSVs on every website build. No career-title, January–September, or employer-size filter is applied here. Unknown values remain visible.\n']
    for filename, label in [('sector', 'NAICS sector'), ('remote', 'Work arrangement'), ('posted_month', 'Posting month')]:
        name = f'data/eda/{filename}.csv'
        records = read_csv(name)
        assert sum(int(r['rows']) for r in records) == total, f'Stale or incomplete CSV: {name}'
        assert all(abs(float(r['share_source_rows']) - int(r['rows']) / total) < 1e-10 for r in records)
        inputs.append(name)
        market.append(f'### {label}\n\n' + table(name, [('value', label, 'text'), ('rows', 'Job postings', 'count'),
            ('share_source_rows', 'Share of full US release', 'share')], f'{label}: denominator = {total:,} US job postings.'))
    name = 'data/naics/industries.csv'
    inputs.append(name)
    industries = read_csv(name)
    snapshot = json.loads((ROOT / 'data/naics/snapshot.json').read_text())
    for level in (4, 5, 6):
        records = sorted([r for r in industries if r['level'] == str(level)], key=lambda r: (-int(r['postings']), r['code']))
        classified = snapshot['coverage'][str(level)]['classified']
        assert sum(int(r['postings']) for r in records) == classified, f'NAICS {level} CSV disagrees with snapshot'
        market.append(f'### NAICS {level}: leading industries\n\n{classified:,} of {total:,} postings have a valid NAICS {level} code. The top 15 groups are shown; the download and [NAICS explorer](naics_explorer.qmd) contain every group. Employers may occur in several groups, so employer counts must not be summed.\n\n' + table(name, [
            ('code', f'NAICS {level}', 'text'), ('name', 'Industry', 'text'), ('postings', 'Job postings', 'count'),
            ('employers', 'Distinct employer names', 'count')], f'Full US release, NAICS {level}; ordered by job postings.', rows=records, limit=15))
    outputs = {'_content/csv-dataset-counts.md': summary, '_content/csv-market-tables.md': '\n\n'.join(market)}
    for name, content in outputs.items():
        (ROOT / name).write_text(content + '\n', encoding='utf-8')
    inputs.append('data/overview/dataset_counts.csv')
    manifest = {group: {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
                for group, names in [('inputs', inputs), ('outputs', outputs)]}
    (ROOT / 'data/overview/csv-tables.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('CSV TABLES GENERATED: full releases, source distributions and NAICS 4/5/6')


if __name__ == '__main__':
    build()
