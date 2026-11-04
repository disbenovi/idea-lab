"""Read-only, dependency-free churn and co-change report for the current repo."""
import argparse
from collections import Counter
from datetime import datetime
from fnmatch import fnmatchcase
from itertools import combinations
import json
from pathlib import PurePosixPath
import subprocess
import sys


DEFAULT_EXCLUDES = ('*.lock', 'package-lock.json', 'npm-shrinkwrap.json',
                    'yarn.lock', 'pnpm-lock.yaml', 'dist/*', 'vendor/*',
                    'build/*', 'node_modules/*', '__pycache__/*')


def excluded(path, patterns):
    # Match generated directories at any depth, not just the repository root.
    parts = path.split('/')
    return any(fnmatchcase('/'.join(parts[i:]), pattern)
               for i in range(len(parts)) for pattern in patterns)


def read_commits(limit=200, since=None):
    command = ['git', '--no-pager', 'log', '--numstat', '-z', '--no-merges',
               '--no-renames', '--no-ext-diff', '--no-textconv',
               '--format=%x00%H%x00%ae%x00%cI', '-n', str(limit)]
    if since is not None:
        command.append('--since=' + since)
    command.append('--')
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=True)
    tokens = iter(result.stdout.decode('utf-8', 'surrogateescape').split('\0'))
    commit = None
    for token in tokens:
        if not token.strip('\n'):
            sha = next(tokens, None)
            if not sha:
                continue
            if commit is not None:
                yield commit
            commit = (next(tokens), next(tokens), [])
        else:
            added, removed, path = token.lstrip('\n').split('\t', 2)
            commit[2].append((path, added, removed))
    if commit is not None:
        yield commit


def analyse(commits, patterns=DEFAULT_EXCLUDES):
    files, directories, together = {}, Counter(), Counter()
    count = 0
    for author, date, changes in commits:
        count += 1
        touched = set()
        for path, added, removed in changes:
            if excluded(path, patterns):
                continue
            item = files.setdefault(path, dict(path=path, commits=0, authors=set(),
                                    added=0, removed=0, last_changed=date))
            item['authors'].add(author)
            if datetime.fromisoformat(date) > datetime.fromisoformat(item['last_changed']):
                item['last_changed'] = date
            # Git reports binary changes as '-', with no measurable line churn.
            item['added'] += 0 if added == '-' else int(added)
            item['removed'] += 0 if removed == '-' else int(removed)
            touched.add(path)
        for path in touched:
            files[path]['commits'] += 1
        directories.update({str(PurePosixPath(path).parent) for path in touched})
        together.update(combinations(sorted(touched), 2))
    hotspots = []
    for item in files.values():
        item['authors'] = len(item['authors'])
        item['churn'] = item['added'] + item['removed']
        item['directory_ratio'] = item['commits'] / directories[str(PurePosixPath(item['path']).parent)]
        item['directory_hotspot'] = item['directory_ratio'] > 0.6
        hotspots.append(item)
    hotspots.sort(key=lambda item: (-item['churn'], item['path']))
    pairs = []
    for (a, b), total in together.items():
        ratio = total / min(files[a]['commits'], files[b]['commits'])
        if total >= 5 and ratio >= 0.6:
            pairs.append(dict(files=[a, b], together=total, ratio=ratio))
    pairs.sort(key=lambda pair: (-pair['together'], -pair['ratio'], pair['files']))
    return dict(commits_analysed=count, hotspots=hotspots, pairs=pairs[:10])


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be greater than zero')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--commits', type=positive, default=200)
    parser.add_argument('--since', metavar='DATE')
    parser.add_argument('--exclude', default='', help='extra comma-separated globs')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    patterns = DEFAULT_EXCLUDES + tuple(p.strip() for p in args.exclude.split(',') if p.strip())
    try:
        report = analyse(read_commits(args.commits, args.since), patterns)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            message = error.stderr.decode('utf-8', 'replace').strip()
        else:
            message = str(error)
        print('git-churn: ' + message, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    else:
        print('Commits analysed:', report['commits_analysed'])
        print('Churn  Commits  Authors  Added  Removed  Last changed  Path (* directory hotspot)')
        for item in report['hotspots']:
            print(item['churn'], item['commits'], item['authors'], item['added'],
                  item['removed'], item['last_changed'], json.dumps(item['path']),
                  '*' if item['directory_hotspot'] else '')
        print('Coupling (at least 5 commits, ratio >= 0.6):')
        for pair in report['pairs']:
            print(pair['together'], f"{pair['ratio']:.3f}", json.dumps(pair['files']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
