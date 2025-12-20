## `.github/` 的文档

## 需求（想做到什么？）
我希望将 "用户提交产品"（新增一条 Github Issue 的 Comment）   
到 "存入 .md 文件"，这个流程进行自动化。减少我的时间投入。

## 如何本地运行
```bash
export GITHUB_TOKEN="你的_github_token" 
export LLM_API_KEY="你的_ai_key" 
export GITHUB_REPOSITORY="你的用户名/你的仓库名" 

python .github/scripts/process_item.py
```

