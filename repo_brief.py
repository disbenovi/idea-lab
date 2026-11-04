"""Read-only, deterministic repository brief. Python 3.9+, standard library only."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import stat

LANGUAGES = {
    '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.go': 'Go', '.rs': 'Rust',
    '.c': 'C', '.h': 'C', '.cpp': 'C++', '.hpp': 'C++', '.java': 'Java',
    '.rb': 'Ruby', '.sh': 'Shell', '.php': 'PHP', '.swift': 'Swift',
    '.kt': 'Kotlin', '.cs': 'C#', '.html': 'HTML', '.css': 'CSS',
    '.md': 'Markdown', '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML',
    '.toml': 'TOML', '.txt': 'Text',
}
SKIP_DIRS = {'.git', '.hg', '.svn', '.venv', 'venv', 'node_modules',
             '__pycache__', '.pytest_cache', '.mypy_cache', '.ssh', '.config'}
DEPENDENCIES = {'requirements.txt', 'pyproject.toml', 'package.json', 'go.mod'}
TEST_DIRS = {'test', 'tests', '__tests__', 'spec', 'specs'}
READ_LIMIT = 65536


def excluded(name):
    lower = name.lower()
    return (lower == '.env' or lower.startswith('.env.')
            or lower.endswith(('.pem', '.key', '.pyc', '.pyo'))
            or lower in {'.git', '.hg', '.svn', 'credentials', 'credentials.json', 'id_rsa', 'id_ed25519'})


def test_file(path):
    name = path.name.lower()
    return (path.suffix.lower() in {'.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rb'}
            and (name.startswith('test_') or name.endswith(('_test.py', '_test.go',
                 '_spec.rb')) or '.test.' in name or '.spec.' in name
                 or (bool(TEST_DIRS.intersection(path.parts[:-1]))
                     and name not in {'__init__.py', 'conftest.py'})))


def read_text(path, warnings, relative):
    try:
        with path.open('r', encoding='utf-8', errors='replace') as stream:
            text = stream.read(READ_LIMIT + 1)
        if len(text) > READ_LIMIT:
            warnings.add(f'{relative}: text truncated at {READ_LIMIT} characters')
        return text[:READ_LIMIT]
    except OSError:
        warnings.add(f'{relative}: cannot read text')
        return ''


def readme_summary(text):
    lines = text.splitlines()
    heading, heading_lines = None, set()
    for index, line in enumerate(lines):
        match = re.match(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        setext = (index + 1 < len(lines) and line.strip()
                  and re.fullmatch(r'\s*(?:=+|-+)\s*', lines[index + 1]))
        if match or setext:
            heading = match.group(1) if match else line.strip()
            heading_lines = {index} if match else {index, index + 1}
            break
    paragraph = []
    for index, line in enumerate(lines):
        if index in heading_lines or re.match(r'^\s*#{1,6}\s', line):
            if paragraph:
                break
            continue
        if not line.strip():
            if paragraph:
                break
        else:
            paragraph.append(line.strip())
    return {'heading': heading, 'paragraph': ' '.join(paragraph) or None}


def scan(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError('path must be an existing directory')
    files, warnings, test_dirs = [], set(), set()

    def walk_error(error):
        warnings.add(f'{Path(error.filename).relative_to(root).as_posix()}: cannot list directory')

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS
                         and not excluded(d) and not Path(directory, d).is_symlink())
        for child in dirs:
            if child.lower() in TEST_DIRS:
                test_dirs.add((Path(directory) / child).relative_to(root).as_posix())
        for name in sorted(names):
            path = Path(directory, name)
            relative = path.relative_to(root)
            if excluded(name) or path.is_symlink():
                continue
            try:
                info = path.stat()
                if stat.S_ISREG(info.st_mode):
                    files.append((relative, info.st_size))
            except OSError:
                warnings.add(f'{relative.as_posix()}: cannot stat file')
    files.sort(key=lambda item: item[0].as_posix())
    languages = defaultdict(lambda: {'files': 0, 'bytes': 0})
    entries, dependencies, frameworks = set(), [], set()
    for path, size in files:
        language = LANGUAGES.get(path.suffix.lower(), 'Other')
        languages[language]['files'] += 1
        languages[language]['bytes'] += size
        name, relative = path.name, path.as_posix()
        if path.stem.lower() in {'main', '__main__', 'cli'} or 'bin' in path.parts[:-1]:
            entries.add(relative)
        if name in DEPENDENCIES:
            dependencies.append(relative)
        for index, part in enumerate(path.parts[:-1]):
            if part.lower() in TEST_DIRS:
                test_dirs.add(Path(*path.parts[:index + 1]).as_posix())
        if name in {'pytest.ini', 'conftest.py'}:
            frameworks.add('pytest')
        if name.startswith('jest.config.'):
            frameworks.add('Jest')
        if name.startswith('vitest.config.'):
            frameworks.add('Vitest')
        if name.endswith('_test.go'):
            frameworks.add('Go testing')
        if name.endswith('_spec.rb'):
            frameworks.add('RSpec')
        if name == 'package.json':
            try:
                package = json.loads(read_text(root / path, warnings, relative))
                bins = package.get('bin') if isinstance(package, dict) else None
                if isinstance(bins, str):
                    entries.add(f'{relative} bin: {bins}')
                elif isinstance(bins, dict):
                    entries.update(f'{relative} bin {key}: {value}'
                                   for key, value in bins.items() if isinstance(value, str))
            except ValueError:
                warnings.add(f'{relative}: invalid JSON')
        if name == 'Makefile':
            text = read_text(root / path, warnings, relative)
            for line in text.splitlines():
                match = re.match(r'^([A-Za-z0-9_./% -]+):(?!=)', line)
                if match:
                    entries.update(f'{relative} target: {target}'
                                   for target in match.group(1).split()
                                   if not target.startswith('.'))
    readmes = [p for p, _ in files if len(p.parts) == 1
               and (p.name.lower() == 'readme' or p.name.lower().startswith('readme.'))]
    readme = 'absent'
    if readmes:
        path = sorted(readmes, key=lambda p: (p.name.lower() != 'readme.md', p.name))[0]
        readme = {'path': path.as_posix(), **readme_summary(
            read_text(root / path, warnings, path.as_posix()))}
    return {
        'languages': [{'language': name, **counts} for name, counts in sorted(
            languages.items(), key=lambda item: (-item[1]['files'], -item[1]['bytes'], item[0]))[:5]],
        'entry_points': sorted(entries),
        'largest_files': [{'path': path.as_posix(), 'bytes': size} for path, size in
                          sorted(files, key=lambda item: (-item[1], item[0].as_posix()))[:10]],
        'test_dirs': sorted(test_dirs), 'test_frameworks': sorted(frameworks) or ['unknown'],
        'test_files': sum(test_file(path) for path, _ in files),
        'dependency_files': dependencies, 'readme': readme, 'warnings': sorted(warnings),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--json', action='store_true', help='emit structured JSON')
    args = parser.parse_args()
    try:
        brief = scan(args.path)
    except ValueError as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(brief, indent=2, ensure_ascii=True))
    else:
        print('Repository brief')
        for key, value in brief.items():
            print(f'{key}: {json.dumps(value, ensure_ascii=True)}')


if __name__ == '__main__':
    main()
