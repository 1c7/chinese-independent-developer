#!/usr/bin/env python3
"""列出「评论里出现、但 README 系列里没有」的产品 URL。

用途：替代按用户名做的「提交者 - 已致谢」差集。
按人去重会漏掉老作者的新投稿（同一个人第二次提另一个产品），按 URL 比对不会。

用法：
  gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100" > /tmp/c160.json
  python3 .github/scripts/pending_submissions.py /tmp/c160.json

退出码：0 = 没有待处理 URL（可以放心空跑）；1 = 有待处理项，逐条进检查一。

注意：本脚本只做「候选筛选」，不判断该不该收录。
作者主页、博客、Twitter 这类链接也会出现在输出里，需要人看一眼跳过。
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERIES = [
    ROOT / "README.md",
    ROOT / ".github" / "pages" / "README-Programmer-Edition.md",
    ROOT / ".github" / "pages" / "README-Game.md",
    ROOT / ".github" / "pages" / "README-Earlier-Projects.md",
    ROOT / ".github" / "pages" / "README-Earlier-Projects-2.md",
]
OURS = {"1c7", "claude[bot]", "github-actions[bot]"}

URL_RE = re.compile(r"https?://[^\s\)\](<>\"'，。、；：！？）：》]+")
# 明显不是产品的东西：只有一段路径的 github 主页、社交平台个人页
NOISE_RE = re.compile(
    r"^(github\.com/[^/]+|"
    r"(www\.)?(x|twitter)\.com/[^/]+|"
    r"t\.me/[^/]+|"
    r"www\.v2ex\.com/member/[^/]+)$"
)


def norm(url: str) -> str:
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"))
    u = re.sub(r"^www\.", "", u)
    return u


def load_series() -> str:
    out = []
    for p in SERIES:
        if p.exists():
            out.append(p.read_text(encoding="utf-8"))
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("用法：python3 .github/scripts/pending_submissions.py <comments.json>")

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]

    readme = load_series()
    readme_norm = norm_all_text(readme)

    seen = set()
    rows = []
    for c in data:
        user = (c.get("user") or {}).get("login", "")
        if user in OURS:
            continue
        body = c.get("body") or ""
        if body.lstrip().startswith("感谢提交") or "已将你的产品" in body:
            continue
        for raw in URL_RE.findall(body):
            u = norm(raw)
            if not u or NOISE_RE.match(u):
                continue
            host = u.split("/")[0]
            # 同一条评论里同一站点的「更多介绍」子路径只报一次
            key = (c.get("id"), host)
            if key in seen:
                continue
            if u in readme_norm or host_in_readme(host, readme_norm):
                continue
            seen.add(key)
            rows.append((c.get("created_at", "")[:16], user, c.get("id"), u, body[:60].replace("\n", " ")))

    if not rows:
        print("无待处理 URL：窗口内所有产品链接都已在 README 系列中。")
        return 0

    rows.sort()
    print(f"待处理 URL {len(rows)} 条（未出现在 README 系列里，需逐条判断）：")
    for ts, user, cid, u, snippet in rows:
        print(f"  {ts}  @{user}  id={cid}\n    {u}\n    {snippet}")
    return 1


def norm_all_text(text: str) -> str:
    """把 README 正文里的 URL 也归一化，便于直接子串比对。"""
    return re.sub(r"https?://(www\.)?", "", text)


def host_in_readme(host: str, readme_norm: str) -> bool:
    """子域或路径写法不一致时，退一步按主机名判断。"""
    return host in readme_norm


if __name__ == "__main__":
    sys.exit(main())
