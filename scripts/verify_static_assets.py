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
