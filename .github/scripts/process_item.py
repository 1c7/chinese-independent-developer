import os
import re
import datetime
from github import Github 
from openai import OpenAI
from datetime import datetime, timedelta, timezone

# ================= 配置区 =================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
REPO_NAME = "1c7/chinese-independent-developer" 
ISSUE_NUMBER = 160
ADMIN_HANDLE = "1c7" 
TRIGGER_EMOJI = "rocket" # 🚀
SUCCESS_EMOJI = "hooray" # 🎉
# ==========================================

def remove_quote_blocks(text: str) -> str:
    """移除 GitHub 引用回复块"""
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if not line.lstrip().startswith('>'):
            cleaned_lines.append(line)
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def get_ai_project_line(raw_text):
    """只让 AI 提取项目名称、链接和描述行"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    prompt = f"""
任务：将用户的项目介绍转换为单行 Markdown 格式。
要求：
1. 严格禁止使用“一款、一个、完全免费、高效、简洁、强大、快速、好用”等营销废话。
2. 描述必须以“用途”或“功能”作为动词开头。   
3. 严禁使用加粗格式（不要使用 **）。
4. 仅输出以下格式的一行文字：
* :white_check_mark: [项目名](网址)：用途描述

待处理文本：
{raw_text}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def main():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    issue = repo.get_issue(ISSUE_NUMBER)
    
    time_threshold = datetime.now(timezone.utc) - timedelta(days=3)
    comments = issue.get_comments(since=time_threshold)

    processed_count = 0

    for comment in comments:
        reactions = comment.get_reactions()
        has_trigger = any(r.content == TRIGGER_EMOJI and r.user.login == ADMIN_HANDLE for r in reactions)
        has_success = any(r.content == SUCCESS_EMOJI for r in reactions)

        if has_trigger and not has_success:
            print(f"\n{'='*60}")
            print(f"处理评论：\n{comment.body}")
            print(f"\n评论链接：{comment.html_url}")
            print(f"{'='*60}\n")

            cleaned_body = remove_quote_blocks(comment.body)

            # --- 新逻辑：判断用户是否自带了 Header ---
            # 匹配以 #### 开头的行
            header_match = re.search(r'^####\s+.*', cleaned_body, re.MULTILINE)
            
            if header_match:
                # 1. 提取用户自己写的 Header
                header_line = header_match.group(0).strip()
                # 2. 从正文中移除这一行，避免干扰 AI
                body_for_ai = cleaned_body.replace(header_line, "").strip()
                print(f"检测到用户自带 Header: {header_line}")
            else:
                # 1. 自动生成 Header
                author_name = comment.user.login
                author_url = comment.user.html_url
                header_line = f"#### {author_name} - [Github]({author_url})"
                body_for_ai = cleaned_body
                print(f"自动生成 Header: {header_line}")

            # 3. AI 仅处理项目详情行
            project_line = get_ai_project_line(body_for_ai)
            
            # 组合成最终条目
            formatted_entry = f"{header_line}\n{project_line}"
            
            # 4. 更新 README.md 逻辑
            content = repo.get_contents("README.md", ref="master")
            readme_text = content.decoded_content.decode("utf-8")

            today_str = datetime.now().strftime("%Y 年 %m 月 %d 号添加")
            date_header = f"### {today_str}"
            
            if date_header not in readme_text:
                new_readme = readme_text.replace("3. 项目列表\n", f"3. 项目列表\n\n{date_header}\n")
            else:
                new_readme = readme_text

            insertion_point = new_readme.find(date_header) + len(date_header)
            final_readme = new_readme[:insertion_point] + "\n\n" + formatted_entry + new_readme[insertion_point:]

            # 5. 提交 PR 逻辑
            branch_name = f"add-project-{comment.id}"
            base = repo.get_branch("master")

            try:
                repo.get_git_ref(f"heads/{branch_name}").delete()
            except:
                pass

            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)
            repo.update_file(
                "README.md",
                f"docs: add project from {comment.user.login}",
                final_readme,
                content.sha,
                branch=branch_name
            )

            # 为了彻底消除 Issue 里的 "mentioned this" 红框，
            # 在 https:// 后面插入一个不可见字符 \u200b
            safe_url = comment.html_url.replace("https://", "https://\u200b")

            pr = repo.create_pull(
                title=f"新增项目：来自 {comment.user.login} 的评论",
                body=f"原评论内容：{comment.body} \n\n 原始评论：{safe_url} \n\n 此 PR 是自动生成，目的是节省时间。\n （触发方法：Github 用户 1c7 在评论下方点击了'火箭'图标，然后用 Github Action 遍历评论），",
                head=branch_name,
                base="master"
            )

            comment.create_reaction(SUCCESS_EMOJI)
            comment.create_comment(f"感谢提交，已添加！\n\nPR 链接：{pr.html_url}")
            processed_count += 1

    if processed_count == 0:
        print("未发现新标记的任务。")

if __name__ == "__main__":
    main()