import os
import re
import datetime
from github import Github 
from openai import OpenAI
from datetime import datetime, timedelta, timezone

# ================= 配置区 =================
PAT_TOKEN = os.getenv("PAT_TOKEN")  # GitHub Personal Access Token
API_KEY = os.getenv("LLM_API_KEY")  # LLM API 密钥（如 DeepSeek、OpenAI）
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")  # LLM API 基础 URL
REPO_NAME = "1c7/chinese-independent-developer"  # GitHub 仓库名称
ISSUE_NUMBER = 160  # 用于收集项目提交的 Issue 编号
ADMIN_HANDLE = "1c7"  # 管理员 GitHub 用户名
TRIGGER_EMOJI = "rocket"  # 触发处理的表情符号 🚀
SUCCESS_EMOJI = "hooray"  # 处理成功的表情符号 🎉
# ==========================================

def check_environment():
    """检查必需的环境变量是否存在"""
    if not PAT_TOKEN:
        raise ValueError("❌ 缺少环境变量 PAT_TOKEN！请设置 GitHub Personal Access Token。")
    if not API_KEY:
        raise ValueError("❌ 缺少环境变量 LLM_API_KEY！请设置 LLM API Key。")

    print(f"✅ 环境变量检查通过")
    print(f"   - PAT_TOKEN: {'*' * 10}{PAT_TOKEN[-4:]}")
    print(f"   - API_KEY: {'*' * 10}{API_KEY[-4:]}")
    print(f"   - BASE_URL: {BASE_URL}\n")

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
    """让 AI 提取项目名称、链接和描述（支持多个产品）"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    prompt = f"""
任务：将用户的项目介绍转换为 Markdown 格式。

要求：
1. 识别文本中的所有产品/项目（可能有多个）
2. 每个项目占一行
3. 在文字的开头，去掉"一款、一个、完全免费、高效、简洁、强大、快速、好用、安全"等营销废话
4. 严禁使用加粗格式（不要使用 **）
5. 将产品名称从文字的后面提升到最前面
6. 每行格式：* :white_check_mark: [项目名](网址)：用途描述

示例 1：
输入：https://example.com：一款基于 AI 的高效视频生成网站
输出：* :white_check_mark: [example.com](https://example.com)：AI 视频生成网站

示例 2：
输入：[MyApp](https://myapp.com) 完全免费的强大工具，帮助用户管理任务
输出：* :white_check_mark: [MyApp](https://myapp.com)：任务管理工具

示例 3（多个项目）：
输入：
[ProductA](https://a.com)：AI 绘画工具
[ProductB](https://b.com)：AI 写作助手
输出：
* :white_check_mark: [ProductA](https://a.com)：AI 绘画工具
* :white_check_mark: [ProductB](https://b.com)：AI 写作助手

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
    # 检查环境变量
    check_environment()

    g = Github(PAT_TOKEN)
    repo = g.get_repo(REPO_NAME)
    issue = repo.get_issue(ISSUE_NUMBER)

    time_threshold = datetime.now(timezone.utc) - timedelta(days=3)
    comments = issue.get_comments(since=time_threshold)

    # ===== 阶段 1：收集待处理评论 =====
    pending_comments = []
    formatted_entries = []

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

            # 判断用户是否自带了 Header
            header_match = re.search(r'^####\s+.*', cleaned_body, re.MULTILINE)

            if header_match:
                header_line = header_match.group(0).strip()
                body_for_ai = cleaned_body.replace(header_line, "").strip()
                print(f"检测到用户自带 Header: {header_line}")
            else:
                author_name = comment.user.login
                author_url = comment.user.html_url
                header_line = f"#### {author_name} - [Github]({author_url})"
                body_for_ai = cleaned_body
                print(f"自动生成 Header: {header_line}")

            # AI 处理项目详情行
            project_line = get_ai_project_line(body_for_ai)
            formatted_entry = f"{header_line}\n{project_line}"

            pending_comments.append(comment)
            formatted_entries.append(formatted_entry)

    # ===== 阶段 2：批量提交 =====
    if not pending_comments:
        print("无待处理评论")
        return

    print(f"\n共收集 {len(pending_comments)} 个待处理评论")

    # 更新 README
    content = repo.get_contents("README.md", ref="master")
    readme_text = content.decoded_content.decode("utf-8")

    today_str = datetime.now().strftime("%Y 年 %-m 月 %-d 号添加")
    date_header = f"### {today_str}"

    if date_header not in readme_text:
        new_readme = readme_text.replace("3. 项目列表\n", f"3. 项目列表\n\n{date_header}\n")
    else:
        new_readme = readme_text

    # 插入所有条目（用两个换行分隔）
    insertion_point = new_readme.find(date_header) + len(date_header)
    all_entries = "\n\n".join(formatted_entries)
    final_readme = new_readme[:insertion_point] + "\n\n" + all_entries + new_readme[insertion_point:]

    # 创建分支
    branch_name = f"batch-add-projects-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    base = repo.get_branch("master")

    try:
        repo.get_git_ref(f"heads/{branch_name}").delete()
    except:
        pass

    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)
    repo.update_file(
        "README.md",
        f"docs: batch add {len(pending_comments)} projects",
        final_readme,
        content.sha,
        branch=branch_name
    )

    # 构建 PR body
    comment_links = "\n".join([
        f"- [{c.user.login}]({c.html_url})"
        for c in pending_comments
    ])

    formatted_list = "\n\n".join([
        f"### {i+1}. {formatted_entries[i]}"
        for i in range(len(formatted_entries))
    ])

    pr_body = f"""批量添加 {len(pending_comments)} 个项目

## 原始评论链接
{comment_links}

## 格式化结果
{formatted_list}

---
自动生成，触发机制：用户 {ADMIN_HANDLE} 点击 🚀
"""

    pr = repo.create_pull(
        title=f"新增项目：批量添加 {len(pending_comments)} 个项目",
        body=pr_body,
        head=branch_name,
        base="master"
    )

    print(f"\n✅ PR 创建成功：{pr.html_url}")

    # 标记所有评论（添加 🎉 表情）
    for comment in pending_comments:
        comment.create_reaction(SUCCESS_EMOJI)

    # 创建一条评论提及所有用户
    user_mentions = " ".join([f"@{c.user.login}" for c in pending_comments])
    reply_body = f"{user_mentions} 感谢提交，已添加！\n\n PR 链接：{pr.html_url}"
    issue.create_comment(reply_body)

    print(f"\n✅ 已标记所有 {len(pending_comments)} 个评论")

if __name__ == "__main__":
    main()