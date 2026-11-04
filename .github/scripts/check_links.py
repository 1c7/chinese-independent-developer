"""校验提交条目里的链接是否可访问。

维护者规则（唯一硬性的一条）：链接必须能打开。打不开的条目不收录，
并把失败原因写回 Issue，方便提交者补链后重投。

设计要点：
- App Store 链接走 iTunes lookup 接口判断，比抓 HTML 页面稳，还能顺带查出
  「这个 App 只在哪些区上架」，回复时可以直接告诉提交者。
- 普通链接先 HEAD，服务端拒绝 HEAD（403/405/501）时退回 GET。
- 403 / 429 视为「对方拒绝爬虫」，不算死链，避免误伤。
- 同一个 URL 在同一次运行里只查一次。
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
TIMEOUT = 12
# App Store 链接：https://apps.apple.com/{国家}/app/{可选名字}/id{数字}
APP_STORE_RE = re.compile(
    r"https?://apps\.apple\.com/([a-z]{2})/app/(?:[^/\s)]*/)?id(\d+)", re.IGNORECASE
)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
LOOKUP_API = "https://itunes.apple.com/lookup?id={app_id}&country={country}"
# 国内区查不到时，用来判断 App 是否只是「没上中国区」
PROBE_COUNTRIES = ("cn", "us", "hk", "tw")

LinkProblem = namedtuple("LinkProblem", "url label reason")


def _clean(url):
    """去掉链接尾部的标点，避免把句号、括号算进 URL。"""
    return url.strip().rstrip(".,;:!?、。，；）)】》\"'")


def _fetch(url, method="GET"):
    """发一个请求，返回 HTTP 状态码。网络异常返回 None。"""
    request = urllib.request.Request(
        url, method=method, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception:
        return None


def app_store_target(url):
    """如果是 App Store 链接，返回 (国家, 数字 id)，否则 None。"""
    match = APP_STORE_RE.search(_clean(url))
    if not match:
        return None
    return match.group(1).lower(), match.group(2)


def lookup_app_store(app_id, country):
    """查 iTunes 接口。查得到返回 App 信息，查不到返回 None。

    接口被限流或网络异常时抛 RuntimeError，让调用方按「暂时查不了」处理，
    而不是误判成死链。
    """
    query = LOOKUP_API.format(app_id=app_id, country=country)
    try:
        with urllib.request.urlopen(
            urllib.request.Request(query, headers={"User-Agent": USER_AGENT}),
            timeout=TIMEOUT,
        ) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception as error:  # noqa: BLE001 - 统一转成「查不了」
        raise RuntimeError(f"iTunes 接口查询失败：{error}") from error
    results = payload.get("results") or []
    return results[0] if results else None


def _check_app_store(url, country, app_id):
    """App Store 链接的判定。返回 None 表示没问题，否则返回原因字符串。"""
    try:
        if lookup_app_store(app_id, country):
            return None
        available = [
            code
            for code in PROBE_COUNTRIES
            if code != country and lookup_app_store(app_id, code)
        ]
    except RuntimeError:
        return None  # 查不了就不判死链，交给人工看

    if available:
        regions = " / ".join(code.upper() for code in available)
        return f"{country.upper()} 区查不到这个 App（{regions} 区在售）"
    return f"App Store 查不到这个 App（id {app_id}）"


def _check_http(url):
    """普通链接的判定。返回 None 表示没问题，否则返回原因字符串。"""
    status = _fetch(url, "HEAD")
    if status is None or status in (403, 405, 429, 501):
        status = _fetch(url, "GET") or status

    if status is None:
        return "无法连接"
    if status in (403, 429):
        return None  # 对方拦爬虫，不当死链
    if 200 <= status < 400:
        return None
    if status == 404:
        return "HTTP 404（页面不存在）"
    if status >= 500:
        return f"HTTP {status}（站点异常）"
    return f"HTTP {status}"


def check_url(url, _cache=None):
    """检查单个链接。返回 None 表示可访问，否则返回原因字符串。"""
    target = _clean(url)
    if not target:
        return "空链接"

    if _cache is not None and target in _cache:
        return _cache[target]

    store = app_store_target(target)
    if store:
        country, app_id = store
        reason = _check_app_store(target, country, app_id)
    else:
        reason = _check_http(target)

    if _cache is not None:
        _cache[target] = reason
    return reason


def extract_links(text):
    """抽出 Markdown 链接，返回 [(显示名, URL)]。"""
    return [(label.strip(), _clean(url)) for label, url in MD_LINK_RE.findall(text)]


def check_line_links(line, _cache=None):
    """检查一行里的所有链接，返回问题列表。"""
    problems = []
    for label, url in extract_links(line):
        reason = check_url(url, _cache)
        if reason:
            problems.append(LinkProblem(url=url, label=label, reason=reason))
    return problems


def filter_entry(entry_text, _cache=None):
    """过滤条目：只摘掉链接打不开的产品行，Header 行保留。

    返回 (过滤后的条目, 被摘掉的问题列表)。
    """
    kept_lines, problems = [], []
    for line in entry_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("*") and ":white_check_mark:" in stripped:
            line_problems = check_line_links(line, _cache)
            if line_problems:
                problems.extend(line_problems)
                continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip(), problems


def format_problems(problems):
    """把问题列表拼成适合贴进 Issue 回复的 Markdown。"""
    if not problems:
        return ""
    lines = ["以下链接打不开，暂未收录，补好链接后回复一句我再加上："]
    for problem in problems:
        lines.append(f"- [{problem.label}]({problem.url})：{problem.reason}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    for argument in sys.argv[1:] or ["https://apps.apple.com/cn/app/id6813423397"]:
        print(f"{argument}\t{check_url(argument) or 'OK'}")
