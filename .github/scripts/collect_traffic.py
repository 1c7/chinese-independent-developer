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
    history_path = output / 'daily.json'
    previous = json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else []
    history = merge_daily(previous, payloads['views'], payloads['clones'])
    now = datetime.now(timezone.utc)
    snapshot = {'repository': repository, 'collected_at': now.isoformat(),
                'timezone': 'UTC', **payloads}
    # One snapshot per UTC date; manual reruns refresh that day's snapshot.
    save_json(output / 'snapshots' / f'{now:%Y-%m-%d}.json', snapshot)
    save_json(history_path, history)
    save_json(output / 'latest.json', snapshot)
    text = [f'# {repository} 流量存档', '', f'最后采集：{now:%Y-%m-%d %H:%M UTC}', '',
            '每周自动采集，也可随时在 Actions 手动运行。全部日期按 UTC。', '',
            '- `daily.json`：按日期合并的浏览/克隆历史，重叠日期更新而非相加。',
            '- `latest.json`：最新原始数据，保留 GitHub 的窗口去重统计。',
            '- `snapshots/`：每次采集的原始窗口，同一天重跑会更新当天快照。', '',
            '来源和热门页面是最近 14 天的前十名快照，不能跨快照相加。',
            '每日独立人数不能相加当成跨日去重人数；缺失日期不填零。', '',
            '| 日期 UTC | 浏览次数 | 独立访客 | 克隆次数 | 独立克隆者 |',
            '|---|---:|---:|---:|---:|']
    for row in history[-30:]:
        cells = [row['date']] + [str(row.get(k, '—')) for k in
                                ('views', 'views_uniques', 'clones', 'clones_uniques')]
        text.append('| ' + ' | '.join(cells) + ' |')
    (output / 'README.md').write_text('\n'.join(text) + '\n', encoding='utf-8')
    print(f'Saved {len(history)} dates to {output}; latest view date: ' +
          max((x['timestamp'][:10] for x in payloads['views']['views']), default='none'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get('GH_TOKEN')
    if not token or not args.repository:
        parser.error('GH_TOKEN and --repository (or GITHUB_REPOSITORY) are required')
    collect(args.repository, args.output, token)
