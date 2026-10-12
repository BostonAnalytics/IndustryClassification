"""Reconcile generated and rendered tables with their downloadable CSV cells."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from publish_csv_tables import read_csv, table

ROOT = Path(__file__).resolve().parents[1]


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.active = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and 'data-csv' in attrs:
            self.active = {'source': attrs['data-csv'], 'rows': []}
        if self.active is not None and tag == 'tr':
            self.row = []
        if self.active is not None and tag == 'td':
            self.cell = ''

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if self.active is not None and tag == 'td':
            self.row.append(self.cell.strip())
            self.cell = None
        if self.active is not None and tag == 'tr' and self.row:
            self.active['rows'].append(self.row)
        if self.active is not None and tag == 'table':
            self.tables.append(self.active)
            self.active = None


def verify(text):
    parser = Tables()
    parser.feed(text)
    assert len(parser.tables) == 7, len(parser.tables)
    for item in parser.tables:
        records = read_csv(item['source'])
        if item['source'].endswith('dataset_counts.csv'):
            expected = [[r['dataset'], f"{int(r['job_postings']):,}", f"{int(r['employer_names']):,}", r['release_id']] for r in records]
        elif item['source'].endswith('industries.csv'):
            level = len(item['rows'][0][0])
            records = sorted([r for r in records if int(r['level']) == level], key=lambda r: (-int(r['postings']), r['code']))[:15]
            expected = [[r['code'], r['name'], f"{int(r['postings']):,}", f"{int(r['employers']):,}"] for r in records]
        else:
            expected = [[r['value'], f"{int(r['rows']):,}", f"{float(r['share_source_rows']):.1%}"] for r in records]
        assert item['rows'] == expected, item['source']


def main():
    manifest = json.loads((ROOT / 'data/overview/csv-tables.json').read_text())
    for group in ('inputs', 'outputs'):
        for name, digest in manifest[group].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    text = '\n'.join((ROOT / name).read_text(encoding='utf-8') for name in manifest['outputs'])
    verify(text)
    # Positive corruption control: a plausible but wrong posting count must fail.
    try:
        verify(text.replace('815,193</td>', '199</td>', 1))
    except AssertionError:
        pass
    else:
        raise AssertionError('A corrupted count was accepted')
    escaped = table('test.csv', [('code', 'Code', 'text'), ('name', 'Name', 'text')], 'test',
                    rows=[{'code': '0012', 'name': '<script>"a,b" & c</script>'}])
    assert '<td>0012</td>' in escaped and '<script>' not in escaped and '&amp;' in escaped
    page = ROOT / '_site/market_baseline.html'
    if '--published' in sys.argv:
        assert page.exists() and 'csv-result' in page.read_text(encoding='utf-8'), 'CSV tables missing from rendered website'
    if page.exists() and 'csv-result' in page.read_text(encoding='utf-8'):
        rendered = page.read_text(encoding='utf-8')
        verify(rendered)
        assert rendered.index('Full US release: market tables') < rendered.index('Filtered healthcare analyst research cohort')
    assert 'python scripts/publish_csv_tables.py' in (ROOT / '_quarto.yml').read_text()
    print('CSV TABLES VERIFIED: every displayed cell, source hashes, corruption rejection and scope order')


if __name__ == '__main__':
    main()
