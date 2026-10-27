#!/usr/bin/env python3
"""把 README.md 末尾最旧的日期区块搬到 .github/pages/README-Earlier-Projects.md。

用法：
  python3 .github/scripts/migrate_archive.py            # 预演，只打印计划，不写文件
  python3 .github/scripts/migrate_archive.py --write    # 真正执行
  python3 .github/scripts/migrate_archive.py --target 487500 --write

规则来源：SKILL.md「步骤3」的容量搬迁小节。
- 一次剪到 --target（默认 487,500），不要只剪到刚好低于 490,000
- 只动要搬的区块，其余内容逐字保留；不对分册做整体重排
- 兼容 `### 2024年4月24日添加`（日）和 `### 2024 年 4 月 24 号添加`（号）两种历史写法
- 同日期重复区块各算各的，不合并
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
ARCHIVE = ROOT / ".github" / "pages" / "README-Earlier-Projects.md"

THRESHOLD = 490_000
DEFAULT_TARGET = 487_500

DATE_RE = re.compile(
    r"^###\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[号日]添加\s*$",
    re.MULTILINE,
)
# 只匹配「## 👉」前缀，兼容 2026-10-27 改名后的「2018 ~ 2025 年收录的项目」
# 与改名前的「更早的项目」两种尾部引路行写法。
TAIL_MARK = "## 👉"


def date_blocks(text):
    """返回 [(start, end, (year, month, day))]，start 是标题行首，end 是下一区块标题行首或文本末尾。"""
    hits = list(DATE_RE.finditer(text))
    out = []
    for i, m in enumerate(hits):
        start = m.start()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out.append((start, end, (int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="真正写文件（默认只预演）")
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET)
    args = ap.parse_args()

    readme = README.read_text(encoding="utf-8")
    archive = ARCHIVE.read_text(encoding="utf-8")
    archive_original = archive

    size_before = len(readme.encode("utf-8"))
    print(f"README.md 当前 {size_before:,} 字节，阈值 {THRESHOLD:,}，目标 {args.target:,}")

    if size_before <= args.target:
        print("已在目标以内，无需搬迁。")
        return 0

    # README = 主体（含日期区块） + 尾部（更早的项目指引、帮助网站等）
    cut = readme.find("\n" + TAIL_MARK)
    if cut < 0:
        sys.exit(f"找不到尾部标记「{TAIL_MARK}」，拒绝执行（避免误剪正文）")
    body, tail = readme[:cut], readme[cut:]

    blocks = date_blocks(body)
    if not blocks:
        sys.exit("README.md 里没解析到任何日期区块，拒绝执行")

    # 从最旧（列表末尾）往前挑，直到剪够
    moving = []
    trimmed = body
    cur = size_before
    for start, end, d in reversed(blocks):
        if cur <= args.target:
            break
        moving.append((start, end, d))
        chunk_len = len(body[start:end].encode("utf-8"))
        cur -= chunk_len
        print(f"  剪出 {d[0]}-{d[1]:02d}-{d[2]:02d}（{chunk_len:,} 字节）")

    if not moving:
        print("没有可剪的区块。")
        return 0

    # 逐个删除（从后往前，索引才不失效）
    for start, end, _ in sorted(moving, key=lambda x: x[0], reverse=True):
        trimmed = trimmed[:start] + trimmed[end:].lstrip("\n")
        # 保持区块之间恰好一个空行
        trimmed = trimmed.rstrip("\n") + "\n\n"

    moved_text = "".join(body[s:e] for s, e, _ in sorted(moving, key=lambda x: x[0])).strip("\n")
    new_readme = trimmed.rstrip("\n") + "\n\n" + tail.lstrip("\n")

    # ---- 插入分册：按日期倒序定位，不整体重排 ----
    a_hits = list(DATE_RE.finditer(archive))
    if not a_hits:
        sys.exit("分册里没解析到日期区块，拒绝执行")

    for start, end, d in moving:
        chunk = body[start:end].strip("\n")
        # 重新定位（archive 在变），找第一个日期比它旧的区块，插到它前面
        hits = list(DATE_RE.finditer(archive))
        insert_at = None
        for i, m in enumerate(hits):
            cur_d = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if cur_d < d:
                insert_at = m.start()
                break
        if insert_at is None:
            # 没有更旧的 → 放到分册末尾
            archive = archive.rstrip("\n") + "\n\n" + chunk + "\n"
        else:
            archive = archive[:insert_at] + chunk + "\n\n" + archive[insert_at:]

    # ---- 更新年份范围文字 ----
    years = [int(m.group(1)) for m in DATE_RE.finditer(archive)]
    if years:
        lo, hi = min(years), max(years)
        new_archive = re.sub(r"（\d{4} 年 ~ \d{4} 年）", f"（{lo} 年 ~ {hi} 年）", archive)
        new_readme2 = re.sub(r"（\d{4} 年 ~ \d{4} 年）", f"（{lo} 年 ~ {hi} 年）", new_readme)
        archive, new_readme = new_archive, new_readme2

    # ---- 完整性校验：行级多重集守恒（两份文件合起来算，防止搬迁过程丢行或重复行） ----
    # 年份范围文字（「（2018 年 ~ 2025 年）」）在搬迁时会被正常改写，校验前归一化掉，
    # 否则第一次搬入新年份的区块时会误报「丢失行」。
    def _norm(lines):
        return Counter(
            re.sub(r"（\d{4} 年 ~ \d{4} 年）", "（YEARS）", l)
            for l in lines.splitlines()
            if l.strip()
        )

    before_lines = _norm(readme + "\n" + archive_original)
    after_lines = _norm(new_readme + "\n" + archive)
    if before_lines != after_lines:
        lost = before_lines - after_lines
        gained = after_lines - before_lines
        print("❌ 行级校验失败，未写入。")
        print("  丢失行样例：", list(lost.items())[:5])
        print("  新增行样例：", list(gained.items())[:5])
        return 1

    print(f"\n预演结果：README.md {size_before:,} → {len(new_readme.encode('utf-8')):,} 字节")
    print(f"分册 {len(ARCHIVE.read_text(encoding='utf-8').encode('utf-8')):,} → {len(archive.encode('utf-8')):,} 字节")
    print(f"搬迁区块 {len(moving)} 个，行级校验通过（无内容丢失）")

    if not args.write:
        print("\n这是预演。确认无误后加 --write 执行。")
        return 0

    README.write_text(new_readme, encoding="utf-8")
    ARCHIVE.write_text(archive, encoding="utf-8")
    print("\n已写入 README.md 与分册。请接着跑：")
    print('  grep -c "^### " README.md .github/pages/README-Earlier-Projects.md')
    print("  git diff --stat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
