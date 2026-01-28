## 介绍 `.github/` 文件夹的用途

## 概括
用户在 https://github.com/1c7/chinese-independent-developer/issues/160 提交评论。   
大部分情况下，格式是不符合规范的（可以理解）  
需要用程序自动化处理，减少我的时间投入。

## 流程
1. 我（1c7）在用户提交的评论点击 🚀 图标（表情）
1. 触发 Github Action 执行（手动触发 或 定时执行（每 6 小时）
1. Github Action 会触发 .github/scripts/process_item.py
2. 查找 "当前日期-3天" 开始（这个时间点往后） 所有标记 🚀 图标 的评论
3. 处理格式，创建 Pull Request。
4. 给评论新增一个  🎉 图标（意思是"处理完成"）
7. 回复这条评论：感谢提交，已添加。

我只需要修改 PR 然后 merge 就行。  

一句话概括：我点击 🚀 标签，然后 PR 会自动创建，我只需要 merge PR。我大概点击 3 次左右就可以了（如果介绍语有改进空间，我还得改一下文字，然后才 merge）

## 本地运行（为了开发调试）
```bash
cp .env.example .env

uv sync

uv run .github/scripts/process_item.py
```
