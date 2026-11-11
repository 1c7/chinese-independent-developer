#!/usr/bin/env python3
"""Archive GitHub traffic using only the Python standard library."""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(repository, endpoint, token):
    request = Request(
        f"https://api.github.com/repos/{repository}/{endpoint}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(
                    f"{endpoint}: HTTP {exc.code}. Check token access; traffic requires "
                    "repository Administration: read permission."
                ) from None
        except (URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError(f"{endpoint}: request failed after 3 attempts") from None
        time.sleep(2 ** (attempt + 1))


def merge_daily(previous, views, clones):
    # Replace overlapping dates, never sum overlapping 14-day windows.
    result = {row['date']: dict(row) for row in previous}
    for metric, payload in [('views', views), ('clones', clones)]:
        for item in payload[metric]:
            day = item['timestamp'][:10]
            row = result.setdefault(day, {'date': day})
            row[metric] = item['count']
            row[f'{metric}_uniques'] = item['uniques']
    return [result[day] for day in sorted(result)]


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def collect(repository, output, token):
    # Fetch everything before writing so a failed endpoint cannot produce partial data.
    endpoints = {'views': 'traffic/views?per=day', 'clones': 'traffic/clones?per=day',
                 'referrers': 'traffic/popular/referrers', 'paths': 'traffic/popular/paths'}
    payloads = {name: fetch(repository, endpoint, token) for name, endpoint in endpoints.items()}
    for name in ('views', 'clones'):
        data = payloads[name]
        if not isinstance(data, dict) or not isinstance(data.get(name), list):
            raise RuntimeError(f'Unexpected {name} response')
        for item in data[name]:
            datetime.strptime(item['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            if any(type(item.get(key)) is not int or item[key] < 0 for key in ('count', 'uniques')):
                raise RuntimeError(f'Invalid {name} counts')
    for name in ('referrers', 'paths'):
        if not isinstance(payloads[name], list):
            raise RuntimeError(f'Unexpected {name} response')
    archive_path = output / 'traffic.json'
    archive = json.loads(archive_path.read_text(encoding='utf-8')) if archive_path.exists() else {}
    if archive and archive['repository'] != repository:
        raise RuntimeError('Archive belongs to another repository')
    history = merge_daily(archive.get('daily', []), payloads['views'], payloads['clones'])
    now = datetime.now(timezone.utc)
    snapshots = archive.get('snapshots', {})
    # Keep rolling-window totals/sources as snapshots; never sum them across runs.
    snapshots[f'{now:%Y-%m-%d}'] = {'collected_at': now.isoformat(), **payloads}
    save_json(archive_path, {'repository': repository, 'timezone': 'UTC',
                            'updated_at': now.isoformat(), 'daily': history,
                            'snapshots': snapshots})
    print(f'Saved {len(history)} dates in traffic.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get('GH_TOKEN')
    if not token or not args.repository:
        parser.error('GH_TOKEN and --repository (or GITHUB_REPOSITORY) are required')
    collect(args.repository, args.output, token)
