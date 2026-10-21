#!/usr/bin/env python3
"""列出窗口内提交评论里「README 系列还没有」的产品，按 域名 + 产品名 两个维度查。

查重只看两件事：**产品域名**、**产品名**。
提交者是谁、他以前投过几次、隔了多久，全部不参与判断——同一个作者跨月跨年反复投稿是常态。

用法：
  gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100" > /tmp/c160.json
  python3 .github/scripts/pending_submissions.py /tmp/c160.json

输出三类：
  [新]     域名和产品名都没命中 → 正常新提交，进检查一
  [同名]   产品名命中、域名没命中 → 重点看：换域名的老产品，还是纯重复
  [无链接] 只有裸 URL 没写产品名 → 仍需人看
退出码：0 = 无待处理；1 = 有待处理项。
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
MD_LINK_RE = re.compile(r"\[([^\]\n]{1,80})\]\((https?://[^)\s]+)\)")
# 不是产品：只有一段路径的 github 主页、社交平台个人页
NOISE_RE = re.compile(
    r"^(github\.com/[^/]+|"
    r"(www\.)?(x|twitter)\.com/[^/]+|"
    r"t\.me/[^/]+|"
    r"www\.v2ex\.com/member/[^/]+)$"
)


def norm_url(url: str) -> str:
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"))
    return re.sub(r"^www\.", "", u)


def norm_name(name: str) -> str:
    """产品名归一化：去空格、括号、引号、中英标点，转小写。"""
    return re.sub(r"[\s\[\]【】()（）「」《》\-_·.,，。、:：/\\|~]", "", name).lower()


def load_series() -> tuple[str, set[str]]:
    text, names = [], set()
    for p in SERIES:
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        text.append(t)
        for m in MD_LINK_RE.finditer(t):
            n = norm_name(m.group(1))
            if len(n) >= 2:
                names.add(n)
    return re.sub(r"https?://(www\.)?", "", "\n".join(text)), names


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("用法：python3 .github/scripts/pending_submissions.py <comments.json>")

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]

    readme_norm, readme_names = load_series()

    seen = set()
    rows = []
    for c in data:
        user = (c.get("user") or {}).get("login", "")
        if user in OURS:
            continue
        body = c.get("body") or ""
        if body.lstrip().startswith("感谢提交") or "已将你的产品" in body:
            continue

        names = {}
        for m in MD_LINK_RE.finditer(body):
            names.setdefault(norm_url(m.group(2)).split("/")[0], m.group(1))

        for raw in URL_RE.findall(body):
            u = norm_url(raw)
            if not u or NOISE_RE.match(u):
                continue
            host = u.split("/")[0]
            key = (c.get("id"), host)  # 同评论同站点的「更多介绍」子路径只报一次
            if key in seen:
                continue
            if u in readme_norm or host in readme_norm:
                continue
            seen.add(key)

            tip_name = names.get(host, "")
            if tip_name and norm_name(tip_name) in readme_names:
                kind = "[同名]"
            elif tip_name:
                kind = "[新]  "
            else:
                kind = "[无链接]"
            rows.append((c.get("created_at", "")[:16], user, c.get("id"), host, tip_name, kind))

    if not rows:
        print("无待处理项：窗口内提交的域名与产品名都已在 README 系列中。")
        return 0

    rows.sort()
    print(f"待处理 {len(rows)} 条（域名与产品名均未在 README 系列命中；[同名] 表示名字已存在、域名不同）：")
    for ts, user, cid, host, name, kind in rows:
        print(f"  {kind} {ts}  @{user}  id={cid}  {host}  「{name or '未命名'}」")
    return 1


if __name__ == "__main__":
    sys.exit(main())
