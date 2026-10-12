"""Check saved aggregates and rendered links without opening the raw dataset."""
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def verify():
    data = json.loads((ROOT/'data/naics/snapshot.json').read_text(encoding='utf-8'))
    n = data['counts']['posting_records']
    assert len(data['files']) == 20
    assert sum(p['rows'] for p in data['files']) == n
    assert 0 < data['counts']['distinct_employer_names'] <= n
    for level, coverage in data['coverage'].items():
        assert sum(coverage.values()) == n
        groups = [g for g in data['groups'] if g['level'] == int(level)]
        assert sum(g['postings'] for g in groups) == coverage['classified']
        assert all(0 <= g['employers'] <= g['postings'] for g in groups)
    with (ROOT/'data/naics/industries.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    assert rows == [{k: str(v) for k, v in g.items()} for g in data['groups']]
    script = (ROOT/'data/naics/data.js').read_text(encoding='utf-8')
    assert json.loads(script.removeprefix('window.NAICS_DATA = ').strip().removesuffix(';')) == data
    assert hashlib.sha256((ROOT/'data/naics/column_coverage.csv').read_bytes()).hexdigest() == data['source_column_coverage_sha256']
    overview = json.loads((ROOT/'data/overview/coverage.json').read_bytes())
    global_data = json.loads((ROOT/'data/global/snapshot.json').read_bytes())
    for name, snapshot in [('Jobs_2026', global_data), ('Jobs_2026_US', data)]:
        assert overview['datasets'][name]['counts'] == snapshot['counts']
        assert overview['datasets'][name]['source_manifest_sha256'] == snapshot['source_manifest_sha256']
        candidate = overview['sec']['preview']['stores'][name]
        assert candidate['manifest_sha256'] == snapshot['source_manifest_sha256']
        assert candidate['ambiguous_job_records'] <= candidate['candidate_job_records'] <= candidate['rows']
    assert overview['verified_employer_links'] == 0
    with (ROOT/'data/naics/column_coverage.csv').open(encoding='utf-8-sig') as f:
        fields = {r['column']: int(r['populated']) for r in csv.DictReader(f)}
    for field in overview['useful_fields']:
        assert field['populated'] == fields.get(field['column'], 0)
    home = (ROOT/'_site/data_coverage.html').read_text(encoding='utf8')
    for number in (global_data['counts']['posting_records'], global_data['counts']['distinct_employer_names'], overview['sec']['audit']['unique_unambiguous_ciks']):
        assert f'{number:,}' in home
    assert 'Candidate matches are not verified employer links' in home
    assert '\u00c2\u00b7' not in home
    assert sum(data['months'].values()) == n
    assert overview['future_posting_month_records'] == sum(count for month, count in data['months'].items() if month != 'Unknown' and month > overview['generated_at_utc'][:7])
    for name in ('data/overview/coverage.json', 'data/global/snapshot.json'):
        assert (ROOT/name).read_bytes() == (ROOT/'_site'/name).read_bytes()
    for name in ('data/naics/snapshot.json','data/naics/industries.csv','data/naics/data.js','data/naics/column_coverage.csv','scripts/naics-explorer.js'):
        assert (ROOT/name).read_bytes() == (ROOT/'_site'/name).read_bytes(), name

    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key not in ('href', 'src') or not value:
                    continue
                url = urlsplit(value)
                if url.scheme or url.netloc or not url.path or url.path.startswith('/'):
                    continue
                target = self.path.parent / unquote(url.path)
                assert target.exists(), (self.path.name, value)

    for page in ('data_coverage','naics_explorer'):
        path = ROOT/'_site'/f'{page}.html'
        html = path.read_text(encoding='utf-8')
        parser = Links(); parser.path = path; parser.feed(html)
        assert data['release_id'] in html
        assert f'{n:,}' in html
        assert 'spark.read.parquet' not in html
    explorer = (ROOT/'_site/naics_explorer.html').read_text(encoding='utf-8')
    for control in ('level','parent','search','sort','industry-rows','explorer-status'):
        assert f'id="{control}"' in explorer
    for name in ('analysis_code', 'career_evaluation', 'multiclass_analysis', 'market_baseline'):
        historical = ROOT/'_site'/f'{name}.html'
        html = historical.read_text(encoding='utf8')
        # Source-code excerpts can mention the retired banner without rendering it.
        assert '<aside style="padding:1rem;background:#fff3cd' not in html
        parser = Links(); parser.path = historical; parser.feed(html)
    print('COVERAGE VERIFIED: paper appendices, published aggregates, links, controls and denominators')


if __name__ == '__main__':
    verify()
