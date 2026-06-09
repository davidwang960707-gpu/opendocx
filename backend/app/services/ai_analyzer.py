"""P1-UI-6 高级 AI 卡 — 文档静态分析器

不做 LLM 调用，**纯规则** 从 markdown 文本提取：
  1. **术语**：高频技术词 + 中英混用检测 + 同一概念多种叫法
  2. **接口**：识别 API 端点 (HTTP method + path) / 错误码 / 参数
  3. **健康度**：代码块比例 / 标题层次完整性 / 段落长度 / 链接密度
  4. **摘要**：取首段有意义句子
  5. **知识关联**：从项目内其他文档标题中匹配（输入 docs 列表）

返回结构化 JSON，前端 EditorAIPanel 直接渲染。

零外部依赖 (除了 app.models 里的 Document)。
"""
from __future__ import annotations
import re
from collections import Counter
from typing import Optional


# ── 术语分析 ──────────────────────────────────────────────

# 技术术语模式（中英文混合）
_TERM_PATTERNS = [
    # 英文术语 (大写开头/驼峰/全大写)
    (re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b"), "code"),         # CamelCase
    (re.compile(r"\b[A-Z]{2,5}\b"), "acronym"),                       # API/RAG/SDK/UI
    (re.compile(r"\b[a-z]+(?:[._-][a-z]+)+\b"), "tech"),             # react.js / doc-ai
    # 中文术语 (4 字以上常见技术名词)
    (re.compile(r"[\u4e00-\u9fa5]{4,}"), "zh"),
]

# 常见同义词/异写（命中"X 与 Y 混用"提示）
_TERM_SYNONYMS = {
    ("rag", "检索增强"): "RAG / 检索增强",
    ("llm", "大语言模型"): "LLM / 大语言模型",
    ("agent", "智能体"): "Agent / 智能体",
    ("embedding", "向量"): "Embedding / 向量",
    ("vector", "向量"): "Vector / 向量",
    ("workflow", "工作流"): "Workflow / 工作流",
    ("pipeline", "管道"): "Pipeline / 管道",
}


def extract_terms(content: str, top_n: int = 12) -> list[dict]:
    """从文本中提取高频术语

    英文：CamelCase / ACRONYM / tech.something 等高信号模式
    中文：滑动窗口 (2/3/4 字) 高频组合
    """
    if not content:
        return []

    counter: Counter = Counter()
    # 英文/数字术语
    for pat, _kind in _TERM_PATTERNS[:3]:  # 跳过中文 4+ 模式（噪声大）
        for m in pat.findall(content):
            term = m.strip("`*_# ")
            if len(term) < 2 or term in ("HTTP", "HTTPS"):
                continue
            counter[term] += 1

    # 中文术语：滑动 2/3/4 字窗口 + 频率
    zh_segments = re.findall(r"[\u4e00-\u9fa5]+", content)
    for seg in zh_segments:
        for n in (2, 3, 4):
            for i in range(len(seg) - n + 1):
                counter[seg[i:i+n]] += 1

    # 简单去重：子串合并（高频大词覆盖低频子词）
    sorted_terms = counter.most_common()
    terms: list[dict] = []
    seen_substr: set[str] = set()
    for term, count in sorted_terms:
        # 短词 + 频率太低的直接 skip
        if count < 2:
            continue
        if len(term) < 2:
            continue
        # 跳过纯数字 / 纯标点
        if not re.search(r"[\u4e00-\u9fa5a-zA-Z]", term):
            continue
        # 子串合并：仅当父串频率 >= 当前词时，才认为当前词是子串
        is_sub = any(
            term != t and term in t and counter[t] >= count
            for t in counter
        )
        if is_sub:
            continue
        if term in seen_substr:
            continue
        seen_substr.add(term)
        terms.append({"term": term, "count": count})
        if len(terms) >= top_n:
            break
    return terms


def detect_terminology_issues(content: str) -> list[str]:
    """检测术语混用 / 拼写不一致

    判定规则：同义词 a/b 都出现，且至少有一个 a 的出现位置与最近的 b 距离 > 30 字符
    （避免「RAG (检索增强)」这种括号解释被误判）。
    """
    issues: list[str] = []
    for (a, b), label in _TERM_SYNONYMS.items():
        a_positions = [m.start() for m in re.finditer(a, content, re.IGNORECASE)]
        b_positions = [m.start() for m in re.finditer(re.escape(b), content)]
        if not a_positions or not b_positions:
            continue
        # 检查是否有 a 和 b 相距 > 30 字符（独立使用）
        far_apart = False
        for ap in a_positions:
            for bp in b_positions:
                if abs(ap - bp) > 30:
                    far_apart = True
                    break
            if far_apart:
                break
        if far_apart:
            issues.append(f"「{label}」混用 ({len(a_positions)} 处 / {len(b_positions)} 处)")

    # API 大小写一致性
    api_upper = len(re.findall(r"\bAPI\b", content))
    api_lower = len(re.findall(r"\bapi\b", content))
    if api_upper >= 1 and api_lower >= 1:
        # 任何大写 + 小写混用都提示（与距离无关）
        issues.append(f"API 大小写混用 ({api_upper} 大写 / {api_lower} 小写)")
    return issues


# ── 接口分析 ──────────────────────────────────────────────

_HTTP_METHOD = r"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)"
_API_PATH = r"(/[A-Za-z0-9_\-{}:/.]+)"

# 三种写法:
#   1. `GET /api/v1/...`
#   2. **GET** /api/v1/...
#   3. GET /api/v1/... （在反引号/代码块/行内）
_API_PATTERN = re.compile(
    rf"(?<![\w/])`?\s*\*?\*?{_HTTP_METHOD}\*?\*?\s+{_API_PATH}`?",
    re.MULTILINE,
)

# 错误码 (3 位数字，常跟 status/code/状态)
_ERROR_CODE_PATTERN = re.compile(
    r"\b(?:错误码|status\s*code|HTTP\s*status|状态码)[^\d]{0,10}(\d{3})\b", re.IGNORECASE
)

# 标准错误码
_STANDARD_ERROR_CODES = {400, 401, 403, 404, 409, 422, 429, 500, 502, 503, 504}


def extract_endpoints(content: str) -> list[dict]:
    """提取 API 端点（保留围栏代码块，剥行内反引号）

    围栏代码块里的端点最常见（curl 示例、API 签名），必须保留。
    行内反引号里的 `http://example.com/path` 这类 URL 示例要去掉。
    """
    # 1. 先标记所有"示例 URL"（前后有 http:// 或 https://）的整行，去掉
    cleaned_lines = []
    for line in content.split("\n"):
        if re.search(r"https?://", line) and not re.search(rf"(?<![\w/])(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/", line):
            # 这行含 URL，但不含"HTTP method + /path"端点签名 → 跳过
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)

    # 2. 去掉行内反引号内容（避免误抓 URL 示例）
    # 用 (?<!\`)\` 排除"被 3 个反引号包围"的围栏边界
    cleaned = re.sub(r"(?<!`)`[^`\n]+`(?!`)", "", cleaned)

    endpoints = []
    seen: set[tuple[str, str]] = set()
    for m in _API_PATTERN.finditer(cleaned):
        method = m.group(1).upper()
        path = m.group(2)
        key = (method, path)
        if key in seen:
            continue
        seen.add(key)
        endpoints.append({"method": method, "path": path})
    return endpoints


def extract_error_codes(content: str) -> list[int]:
    """提取错误码（去重 + 排序）"""
    codes = set()
    for m in _ERROR_CODE_PATTERN.finditer(content):
        try:
            codes.add(int(m.group(1)))
        except ValueError:
            pass
    return sorted(codes)


def detect_interface_issues(content: str, endpoints: list[dict], error_codes: list[int]) -> list[str]:
    """检测接口一致性问题"""
    issues: list[str] = []
    # 1. 端点存在但没提错误码
    if endpoints and not error_codes:
        issues.append(f"有 {len(endpoints)} 个端点但未提及错误码")
    # 2. 标准错误码缺失
    if endpoints:
        documented = set(error_codes)
        missing = _STANDARD_ERROR_CODES - documented
        # 只对 401/403/429/500 这些关键码提示
        critical = {401, 403, 429, 500} - documented
        if critical:
            issues.append(f"建议补充错误码: {sorted(critical)}")
    # 3. 端点路径不一致（前缀）
    prefixes = {e["path"].split("/")[1] for e in endpoints if "/" in e["path"] and len(e["path"]) > 1}
    if len(prefixes) > 1:
        issues.append(f"端点前缀不统一: {sorted(prefixes)}")
    return issues


# ── 健康度评分 ─────────────────────────────────────────────

def compute_health(content: str) -> dict:
    """计算健康度（0-100）"""
    if not content or len(content) < 50:
        return {"score": 0, "grade": "待评估", "breakdown": {}}

    lines = content.split("\n")
    total_lines = len(lines)
    char_count = len(content)

    # 1. 标题层次完整性（30 分）
    h1 = sum(1 for l in lines if re.match(r"^# [^#]", l))
    h2 = sum(1 for l in lines if re.match(r"^## ", l))
    h3 = sum(1 for l in lines if re.match(r"^### ", l))
    if h1 == 0:
        heading_score = 5  # 没有 H1 大扣分
    elif h1 > 1:
        heading_score = 12  # 多 H1 也不推荐
    else:
        heading_score = 22  # 完美：有 1 个 H1
    if h2 >= 2:
        heading_score += 8
    elif h2 == 1:
        heading_score += 4
    # H3 适量加分
    if h3 > 0 and h3 < h2 * 4:
        heading_score += 0  # 已经在 22+8
    heading_score = min(30, heading_score)

    # 2. 代码块比例（20 分）
    in_code = False
    code_lines = 0
    code_langs: set[str] = set()
    for l in lines:
        if l.strip().startswith("```"):
            in_code = not in_code
            if in_code:
                lang = l.strip()[3:].strip()
                if lang:
                    code_langs.add(lang)
            continue
        if in_code:
            code_lines += 1
    code_ratio = code_lines / max(total_lines, 1)
    # 理想 15-40%
    if 0.15 <= code_ratio <= 0.40:
        code_score = 20
    elif 0.05 <= code_ratio < 0.15 or 0.40 < code_ratio <= 0.55:
        code_score = 14
    elif code_ratio == 0 and h2 >= 1:
        code_score = 6  # 有 H2 章节但无代码，可能是设计/纯文字
    elif code_ratio > 0.55:
        code_score = 10
    else:
        code_score = 8

    # 3. 段落长度（25 分）— 太长阅读累
    paragraphs = [p for p in re.split(r"\n\n+", content) if p.strip() and not p.strip().startswith("#")]
    if not paragraphs:
        para_score = 10
    else:
        para_lengths = [len(p) for p in paragraphs]
        avg = sum(para_lengths) / len(para_lengths)
        # 理想 80-300 字符
        if 80 <= avg <= 250:
            para_score = 25
        elif 50 <= avg < 80 or 250 < avg <= 400:
            para_score = 18
        elif avg < 50:
            para_score = 12
        else:
            para_score = 10

    # 4. 链接密度（25 分）— 内部链接反映知识图谱意识
    links = len(re.findall(r"\[.+?\]\(.+?\)", content))
    link_density = links / max(char_count / 1000, 1)  # 每千字链接数
    if link_density >= 3:
        link_score = 25
    elif link_density >= 1.5:
        link_score = 18
    elif link_density >= 0.5:
        link_score = 12
    elif links > 0:
        link_score = 8
    else:
        link_score = 5

    total = heading_score + code_score + para_score + link_score
    total = min(100, total)

    if total >= 85:
        grade = "优秀"
    elif total >= 70:
        grade = "良好"
    elif total >= 50:
        grade = "待改进"
    else:
        grade = "需重写"

    return {
        "score": total,
        "grade": grade,
        "breakdown": {
            "heading": heading_score,
            "code": code_score,
            "paragraph": para_score,
            "link": link_score,
        },
        "stats": {
            "lines": total_lines,
            "chars": char_count,
            "h1": h1, "h2": h2, "h3": h3,
            "code_ratio": round(code_ratio, 2),
            "code_langs": sorted(code_langs),
            "paragraphs": len(paragraphs),
            "avg_paragraph_length": round(sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)),
            "links": links,
        },
    }


# ── 摘要 ─────────────────────────────────────────────

def extract_summary(content: str, max_len: int = 140) -> str:
    """提取文档摘要（启发式）：
    1. 跳过标题（以 # 开头）、引用（> 开头）、列表（-/*/+ 开头）、代码块（```）
    2. 优先取中等长度段落（>= 20 字符）
    3. fallback 到第一段
    """
    if not content.strip():
        return ""
    # 先剥离代码块
    cleaned = re.sub(r"```[\s\S]*?```", "", content)
    paragraphs = [p.strip() for p in re.split(r"\n\n+", cleaned) if p.strip()]
    candidates: list[str] = []
    for p in paragraphs:
        first_line = p.split("\n", 1)[0].lstrip()
        # 跳过标题
        if first_line.startswith("#"):
            continue
        # 跳过列表/引用/纯代码行
        if first_line.startswith((">", "-", "*", "+", "```")):
            continue
        # 跳过纯分隔线
        if re.match(r"^[-*_]{3,}$", first_line):
            continue
        candidates.append(p)
    # 优先 >= 20 字符的说明性段落
    for p in candidates:
        if len(p) >= 20:
            return p[:max_len] + ("…" if len(p) > max_len else "")
    # fallback：取第一个候选
    if candidates:
        p = candidates[0]
        return p[:max_len] + ("…" if len(p) > max_len else "")
    # 终极 fallback：第一段（标题）
    if paragraphs:
        p = paragraphs[0]
        return p[:max_len] + ("…" if len(p) > max_len else "")
    return ""


# ── 知识关联 ─────────────────────────────────────────────

def find_related_docs(
    content: str,
    current_doc_id: Optional[str],
    other_doc_titles: list[dict],
) -> list[dict]:
    """从其他文档标题中匹配当前文档提到的概念

    other_doc_titles: [{"id": ..., "title": ...}, ...]
    返回: [{"id": ..., "title": ..., "match_count": ..., "matched_terms": [...]}, ...]
    """
    if not content or not other_doc_titles:
        return []
    # 当前文档的高频词
    terms_in_content = set()
    for pat, _ in _TERM_PATTERNS:
        for m in pat.findall(content):
            t = m.strip("`*_# ")
            if 2 <= len(t) <= 30:
                terms_in_content.add(t.lower())
    # 中文分词近似：滑动窗口 2-4 字
    zh_text = re.findall(r"[\u4e00-\u9fa5]+", content)
    for seg in zh_text:
        for n in (2, 3, 4):
            for i in range(len(seg) - n + 1):
                terms_in_content.add(seg[i:i+n].lower())

    related = []
    for doc in other_doc_titles:
        if doc["id"] == current_doc_id:
            continue
        title = doc["title"]
        title_lower = title.lower()
        matched = []
        for term in terms_in_content:
            if term in title_lower and len(term) >= 2:
                matched.append(term)
        if matched:
            related.append({
                "id": doc["id"],
                "title": title,
                "match_count": len(matched),
                "matched_terms": matched[:3],
            })
    related.sort(key=lambda x: x["match_count"], reverse=True)
    return related[:5]


# ── 主分析函数 ─────────────────────────────────────────────

def analyze_document(
    content: str,
    other_doc_titles: Optional[list[dict]] = None,
    current_doc_id: Optional[str] = None,
) -> dict:
    """分析单个文档，返回前端 4 张卡需要的全部数据

    其他接口：
      analyze_document_batch([...])   批量分析
    """
    terms = extract_terms(content)
    term_issues = detect_terminology_issues(content)
    endpoints = extract_endpoints(content)
    error_codes = extract_error_codes(content)
    iface_issues = detect_interface_issues(content, endpoints, error_codes)
    health = compute_health(content)
    summary = extract_summary(content)
    related = find_related_docs(content, current_doc_id, other_doc_titles or [])

    # 摘要置信度：基于段落平均长度 + 标题完整度
    stats = health.get("stats", {})
    avg_para = stats.get("avg_paragraph_length", 0)
    heading_complete = stats.get("h1", 0) == 1 and stats.get("h2", 0) >= 1
    confidence = 60
    if heading_complete:
        confidence += 20
    if 60 <= avg_para <= 280:
        confidence += 15
    if stats.get("paragraphs", 0) >= 3:
        confidence += 5
    confidence = min(98, confidence)

    return {
        "summary": {
            "text": summary,
            "confidence": confidence,
        },
        "health": health,
        "terminology": {
            "terms": terms,
            "issues": term_issues,
        },
        "interface": {
            "endpoints": endpoints,
            "error_codes": error_codes,
            "issues": iface_issues,
        },
        "knowledge": {
            "related": related,
        },
    }
