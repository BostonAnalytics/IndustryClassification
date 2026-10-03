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
    for page in pages:
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
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'SITE VERIFIED: {len(pages)} HTML pages; local resources resolve; published metric CSVs valid')

if __name__ == '__main__':
    verify()
