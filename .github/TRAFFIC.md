# 仓库访问统计

Python 标准库脚本，无第三方 Python 依赖或统计服务。

- 每周一北京时间 **09:23** 自动运行（GitHub 调度可能延迟）。
- 手动采集：**Actions → 保存仓库访问统计 → Run workflow → 选择 master → Run workflow**。
- 采集配置变更合入 master 时也运行一次。
- 定时与手动触发需工作流存在于默认分支 master。

## 数据存放

同一仓库的独立分支 [traffic-data](https://github.com/1c7/chinese-independent-developer/tree/traffic-data)。

分支里只有一个 `traffic.json`：

- `daily`：按 UTC 日期合并的历史浏览、独立访客、克隆和独立克隆者。
- `snapshots`：每个采集日期的原始窗口（包括来源和热门页面），同一天重跑会更新。
- `updated_at`：最近采集时间。

来源和热门页面是滚动 14 天的前十名，保存快照，不能跨快照累加。每日数据重叠时覆盖更新，不重复累计；缺失日期不填零。每日 UV 不能相加当作跨日去重人数。日期按 API 返回的 UTC 日期。初次运行只能获取最近 14 天，无法恢复更早数据。

公开仓库的数据分支也公开。数据分支具有独立提交历史，统计提交不会进入 master，但仓库总大小和提交数量会逐渐增加。数据分支只包含统计文件，不包含工作流。

## 权限和失败处理

读取统计复用已有的 `PAT_TOKEN` Secret，不读取或输出 Token 本身。细粒度 Token 需本仓库 Administration: read；传统 Token 需适用的 repo 权限。以后可换成专用的最小权限 Token。提交数据使用 GitHub 自动提供的 `GITHUB_TOKEN`（contents: write）。

接口失败时不提交部分采集结果；运行串行执行，避免并发推送。每周采集约有一周的补跑余量，超过 14 天未成功可能产生永久缺口。失败后可随时手动补跑。

GitHub 可能在公开仓库长期无活动时自动禁用定时工作流；应关注失败/禁用通知，禁用后重新启用。数据分支提交不是保证调度永久启用的机制。

## 测试

```sh
python3 -m unittest discover -s .github/tests -p 'test_collect_traffic.py' -v
```
