"""Keep historical public pages that are absent from this source checkout."""
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'd28b31e7ba393d49df80a82c94f8b0d2cee81664'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    if subprocess.run(['git', 'cat-file', '-e', BASELINE], cwd=ROOT, capture_output=True).returncode:
        subprocess.run(['git', 'fetch', '--depth=1', 'origin', BASELINE], cwd=ROOT, check=True)
    count = 0
    for name in git('ls-tree', '-r', '--name-only', BASELINE).decode().splitlines():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Invalid baseline path')
        target = ROOT/'_site'/name
        if target.exists():
            continue
        raw = git('show', f'{BASELINE}:{name}')
        if name.endswith('.html') and len(path.parts) == 1:
            html = raw.decode('utf8')
            banner = '<aside style="padding:1rem;background:#fff3cd;color:#332700">Historical analysis from the previous publication. Its samples and results are separate from the current full datasets. <a href="index.html">See current dataset counts and coverage</a>.</aside>'
            html, replacements = re.subn(r'(<body\b[^>]*>)', lambda m: m[1] + banner, html, count=1, flags=re.I)
            if replacements != 1:
                raise ValueError('Cannot label historical page: ' + name)
            raw = html.encode('utf8')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        count += 1
    print(f'HISTORICAL PAGES PRESERVED: {count} missing files restored from {BASELINE}')


if __name__ == '__main__':
    main()
