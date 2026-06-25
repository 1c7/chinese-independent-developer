---
name: chinese-indie-dev
description: >
  处理 1c7/chinese-independent-developer 仓库的项目提交。
  检查 issue #160 新评论、新开的 Issue、新开的 PR，
  将有效项目添加到对应 README，关闭垃圾内容。
  当用户说"处理提交"、"处理 issue"、"跑一下列表"时使用。
metadata:
  author: 1c7
  version: "1.1"
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

⚠️ 严格禁止：不得调用添加 reaction 的 API。

⚠️ 严格禁止：不得以任何理由删除或修改 README 中已有的条目。本 skill 的唯一允许操作是**新增**。如果发现疑似重复，只需跳过，绝对不能删除。

---

## 预检：快速判断是否有任何新内容

**在做任何实质处理之前**，先并行运行以下三条命令，统计各自的结果数量：

```bash
SINCE=$(date -u -d '7 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7H +%Y-%m-%dT%H:%M:%SZ)

# 检查一：#160 新评论数
COUNT_COMMENTS=$(gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100" | jq 'length')

# 检查二：新 Issue 数
COUNT_ISSUES=$(gh api "repos/1c7/chinese-independent-developer/issues?state=open&per_page=50" \
  | jq --arg since "$SINCE" '[.[] | select(.number != 160 and .pull_request == null and .created_at >= $since)] | length')

# 检查三：待处理 PR 数（排除 auto-add- 分支）
COUNT_PRS=$(gh api "repos/1c7/chinese-independent-developer/pulls?state=open&per_page=50" \
  | jq '[.[] | select(.head.ref | startswith("auto-add-") | not)] | length')

echo "新评论: $COUNT_COMMENTS  新Issue: $COUNT_ISSUES  待处理PR: $COUNT_PRS"
```

如果三个数字**全部为 0**，立即输出「无新内容，本次运行结束」，然后**停止，不再执行后续任何步骤**。

只要有任意一个数字 > 0，才继续向下执行。

---

## 检查一：issue #160 的新评论

获取最近 7 小时内的评论（每 6 小时运行一次，留 1 小时余量）：

```bash
SINCE=$(date -u -d '7 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7H +%Y-%m-%dT%H:%M:%SZ)
gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100"
```

对每条评论，从内容中提取产品 URL，检查是否已在任意 README 中：

```bash
grep -rF "<产品完整URL>" README.md pages/README-Programmer-Edition.md pages/README-Game.md
```

⚠️ 去重规则（必须严格遵守）：
- 必须用产品的**完整 URL**（如 `https://example.com`）做精确字符串匹配，使用 `grep -F`（固定字符串，非正则）
- 禁止用产品名称、描述文字或部分关键词判断重复——描述里提到某个工具名不等于该工具已在列表中
- URL 已存在 → 跳过，对 README 不做任何操作
- URL 不存在 → 进入「通用处理流程」
- 当前运行中已通过 PR 合并的条目，视为已存在，不再重复处理

处理完所有检查一的评论后，记录所有成功处理的评论作者用户名（用于最后一步发感谢评论到 #160）。

---

## 检查二：最近 7 小时内开启的新 Issue（非 #160）

```bash
SINCE=$(date -u -d '7 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7H +%Y-%m-%dT%H:%M:%SZ)
gh api "repos/1c7/chinese-independent-developer/issues?state=open&per_page=50" \
  | jq --arg since "$SINCE" \
    '[.[] | select(.number != 160 and .pull_request == null and .created_at >= $since)]'
```

判断每个 Issue：
- **有效项目提交**（含产品名 + 可访问 URL）→ 进入「通用处理流程」，完成后：
  1. 在**该 issue 本身**（不是 #160！）发感谢评论，立即捕获 ID 并 PATCH 去掉自动追加的署名：
     ```bash
     CLEAN_BODY="@<提交者用户名> 感谢提交，已添加！"
     COMMENT_RESPONSE=$(gh api repos/1c7/chinese-independent-developer/issues/<number>/comments \
       -X POST -f body="$CLEAN_BODY")
     COMMENT_ID=$(echo "$COMMENT_RESPONSE" | jq -r '.id')
     gh api --method PATCH \
       repos/1c7/chinese-independent-developer/issues/comments/$COMMENT_ID \
       -f body="$CLEAN_BODY"
     ```
  3. 关闭 issue：`gh issue close <number>`
- **垃圾广告、无关内容、内容不清晰** → 直接关闭：`gh issue close <number>`

检查二的提交者不需要在最后一步中 @ 到 #160，他们已在各自的 issue 里收到了感谢。

---

## 检查三：所有未关闭的 PR（排除 auto-add- 分支）

直接获取所有 open 状态的 PR（不限时间，确保不遗漏）：

```bash
gh api "repos/1c7/chinese-independent-developer/pulls?state=open&per_page=50" \
  | jq '[.[] | select(.head.ref | startswith("auto-add-") | not)]'
```

判断每个 PR：
- **有效项目提交**（对 README 的修改，含产品名 + URL）→ 直接合并：
  ```bash
  gh pr merge <number> --squash --yes
  ```
  - 如果合并成功：在该 PR 发感谢评论，立即捕获 ID 并 PATCH 去掉署名：
    ```bash
    CLEAN_BODY="@<提交者用户名> 感谢提交，已合并！"
    PR_COMMENT_RESPONSE=$(gh api repos/1c7/chinese-independent-developer/issues/<number>/comments \
      -X POST -f body="$CLEAN_BODY")
    PR_COMMENT_ID=$(echo "$PR_COMMENT_RESPONSE" | jq -r '.id')
    gh api --method PATCH \
      repos/1c7/chinese-independent-developer/issues/comments/$PR_COMMENT_ID \
      -f body="$CLEAN_BODY"
    ```
  - 如果合并失败（如 merge conflict）：在该 PR 发评论说明原因，**不要**通过通用处理流程重新提交，不要关闭 PR，让提交者自己解决冲突
- **垃圾广告、无关内容** → 直接关闭：`gh pr close <number>`

⚠️ 严格禁止：检查三的 PR 绝对不能走通用处理流程（那样会丢失贡献者的 git 归属）。

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
| 程序员版面 | 需要命令行/写代码/安装依赖 | pages/README-Programmer-Edition.md |
| 游戏版面 | 任何游戏类产品 | pages/README-Game.md |
| 拒绝 | 论坛、无 URL、垃圾广告、无法判断 | 不处理 |

### 步骤3：插入文件并批量提交到 master

先用 Read 工具读取目标 README 了解格式，用 Edit 工具插入条目。**新条目插入当天日期区块的最顶部**（紧接日期标题行之后的空行后面）。

如果当天日期区块尚不存在，则在最新日期区块之前新建。

**所有项目的文件修改全部做完后**，统一一次性提交推送到 master：

```bash
git checkout master && git pull origin master
# （用 Edit 工具对各 README 文件做完所有修改）
git add README.md pages/README-Programmer-Edition.md pages/README-Game.md
git commit -m "新增：<项目1名>、<项目2名>、..."
git push origin master
```

- 不建分支，不开 PR，直接推 master
- 所有项目合为一条 commit，commit message 列出所有项目名
- 如果本次没有任何有效项目，跳过 git 操作

### 步骤4：给评论添加 reaction（仅限检查一的评论）

每条成功处理的 issue #160 评论，添加 👍 reaction 标记已处理：

```bash
gh api repos/1c7/chinese-independent-developer/issues/comments/<COMMENT_ID>/reactions \
  -X POST -f content="+1"
```

---

## 最后一步：发感谢评论并删除 Claude 署名（仅针对检查一的提交者）

所有三个检查都处理完之后，如果检查一中成功合并了至少一个项目，在 issue #160 发一条感谢评论，一次性 @ 所有**来自检查一**的成功处理的提交者：

```bash
gh api repos/1c7/chinese-independent-developer/issues/160/comments \
  -X POST -f body="@user1 @user2 感谢提交，已添加！"
```

- 只发一条，不要逐人发多条
- 检查二的提交者不要 @ 到这里（他们已在各自的 issue 里收到了感谢）
- 如果检查一没有成功处理任何项目，不发评论

Claude Code 会自动在正文末尾追加署名，必须 POST 后立即 PATCH 覆写。用以下模式，把 POST 和 PATCH 写在同一个代码块里确保 ID 被捕获：

```bash
CLEAN_BODY="@user1 @user2 感谢提交，已添加！"
COMMENT_RESPONSE=$(gh api repos/1c7/chinese-independent-developer/issues/160/comments \
  -X POST -f body="$CLEAN_BODY")
COMMENT_ID=$(echo "$COMMENT_RESPONSE" | jq -r '.id')
gh api --method PATCH \
  repos/1c7/chinese-independent-developer/issues/comments/$COMMENT_ID \
  -f body="$CLEAN_BODY"
```

---

## 注意事项

- 幂等性靠 URL grep 检查保证，不依赖 reaction 标记
- 所有文件修改完成后统一一次 commit 推 master，不建分支、不开 PR
- 三个检查都没有新内容时，直接结束
