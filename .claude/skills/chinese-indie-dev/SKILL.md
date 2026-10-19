---
name: chinese-indie-dev
description: >
  处理 1c7/chinese-independent-developer 仓库的项目提交。
  检查 issue #160 新评论、新开的 Issue、新开的 PR，
  将有效项目添加到对应 README，关闭垃圾内容，并把评论区的意见与建议上报维护者。
  当用户要求“收录项目”“处理提交”“处理 issue”“跑一下列表”或运行中国独立开发者列表维护流程时使用。
---

# 中国独立开发者列表：处理项目提交

处理 `1c7/chinese-independent-developer` 的项目提交：扫 #160 评论、open issue、open PR，有效的收进对应 README，无效的按类别拒绝，评论区里的意见与建议单独上报。

**阅读顺序**：本文是流程和硬约束，每次运行完整读一遍。本文写「→ 判例：X」的地方，是历史上踩过的坑，遇到对应情况再去读 `references/precedents.md` 的 X 节，**不要在执行时全量加载判例库**。

## 硬红线（与任何下文冲突时，以本节为准）

1. **不得调用添加 reaction 的 API。**
2. **不得删除或修改他人已有条目**；唯一例外是产品作者本人要求更新自己的条目（换 URL、改描述）。
3. **合并 PR 前必须 `gh pr diff` 逐行审查**，diff 里出现删他人条目的 `-` 行，一律先恢复再合并，绝不让删除落进 master。
4. **所有 GitHub 操作只能走 shell 里的 `gh` / `git`**，保证用的是维护者 1c7 的 PAT；不用 GitHub Connector 或平台原生 GitHub 工具。本地文件读写用当前运行环境自带的工具。
5. **格式问题绝不能作为拒绝 / 关闭理由。** 允许拒绝的只有：垃圾广告、非中国开发者、大厂产品、返佣链接、刷量平台。
6. **状态图标、描述文字以提交者为准。** 提交者写 🕗 就是 `:clock8:`，不许改成 ✅；不许拿官网资料重写他的简介。
7. **版面名称固定写「主版面」「程序员版面」「游戏版面」**，带「面」字。
8. **每一次拒绝都必须在最终汇报里单列**，不许悄悄处理掉；致谢评论不用列。
9. **评论区里的意见与建议只上报、不处置**：不改、不删、不回复、不关闭。
10. 版面判断必须点开产品链接实际看一眼，不能凭标题猜。

---

## 0. 预检

### 0.1 环境自检（先跑这个，不通过就停）

```bash
git status --short                                                   # 必须为空
git fetch origin master && git rev-list --count HEAD..origin/master   # 必须为 0
gh auth status | head -5                                             # 必须是 1c7 本人的 PAT
```

- 落后远端 → `git pull --rebase origin master` 再开始。
- 工作区有改动 → 多半是上次运行中断，先 `git diff` 看清是补完还是丢弃，不要直接 `checkout --`。

### 0.2 三个计数

```bash
SINCE=$(date -u -d '72 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-72H +%Y-%m-%dT%H:%M:%SZ)

COUNT_COMMENTS=$(gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100" | tee /tmp/c160.json | jq 'length')
COUNT_ISSUES=$(gh api "repos/1c7/chinese-independent-developer/issues?state=open&per_page=50" \
  | jq '[.[] | select(.number != 160 and .pull_request == null)] | length')
COUNT_PRS=$(gh api "repos/1c7/chinese-independent-developer/pulls?state=open&per_page=50" \
  | jq '[.[] | select(.head.ref | startswith("auto-add-") | not)] | length')

echo "新评论: $COUNT_COMMENTS  新Issue: $COUNT_ISSUES  待处理PR: $COUNT_PRS"
wc -c README.md
```

- 时间窗统一 **72 小时**（运行间隔不固定，取 3 天余量）。距上次超过 3 天就临时改 `-v-240H`。
- 评论数偏大是正常的：里面混着我们自己的致谢。
- **三个数字全为 0 不等于收工**：仍要跑 0.3 的差集、检查一之二、收尾扫描。

### 0.3 差集（不能只凭"看着都处理过"）

```bash
jq -r '.[] | select(.user.login != "1c7" and .user.login != "claude[bot]") | .user.login' /tmp/c160.json | sort -u > /tmp/submitters.txt
jq -r '.[] | select(.user.login == "1c7" or .user.login == "claude[bot]") | .body' /tmp/c160.json \
  | grep -oE '^@[A-Za-z0-9-]+' | tr -d '@' | sort -u > /tmp/thanked.txt
comm -23 /tmp/submitters.txt /tmp/thanked.txt
```

差集非空 → 逐条进检查一。**差集为空也不代表没有新提交**：差集按用户名去重，老作者的二次投稿会被整个遮掉（→ 判例：F）。必须再逐条核对「窗口内每条非致谢评论之后，有没有 @ 到他的回复」。

---

## 1. 检查一：#160 的新评论

```bash
SINCE=$(date -u -d '72 hours ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-72H +%Y-%m-%dT%H:%M:%SZ)
gh api "repos/1c7/chinese-independent-developer/issues/160/comments?since=$SINCE&per_page=100"
```

对每条评论提取产品 URL，查是否已在任一分册：

```bash
grep -rF "<产品完整URL>" README.md .github/pages/README-Programmer-Edition.md .github/pages/README-Game.md
```

**去重规则**
- 必须用完整 URL 精确匹配（`grep -F`），禁止用产品名或关键词判断重复。
- URL 已存在 → 跳过，且**不发致谢**（说「已添加」会误导）。
- URL 不存在 → 进「通用处理流程」。
- 本次运行中已通过 PR 合并的条目视为已存在。
- 同一产品换域名不算拒绝理由，照常收录，但描述必须写出它独有的功能点（→ 判例：F）。

**72h 窗口重叠**：被判「拒绝」的评论不会在 README 留痕迹，URL 去重挡不住重复处理。发拒绝回复前先查这条评论之后有没有我们 `@` 该提交者的回复：

```bash
gh api "repos/1c7/chinese-independent-developer/issues/160/comments?per_page=100" \
  | jq --arg since "<该评论created_at>" \
    '[.[] | select(.created_at > $since and (.user.login=="1c7" or .user.login=="claude[bot]"))]'
```

处理完记录：作者用户名、产品名、目标版面（供第 7 步逐人致谢）。

---

## 1b. 检查一之二：评论区的意见与建议（只上报，不处理）

> 维护者很少回看原文，这类内容不上报等于消失。**每次运行都跑，空跑也跑。**

拉 #160 最新 200 条评论，排除我们自己：

```bash
TOTAL=$(gh api repos/1c7/chinese-independent-developer/issues/160 --jq .comments)
LAST=$(( (TOTAL + 99) / 100 ))
for p in $((LAST-1)) $LAST; do
  gh api "repos/1c7/chinese-independent-developer/issues/160/comments?per_page=100&page=$p"
done | jq -s 'add' \
  | jq -r '.[] | select(.user.login != "1c7" and .user.login != "claude[bot]")
           | "\(.created_at[0:10])\t\(.id)\t@\(.user.login)\n\(.body[0:300])\n---"'
```

⚠️ 单 issue 评论接口的 `sort`/`direction` **无效**、`per_page>100` 会截断并返回**最早**的一批。必须按上面的算法倒着取页（→ 判例：J）。

**判据**：有没有「产品名 + 可访问 URL + 描述」三元组？有 → 是提交，走检查一。没有、说的是列表本身 → 属于本节。

典型内容：指出描述过时/链接失效/分类放错/作者不是中国人/是返佣或刷量站；要求修改或下架自己的条目；质疑收录标准；抱怨重复、排序、分册、格式；建议加版面或字段；版权侵权投诉；对运营方式的不满。

**动作（硬约束）**
- 不改任何条目、不删、不回复、不关闭、不发 reaction。
- 只登记：链接（`https://github.com/1c7/chinese-independent-developer/issues/160#issuecomment-<id>`）、作者、时间、原文摘要（保留原措辞，不改写成中性描述）、类别 + 建议选项。
- 涉及版权/侵权/法律、要求删他人条目、指认刷量返佣 → 标「紧急」，汇报里置顶。
- 不许因为「语气冲」「像广告」就当噪音忽略；也不许顺手替他改了再报「已处理」。
- 已上报的 comment id 记进 automation memory 的「已上报意见评论 id」，下次先排除。

---

## 2. 检查二：所有未关闭的 Issue（排除 #160）

不限时间窗（2026-10-19 调整）：原来只查「最近 72 小时开启」的 issue，一旦某次运行没跑到这步，issue 就永久滑出窗口、再也不会被看到。

```bash
gh api "repos/1c7/chinese-independent-developer/issues?state=open&per_page=50" \
  | jq '[.[] | select(.number != 160 and .pull_request == null)]'
```

- **有效提交** → 进通用处理流程 → 在**该 issue 本身**（不是 #160）发致谢并 PATCH 验证 → **关闭 issue（不能漏）**。
- **垃圾广告、无关内容** → `gh issue close <number>`。
- **对列表本身的意见 / 纠错 / 投诉** → **不是垃圾，不许关**。保持 open，按 1b 的格式登记进汇报。
- **内容不清、信息缺漏** → 不是关闭理由，尽力提取收录；确属纯广告无任何可定位产品才关。
- **确凿是老外** → 按第 4 步拒绝流程。
- 明显是维护者自己的公告 / 征集 / 置顶帖 → 标注后跳过，不关闭。

检查二的提交者已在各自 issue 收到致谢，不需要在第 7 步再 @。

---

## 3. 检查三：所有未关闭的 PR（排除 auto-add- 分支）

```bash
gh api "repos/1c7/chinese-independent-developer/pulls?state=open&per_page=50" \
  | jq '[.[] | select(.head.ref | startswith("auto-add-") | not)]'
```

每个 PR 的处理顺序：

1. `gh pr diff <number>` **逐行看**。有删他人条目的 `-` 行 → 先恢复（`maintainer_can_modify` 为 true 就推到贡献者分支；否则本地合并时恢复），让最终 diff 回到纯新增（→ 判例：G）。
2. 新增行若落在「### 子版面」清单里 → 照常合并，合并后单独 commit 挪到正确位置（普通产品进当天日期区块；基于本列表数据源的产品进 README 底部专属区块）。
3. `gh pr merge <number> --squash`。报 `Base branch was modified` 不是真失败，`sleep 5` 后重查 `mergeable/mergeable_state`，`true`/`clean` 就重试一次（→ 判例：G）。
4. 合并成功后在该 PR 发致谢（POST → PATCH → GET），说清收录到哪个版面。
5. 合并失败（冲突）：**由我们解决，绝不要求提交者 rebase**。优先改他分支再 `--merge`；推不了才本地 `git merge --no-ff` + `git push` + `gh pr close` 兜底（→ 判例：G）。冲突复杂到分不清该保留什么（不只是新增条目，而是改了已有结构）→ **不要瞎猜、不要删任何已有内容**，在 PR 里说明冲突原因、保持打开等人工介入。

```bash
# maintainer_can_modify=true：改他的分支，让 PR 保持紫色 Merged
git fetch origin master
git fetch origin pull/<number>/head:pr-<number>
git checkout pr-<number> && git merge origin/master --no-edit
# 手工解决冲突：双方新增的条目都保留，冲突标记清干净
git add <冲突文件> && git commit --no-edit
git push "<head.repo.clone_url>" "pr-<number>:<head.ref>"
gh pr merge <number> --merge

# 推不了才兜底（PR 会显示为 Closed，评论里不要提这件事）
git fetch origin master && git fetch origin pull/<number>/head:pr-<number>
git checkout master && git reset --hard origin/master
git merge pr-<number> --no-ff -m "合并 PR #<number>：<项目名>"
git push origin master && gh pr close <number>
```

6. 合并后：跑 `wc -c README.md` 容量检查；格式硬伤单独发整理 commit；当天区块顺序不对另发排序 commit。

- 多个 PR 必须**串行**，每处理完一个立即 `git fetch origin master`。禁止「手动誊抄 + 批量关闭」。
- PR 写错版面 → 照常合并，再单独 commit 搬到正确文件。
- 格式乱 → 不是关闭理由，合并后整理。

---

## 4. 身份判断：只收中国独立开发者

默认**能收就收**，只有确凿证据是老外才拒绝。满足任一条即判为中国人：

1. 中文留言，通顺自然，不是机翻腔。
2. 名字是拼音或明显中国人姓名（含港澳台）。
3. GitHub 主页有中国元素：中文 bio、中文仓库描述、location 写中国城市。

```bash
gh api users/<username> | jq '{name, bio, location}'
gh api "users/<username>/repos?sort=updated&per_page=10" | jq '[.[] | {name, description}]'
```

- 不能只看单一信号；`name` 是外文名但仓库全中文 → 收（→ 判例：A）。
- `location` 在国外不能单独当拒绝依据，中国留学生照样收；写中国城市也不能单独当收录依据。
- 三条都拿不到结论 → **照常收录**，不要为了稳妥而拒。

**确凿是老外时的处理**：检查一不收录、只在评论下礼貌说明；检查二礼貌评论后关闭 issue；检查三礼貌评论后关 PR（不用 merge）。用提交者的语言，只给结论不给判断依据，POST 后同样 PATCH + GET 验证。

```
感谢分享 <产品名>！不过本仓库只收录中国独立开发者的项目（README 开头写明"聚合所有中国独立开发者的项目"），所以暂时不在收录范围内，抱歉。祝 <产品名> 发展顺利！
```
```
Thanks for sharing <product>! This repo specifically curates projects made by Chinese independent developers, so it's outside the scope of this list. Good luck with <product>!
```

**每一次拒绝都必须出现在最终汇报里。**

---

## 5. 补充拒绝类别

除垃圾广告和老外，以下三类也拒绝：

1. **大厂 / 上市公司产品**：官网归属某公司且该公司是上市公司或有规模团队（如 `seko.sensetime.com` = 商汤）。
2. **分销返佣链接**：落地 URL 带渠道参数（`cg_click_id`、`cgv`、`utm_source=cakegrowth_gzh`、`ref=`、`invite=`、`aff=`）。
3. **刷量 / 互赞平台**：按 Star/Watch/Fork 计价；承诺「不掉赞 / 掉赞返积分」；站内每个仓库的 Star 与 Watch 数字完全相同。

⚠️ 判据要逐条比对，不要用观感扩大化：
- `affiliate` 多数是「not affiliated with X, Inc.」免责声明，不是联盟计划。
- `ref=` 指向本仓库且提交者就是作者 → 只是来源追踪，正常收录。
- 站内有 affiliate 但落地 URL 干净、内容无付费墙 → 正常收录。
- GEO / AI 可见度优化 / 真人测试这类推广服务，不按 Star 计价就不是刷量。
- **超出这三类的「看着有点问题」不算拒绝理由**，默认收录；要拒先问维护者（→ 判例：B3）。

**必做核查**（任何可疑链接）：

```bash
curl -sL --max-time 20 "<url>" -o /dev/null -w "HTTP:%{http_code} FINAL_URL:%{url_effective}\n"
curl -sL --max-time 20 "<url>" | grep -oE '<title>[^<]*</title>|og:url[^>]*' | head -5
```

- 落地域名与提交域名不同 → 看归谁；带渠道参数 → 返佣；title 暴露的公司与提交者无关 → 大厂。
- `curl` 打不开 **不能**据此判站点有问题，必须换 `WebFetch` 复核一次。000/SSL_ERROR、503 限流页、403 Cloudflare 拦截都不等于站点挂了（→ 判例：C）。
- 双通道都失败时查根域；根域可达且明确指向该子域产品，就算核实通过。
- `*.pages.dev` / `*.github.io` / `*.vercel.app` / `*.netlify.app` 只是托管，不是大厂。
- 提交者描述与站点不符时以站点 meta description 为准，尤其数量词、输入模态、是否带音频、计费单位。

**拒绝模板**（只给结论）：

```
@<用户名> 感谢推荐！不过本仓库只收录中国独立开发者自己的项目，<产品名> 是 <公司名> 的产品，暂时不在收录范围内，抱歉。祝 <产品名> 发展顺利！
```

POST → 捕获 ID → PATCH 覆写 → GET 验证正文。拒绝后的动作同第 4 步：检查一只回评论、检查二评论后关闭 issue、检查三评论后关闭 PR（不 merge）。

---

## 6. 通用处理流程（检查一、二通过身份判断后）

### 6.1 提取与格式化

必须有：制作者名字（没写用 GitHub 用户名）、产品名、可访问 URL、一句话描述。拿不到 URL 时从仓库或正文里找，只有纯广告无任何可定位产品才算垃圾。

可选：城市、GitHub、博客、更多介绍链接。

```
#### 制作者名字(城市) - [Github](url)
* :white_check_mark: [产品名](url)：一句话描述 - [更多介绍](url)
```

**格式规范**
- 提交者明确说「不要改我的简介」→ 一字不动照用，跳过下面所有清理规则。
- 提交者已写好 README 格式的条目 → 那是定稿，逐字保留，只改半角全角、句尾句号、缺失空格、`[更多介绍]` 前缺的「 - 」。
- **状态图标原样沿用**：🕗→`:clock8:`，✅→`:white_check_mark:`，❌→`:x:`。不许升级、降级，不许拿官网资料重写简介（→ 判例：E）。
- 日期标题用北京时间：`TZ=Asia/Shanghai date +"%Y 年 %-m 月 %-d 号添加"`。
- 描述末尾不加句号；去掉「高效、简洁、强大、快速、好用、一款、一个」等填充词；「免费」是核心特征时保留。
- 不以「免费的」开头：`免费的间歇计时器` → `间歇计时器（免费）`。
- 「在线」一般删掉，除非是用来区分客户端/离线版。
- 产品名提到最前；描述不要以「产品名是一款…」开头；形态、平台放句尾用「 — 」带出。
- 严禁加粗（不用 `**`）。

### 6.2 分类

| 类别 | 标准 | 文件 |
|---|---|---|
| 主版面 | 打开即用的网站或 App，非游戏 | `README.md` |
| 程序员版面 | 需要命令行/写代码/安装依赖，或开发工作流工具 | `.github/pages/README-Programmer-Edition.md` |
| 游戏版面 | 任何游戏 | `.github/pages/README-Game.md` |
| 拒绝 | 垃圾广告、无 URL、确凿老外、大厂、返佣、刷量 | 不处理 |

桌面 App 看服务对象：面向普通用户/创作者 → 主版面；额度监控、依赖清理、Agent/IDE 管理器、菜单栏开发工具 → 程序员版面（→ 判例：D）。

个人博客不算产品，写成作者信息行里的链接（`#### 名字(城市) - [Github](url), [博客](url)`），不单独占一行。把「博客」链接点开核实，实为导航站/资源站的不收。

### 6.3 插入与提交

- 新条目插在**当天日期区块顶部**；区块不存在则在最新区块之前新建。**绝不写进 README 顶部的「### 子版面」清单**——那里只放本仓库自己的页面（程序员版面、游戏版面、更早的项目），外部产品一律不进。
- 同一作者当天已有作者行 → 追加到他的条目列表末尾，不另起重复 `####`。
- PR 带来的条目一律并入**处理当天**的区块，贡献者写在哪不算数。
- 当天区块内按「最新收录在最上」排序；三个文件分别用 `git log` 核对：

```bash
for f in README.md .github/pages/README-Programmer-Edition.md .github/pages/README-Game.md; do
  echo "== $f"; git log --date=local --format="%h %ci %s" -8 -- "$f"
done
```

**容量**：插入后 `wc -c README.md`。超 490,000 就搬迁，一次剪到 487,500 留余量：

```bash
python3 .github/scripts/migrate_archive.py            # 预演，看到「行级校验通过」
python3 .github/scripts/migrate_archive.py --write
```

只有脚本不可用时才手剪，且必须按日期定位插入、兼容「日/号」两种标题、不重排分册（→ 判例：H）。分册自己接近 500,000 字节时，把较新的一半拆成 `README-Earlier-Projects-2.md`，编号一旦定下就冻结。

**提交**：`git pull` → 改文件 → `git add` → 一次 commit → `git push origin master`。不建分支、不开 PR。PR 来源不走这条。

---

## 7. 致谢评论（仅检查一的提交者）

每位提交者单独一条，一人一评，不合并。正文只写结果，不加「谢谢」等结尾客套，不提冲突/手动处理等过程。

```
@<用户名> 感谢提交，已将你的产品 <产品名> 添加到 <主版面/程序员版面/游戏版面>！
```

每条都 POST → 立即 PATCH 覆写 → GET 验证正文，且版面名必须带「面」字。

---

## 8. 收尾扫描（每次都做，含空跑）

```bash
for p in 1 2 3 4 5; do
  for try in 1 2 3; do
    gh api "repos/1c7/chinese-independent-developer/issues/comments?sort=created&direction=desc&per_page=100&page=$p" \
      > /tmp/sig_scan_$p.json 2>/dev/null && break
    sleep 3
  done
done
jq -s 'add' /tmp/sig_scan_[1-5].json > /tmp/sig_scan_all.json
jq -e 'type == "array" and length > 0' /tmp/sig_scan_all.json >/dev/null \
  || { echo "扫描接口没拿到数据，本次扫描无效，必须重试后再判断"; exit 1; }

jq -r '[.[] | select(.body | test("Generated by")) | select(.user.login as $u | ["1c7","claude[bot]"] | index($u)) | .id] | unique | .[]' \
  /tmp/sig_scan_all.json > /tmp/sig_dirty.txt
echo "已扫评论: $(jq 'length' /tmp/sig_scan_all.json) 条"
echo "检出待修: $(grep -c . /tmp/sig_dirty.txt) 条"
```

扫到就逐条 PATCH 并 GET 复核；空正文保护；只修我们自己发的（贡献者用 `>` 引用的是他的评论，不许动）；修完必须重新扫一遍确认残留为 0（→ 判例：I）。

---

## 9. 运行结束向维护者的汇报

只列结果，不列过程：

- 按版面分组：「**主版面新增**：A、B」「**程序员版面新增**：C」「**游戏版面新增**：D」
- 作者本人更新条目：「**主版面更新**：X（作者本人改的）」
- **未收录**必列：`产品X（原因：老外 / 垃圾广告 / 大厂产品 / 带返佣链接 / 刷量平台 / 重复提交 / 信息无法定位）`；被维护者推翻改为收录的，如实写翻转。
- **必须有一节「需要你处理的意见/建议（N 条）」**：链接 + 谁说的 + 原文摘要 + 建议选项，紧急项置顶；没有就写「无」，不许省。
- 结尾：「共 N 项收录，M 项未收录，全部处理完毕。」空跑写「本次无新收录，本次无未收录项」。
- 除此之外不写过程：跳过的重复项、diff 审查、URL 去重、致谢、签名扫描、容量数字、commit 哈希一律不写。

```
**主版面新增**：Unit Converter for Science、Jev AI

**程序员版面新增**：Agents Anywhere

**未收录**：书径 EbookNest（原因：信息无法定位）

**需要你处理的意见/建议（1 条）**
- [issues/160#issuecomment-123456](链接) @someone：说主版面某条链接 404 —— 建议：核实后改 URL

共 3 项收录，1 项未收录，全部处理完毕。
```

---

## 10. 注意事项

- `gh` 不在 PATH 时先 `export PATH="/opt/homebrew/bin:$PATH"`。
- 幂等性靠 URL 精确 grep，不依赖 reaction 标记。
- 判例库：`references/precedents.md`（A 身份 / B 拒绝 / C 网络核查 / D 版面 / E 格式 / F 去重 / G PR / H 容量 / I 签名 / J 接口 / K 意见）。只在遇到边界判断时查，不要每次全读。
