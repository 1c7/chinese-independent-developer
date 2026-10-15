# 仓库访问统计存档

这个 `traffic-data` 分支用于长期保存 [1c7/chinese-independent-developer](https://github.com/1c7/chinese-independent-developer) 的 GitHub 访问统计。

GitHub 流量接口只提供最近 14 天的数据。定期采集并保存到这里，就可以逐步积累更长时间的历史，之后分析每天的访问人数、浏览量和克隆量，以及各次采集时的热门来源和页面。

本分支有两个文件：

- [traffic.json](traffic.json)：所有统计数据。
- `README.md`：分支用途和字段说明。

采集脚本和工作流放在 `master` 分支，统计提交只更新本分支。这个仓库是公开的，因此本分支的数据也公开。

## 什么时候更新

- **自动采集**：每周一北京时间 **09:23**（UTC 01:23），GitHub 调度可能延迟。
- **手动采集**：进入 [保存仓库访问统计](https://github.com/1c7/chinese-independent-developer/actions/workflows/collect_traffic.yml)，点击 **Run workflow**，选择 `master` 后运行。
- **配置更新**：采集脚本或工作流变更合入 `master` 时也会运行。

每次获取 GitHub 当时可提供的最近 14 天数据。`daily` 按日期更新已有记录，保留窗口外的旧记录；不会把两次重叠窗口直接相加。同一个 UTC 日期内多次运行，只保留当天最新的 JSON 快照；此前提交仍可在 Git 历史中查看。

初次采集无法找回已过期的数据；超过 14 天没有成功采集，可能留下无法补齐的缺口。缺失日期不会被自动记作零。

## JSON 顶层字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `repository` | 字符串 | 被统计的仓库，格式为 `owner/repo`。 |
| `timezone` | 字符串 | 统计日期采用的时区，当前为 `UTC`。 |
| `updated_at` | 字符串 | 最近一次成功采集的时间，ISO 8601 格式，带时区。它是采集时间，不是最新访问记录的日期。 |
| `daily` | 数组 | 按日期升序排列的长期每日统计，适合绘制历史趋势和计算日均值。 |
| `snapshots` | 对象 | 按**采集日期（UTC）**保存的原始接口快照，键形如 `2026-10-15`。快照覆盖的是接口当时返回的滚动窗口，不是仅该采集日的访问量。 |

例如，`snapshots["2026-10-15"]` 表示 10 月 15 日采集的数据，其中可能包含 9 月 30 日到 10 月 13 日的记录。具体数据范围应查看快照内的 `timestamp`。

## `daily[]`：长期每日统计

| 字段 | 类型 | 含义 |
|---|---|---|
| `date` | 字符串 | 被统计的日期，格式 `YYYY-MM-DD`，按 UTC 划分。 |
| `views` | 整数 | 当天整个仓库的页面浏览次数（PV），同一访客多次浏览会累计。 |
| `views_uniques` | 整数 | 当天整个仓库的独立访客数（日 UV），按 GitHub 的识别口径去重。 |
| `clones` | 整数 | 当天完整克隆仓库的次数，不包括 `git fetch`。 |
| `clones_uniques` | 整数 | 当天独立克隆者数量，按 GitHub 的识别口径去重。 |

示例：

```json
{
  "date": "2026-10-13",
  "views": 658,
  "views_uniques": 309,
  "clones": 148,
  "clones_uniques": 94
}
```

表示 UTC 10 月 13 日，仓库有 658 次浏览、309 位独立访客，以及 148 次完整克隆、94 位独立克隆者。

UTC 的一天对应北京时间当天 **08:00 至次日 08:00**。独立访客与独立克隆者不是经过核验的真人数量，尤其克隆可能来自自动化任务。如果某一接口未返回某个日期，该日期对应的指标可能缺失；缺失与零不同。

## `snapshots[采集日期]`：滚动窗口原始快照

| 字段 | 类型 | 含义 |
|---|---|---|
| `collected_at` | 字符串 | 这份快照的采集时间，ISO 8601 格式，带时区。 |
| `views` | 对象 | 浏览接口原始结果：窗口总浏览量、窗口独立访客数和每日明细。 |
| `clones` | 对象 | 克隆接口原始结果：窗口总克隆量、窗口独立克隆者和每日明细。 |
| `referrers` | 数组 | 该窗口内 GitHub 返回的前十个访问来源。 |
| `paths` | 数组 | 该窗口内 GitHub 返回的前十个热门仓库页面。 |

### `views` 对象

| 字段 | 含义 |
|---|---|
| `count` | 这次接口统计窗口内的总浏览次数。 |
| `uniques` | 这个窗口内去重后的独立访客数；不是每天独立访客的简单相加。 |
| `views[]` | 每日浏览明细数组。 |
| `views[].timestamp` | 该统计日的 UTC 零点，格式如 `2026-10-13T00:00:00Z`。 |
| `views[].count` | 当天浏览次数。 |
| `views[].uniques` | 当天独立访客数。 |

### `clones` 对象

| 字段 | 含义 |
|---|---|
| `count` | 这次接口统计窗口内的总完整克隆次数。 |
| `uniques` | 这个窗口内去重后的独立克隆者数。 |
| `clones[]` | 每日克隆明细数组。 |
| `clones[].timestamp` | 该统计日的 UTC 零点。 |
| `clones[].count` | 当天完整克隆次数。 |
| `clones[].uniques` | 当天独立克隆者数。 |

上述次数和人数都是整数，`timestamp` 是字符串。

### `referrers[]`：访问来源

| 字段 | 类型 | 含义 |
|---|---|---|
| `referrer` | 字符串 | 来源站点或搜索引擎名称，如 `github.com`、`Google`、`link.zhihu.com`。 |
| `count` | 整数 | 该窗口内归属于这个来源的浏览次数。 |
| `uniques` | 整数 | 该窗口内归属于这个来源的独立访客数。 |

这不是完整来源列表，不能把未列出的部分全部当成“直接访问”；同一访客可能出现在多个来源中。

### `paths[]`：热门页面

| 字段 | 类型 | 含义 |
|---|---|---|
| `path` | 字符串 | GitHub 页面路径，在前面加 `https://github.com` 即可打开。 |
| `title` | 字符串 | GitHub 返回的页面标题或路径说明，如 `Overview`。 |
| `count` | 整数 | 该窗口内这个页面的浏览次数。 |
| `uniques` | 整数 | 该窗口内这个页面的独立访客数。 |

这不是仓库所有页面的完整列表，也不代表用户点击 README 外部项目链接的次数。

## 分析时注意

- **分析每日趋势用 `daily`**。浏览次数、克隆次数可对不重复日期求和；日均独立访客可用每日 `views_uniques` 的平均值。
- **不要把每日 UV 相加当作周期独立人数**：同一个人可能连续多天访问。跨日去重人数只能使用对应快照中 GitHub 提供的窗口 `uniques`，不能从每日数据推算任意月份的准确去重人数。
- **不要跨快照累加**：相邻采集的 14 天窗口有重叠，快照总量、来源和热门页面数据直接相加会重复计数。
- 来源和热门页面只有窗口汇总，不能从中还原每天的来源或每个页面的每日访客。
- 数据覆盖整个仓库，不只是首页；看首页的窗口数据应查 `paths` 中仓库根路径的条目（若它进入热门前十名）。
- 访客和克隆按小时更新，来源和热门页面按天更新，接口之间可能存在刷新时差。

实现与来源：[采集脚本](https://github.com/1c7/chinese-independent-developer/blob/master/.github/scripts/collect_traffic.py)、[工作流](https://github.com/1c7/chinese-independent-developer/blob/master/.github/workflows/collect_traffic.yml)、[GitHub 流量接口说明](https://docs.github.com/en/rest/metrics/traffic)、[GitHub 流量统计帮助](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository)。
