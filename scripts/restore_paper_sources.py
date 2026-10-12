"""Restore the versioned paper, retaining a byte-for-byte backup of overwritten files."""
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    revision = git('rev-parse', 'origin/main').decode().strip()
    names = git('ls-tree', '-r', '--name-only', revision).decode().splitlines()
    selected = [name for name in names if name != 'tmp/paper.txt']
    backup = ROOT/'docs/maintenance/pre-paper-restoration.zip'
    if backup.exists():
        raise ValueError('Restoration already started; inspect its receipt')
    with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in selected:
            path = ROOT/name
            if path.is_file():
                archive.write(path, name)
        for name in ('01_data_exploration.qmd', '02_modeling.qmd', 'custom.scss'):
            archive.write(ROOT/name, name)
    shutil.copyfile(ROOT/'index.qmd', ROOT/'data_coverage.qmd')
    shutil.copyfile(ROOT/'scripts/verify_site.py', ROOT/'scripts/verify_dashboard.py')
    for name in selected:
        target = ROOT/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git('show', f'{revision}:{name}'))
    for name in ('01_data_exploration.qmd', '02_modeling.qmd', 'custom.scss'):
        (ROOT/name).unlink()  # Exact files saved in the backup above.
    receipt = {'source_commit': revision, 'restored_paths': selected, 'backup': str(backup),
               'supplementary_pages': ['data_coverage.qmd', 'naics_explorer.qmd']}
    (ROOT/'docs/maintenance/paper-restoration.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('PAPER SOURCES RESTORED:', revision, len(selected), 'files')


if __name__ == '__main__':
    main()
