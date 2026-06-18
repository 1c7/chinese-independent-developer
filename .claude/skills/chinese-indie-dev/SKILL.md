---
name: chinese-indie-dev
description: >
  处理 1c7/chinese-independent-developer 仓库的项目提交。
  检查 issue #160 新评论、新开的 Issue、新开的 PR，
  将有效项目添加到对应 README，关闭垃圾内容。
  当用户说"处理提交"、"处理 issue"、"跑一下列表"时使用。
metadata:
  author: 1c7
  version: "1.0"
  lang: zh-CN
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
---

# 中国独立开发者列表：处理项目提交

你的任务是处理 GitHub 仓库 `1c7/chinese-independent-developer` 的项目提交。
检查最近的新评论、新 Issue、新 PR，将有效项目添加到对应 README，关闭垃圾内容。

⚠️ 严格禁止：不得向任何 issue 或 PR 发表评论。不得调用添加 reaction 的 API。

---

## 检查一：issue #160 的新评论

获取最近 3 天内的评论：

```bash
SINCE=$(date -u -d '3 days ago' +%Y-%m-%dT%H:%M:%SZ)
gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100"
```

对每条评论，从内容中提取产品 URL，检查是否已在任意 README 中：

```bash
grep -r "<产品URL>" README.md README-Programmer-Edition.md README-Game.md
```

已存在则跳过。不存在则进入「通用处理流程」。

---

## 检查二：最近 2 小时内开启的新 Issue（非 #160）

```bash
gh api "repos/1c7/chinese-independent-developer/issues?state=open&per_page=50" \
  | jq --arg since "$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
    '[.[] | select(.number != 160 and .pull_request == null and .created_at >= $since)]'
```

判断每个 Issue：
- **有效项目提交**（含产品名 + 可访问 URL）→ 进入「通用处理流程」，完成后关闭：`gh issue close <number>`
- **垃圾广告、无关内容、内容不清晰** → 直接关闭：`gh issue close <number>`

---

## 检查三：最近 2 小时内开启的新 PR（排除 auto-add- 分支）

```bash
gh api "repos/1c7/chinese-independent-developer/pulls?state=open&per_page=50" \
  | jq --arg since "$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)" \
    '[.[] | select((.head.ref | startswith("auto-add-") | not) and .created_at >= $since)]'
```

判断每个 PR：
- **有效项目提交**（对 README 的修改，含产品名 + URL）→ 直接合并：`gh pr merge <number> --squash --delete-branch --yes`
- **垃圾广告、无关内容** → 直接关闭：`gh pr close <number>`

---

## 通用处理流程（适用于检查一和检查二）

### 步骤1：提取信息并格式化

从原始内容智能提取，整理为标准格式。提交格式千奇百怪，需灵活判断：

**必须有（缺则归入拒绝类）：**
- 制作者名字：用户没写则用其 GitHub 用户名代替
- 产品名称 + 可访问的产品 URL（http/https 开头）+ 一句话描述

**可选（有则填，无则略去）：**
- 城市、GitHub 链接、博客链接、更多介绍链接

**标准输出格式：**
```
#### 制作者名字(城市) - [Github](url)
* :white_check_mark: [产品名](url)：一句话描述 - [更多介绍](url)
```

**格式规范：**
- 日期区块标题用北京时间：`TZ=Asia/Shanghai date +"%Y 年 %-m 月 %-d 号添加"`
- 描述末尾不加句号
- 去掉「高效、简洁、强大、快速、好用、一款、一个」等营销废话；「免费」若是核心特征则保留
- 产品名称提升到最前面
- 严禁使用加粗格式（不要用 **）

### 步骤2：分类

| 类别 | 判断标准 | 目标文件 |
|------|---------|----------|
| 主版面 | 打开即用的网站或 App，非游戏 | README.md |
| 程序员版面 | 需要命令行/写代码/安装依赖 | README-Programmer-Edition.md |
| 游戏版面 | 任何游戏类产品 | README-Game.md |
| 拒绝 | 论坛、无 URL、垃圾广告、无法判断 | 不处理 |

### 步骤3：插入文件并建 PR 合并

先用 Read 工具读取目标 README 了解格式，用 Edit 工具插入条目。每个项目建独立分支：

```bash
# 每次建分支前先拉取最新 master
git checkout master && git pull origin master
BRANCH="auto-add-$(date +%Y%m%d-%H%M%S)"
git checkout -b $BRANCH
# Edit 工具修改文件后：
git add <文件名>
git commit -m "新增：<项目名>"
git push origin $BRANCH
gh pr create --title "新增：<项目名>" --body "来自 <原始链接>" --base master --head $BRANCH
gh pr merge $BRANCH --squash --delete-branch --yes
```

---

## 注意事项

- 幂等性靠 URL grep 检查保证，不依赖 reaction 标记
- 同一批次多个项目，每个分别建独立分支和 PR，建分支前必须先 `git checkout master && git pull`
- 三个检查都没有新内容时，直接结束
