import os
import re
import datetime
from github import Github # https://github.com/PyGithub/PyGithub
from openai import OpenAI
from datetime import datetime, timedelta, timezone


# ================= 配置区 =================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
REPO_NAME = "1c7/chinese-independent-developer" # os.getenv("GITHUB_REPOSITORY")
ISSUE_NUMBER = 160  # 你在维护的那个 Issue 编号
ADMIN_HANDLE = "1c7" # 替换为你的 GitHub ID
TRIGGER_EMOJI = "rocket" # 🚀
SUCCESS_EMOJI = "hooray" # 🎉
# ==========================================

def remove_quote_blocks(text: str) -> str:
    """移除 GitHub 引用回复块（以 > 开头的行）"""
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # 检查去除前导空格后是否以 > 开头
        if not line.lstrip().startswith('>'):
            cleaned_lines.append(line)

    # 重新拼接，并清理多余空行
    result = '\n'.join(cleaned_lines)

    # 移除连续多个空行，保留单个空行
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()

def get_ai_format(raw_text):
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    prompt = f"""
你是一个严格的文案编辑。任务是将用户的项目介绍转换为标准的 Markdown 格式。

4. 格式模板：
#### 制作者名字 - [Github](链接)
* :white_check_mark: [项目名](链接)：用途描述

待处理文本：
{raw_text}
"""
    response = client.chat.completions.create(
        model="deepseek-reasoner", # 或者使用 deepseek-chat
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def main():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    issue = repo.get_issue(ISSUE_NUMBER)
    
    # 计算 3 天前的时间（GitHub API 使用的是 UTC 时间）
    time_threshold = datetime.now(timezone.utc) - timedelta(days=3)
    
    # 如果你一定要死守 2025-12-15，也可以手动指定：
    # time_threshold = datetime(2025, 12, 15, tzinfo=timezone.utc)
    
    # 重点：在这里加上 since 参数
    comments = issue.get_comments(since=time_threshold)

    processed_count = 0

    for comment in comments:
        # 1. 检查是否有你的 🚀 反应
        reactions = comment.get_reactions()
        has_trigger = any(r.content == TRIGGER_EMOJI and r.user.login == ADMIN_HANDLE for r in reactions)
        # 2. 检查是否已经标记过成功 🎉
        has_success = any(r.content == SUCCESS_EMOJI for r in reactions)

        if has_trigger and not has_success:
            print(f"发现待处理评论 ID: {comment.id}")

            # 清理引用块，然后 AI 格式化内容
            cleaned_body = remove_quote_blocks(comment.body)
            formatted_entry = get_ai_format(cleaned_body)
            
            # 准备修改 README.md
            content = repo.get_contents("README.md", ref="master")
            readme_text = content.decoded_content.decode("utf-8")

            # 插入日期逻辑
            today_str = datetime.now().strftime("%Y 年 %m 月 %d 号添加")
            date_header = f"### {today_str}"
            
            if date_header not in readme_text:
                # 在 "3. 项目列表" 下方插入新日期
                new_readme = readme_text.replace("3. 项目列表\n", f"3. 项目列表\n\n{date_header}\n")
            else:
                new_readme = readme_text

            # 在日期标题下插入新条目
            insertion_point = new_readme.find(date_header) + len(date_header)
            final_readme = new_readme[:insertion_point] + "\n\n" + formatted_entry + new_readme[insertion_point:]

            # 创建新分支并提交 PR
            branch_name = f"add-project-{comment.id}"
            base = repo.get_branch("master")

            # 检查分支是否已存在，如果存在则删除
            try:
                existing_ref = repo.get_git_ref(f"heads/{branch_name}")
                existing_ref.delete()
                print(f"已删除现有分支: {branch_name}")
            except:
                pass  # 分支不存在，继续

            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)
            
            repo.update_file(
                "README.md",
                f"docs: add new project from comment {comment.id}",
                final_readme,
                content.sha,
                branch=branch_name
            )

            pr = repo.create_pull(
                title=f"新增项目：来自评论 {comment.id}",
                body=f"{comment.body}\n\n---\n原始评论：`{comment.html_url}`",
                head=branch_name,
                base="master"
            )

            # 用表情标记为成功，并回复
            comment.create_reaction(SUCCESS_EMOJI)
            # comment.create_comment(f"感谢提交，已添加！\n\nPR 链接：{pr.html_url}")
            
            processed_count += 1
            print(f"评论 {comment.id} 处理成功，已创建 PR。")

    if processed_count == 0:
        print("没有发现需要处理的新评论。")

if __name__ == "__main__":
    main()