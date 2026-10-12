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
