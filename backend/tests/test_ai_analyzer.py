"""P1-UI-6 高级 AI 卡 — 文档分析器单元测试

不依赖数据库，纯函数测试。
"""
import pytest
from app.services.ai_analyzer import (
    extract_terms,
    detect_terminology_issues,
    extract_endpoints,
    extract_error_codes,
    detect_interface_issues,
    compute_health,
    extract_summary,
    find_related_docs,
    analyze_document,
)


# ── extract_terms ─────────────────────────────────────────────

def test_extract_terms_chinese_high_frequency():
    """中文高频 2/3/4 字组合"""
    text = "点击注册按钮。点击按钮完成注册。按钮在右上角。"
    terms = extract_terms(text, top_n=10)
    assert any(t["term"] == "点击" and t["count"] >= 2 for t in terms)
    assert any(t["term"] == "按钮" and t["count"] >= 2 for t in terms)


def test_extract_terms_english_acronym():
    """英文缩写 (API/SDK/LLM)"""
    text = "API 调用方式。API 鉴权。LLM 服务通过 LLM 网关。"
    terms = extract_terms(text, top_n=10)
    term_names = {t["term"] for t in terms}
    assert "API" in term_names
    assert "LLM" in term_names


def test_extract_terms_dedup_substring():
    """子串合并：父串频率>=子串时，子串被去重"""
    text = "错误码 401。错误码 403。错误码 500。"
    terms = extract_terms(text, top_n=10)
    term_names = [t["term"] for t in terms]
    # 父串"错误码"应保留，子串"误码"应被去重
    assert "错误码" in term_names
    assert "误码" not in term_names


# ── detect_terminology_issues ──────────────────────────────────

def test_detect_terminology_mixed_uses():
    """同义词在不同句子中独立出现 → 混用"""
    text = "本文使用 RAG 技术。" + "x" * 40 + "检索增强可以提高准确率。"
    issues = detect_terminology_issues(text)
    assert any("RAG" in i and "检索增强" in i for i in issues)


def test_detect_terminology_pure_chinese_paren_explanation():
    """同一句中 'RAG (检索增强)' 不算混用"""
    text = "RAG (检索增强生成) 是一种技术。"
    issues = detect_terminology_issues(text)
    assert not any("RAG" in i and "检索增强" in i for i in issues)


def test_detect_api_case_inconsistent():
    """API 大小写混用（需距离 > 30 字符才算）"""
    text = "调用 API 接口获取数据。" + "x" * 40 + "访问 api 接口验证。"
    issues = detect_terminology_issues(text)
    assert any("API 大小写" in i for i in issues)


# ── extract_endpoints ─────────────────────────────────────────

def test_extract_endpoints_normal():
    """3 种写法都能抓到"""
    text = """
请使用 **GET** /api/v1/users 获取列表。
**POST** /api/v1/users 创建。
GET /api/v1/users/{id} 获取详情。
"""
    eps = extract_endpoints(text)
    methods_paths = {(e["method"], e["path"]) for e in eps}
    assert ("GET", "/api/v1/users") in methods_paths
    assert ("POST", "/api/v1/users") in methods_paths
    assert ("GET", "/api/v1/users/{id}") in methods_paths


def test_extract_endpoints_in_code_block():
    """围栏代码块里的端点必须被抓到（curl/API 签名）"""
    text = """
## 上传文档

```
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

### 查询

```
GET /api/v1/documents?project_id=<id>
```
"""
    eps = extract_endpoints(text)
    paths = {e["path"] for e in eps}
    assert "/api/v1/documents/upload" in paths
    # query string 里的 / 也算
    assert any("documents" in p for p in paths)


def test_extract_endpoints_ignores_example_url():
    """代码块里的示例 URL 不应误抓"""
    text = """
### GET /api/v1/users

```bash
curl http://api.example.com/api/v1/users
```
"""
    eps = extract_endpoints(text)
    # 只应该有 GET /api/v1/users（来自标题）
    # 不应该有 example.com 的 URL
    paths = [e["path"] for e in eps]
    assert "/api/v1/users" in paths
    # example.com 出现在代码块里已被剥离，不应被抓
    for p in paths:
        assert "example.com" not in p


# ── extract_error_codes ───────────────────────────────────────

def test_extract_error_codes():
    text = "错误码 401 表示未授权。HTTP status 403 表示禁止。状态码 500 表示服务器错误。"
    codes = extract_error_codes(text)
    assert 401 in codes
    assert 403 in codes
    assert 500 in codes


def test_detect_interface_issues_missing_critical():
    """有端点 + 缺 401/403/429/500 → 提示补"""
    text = """
### GET /api/v1/users
无鉴权描述。
"""
    issues = detect_interface_issues(text, extract_endpoints(text), extract_error_codes(text))
    assert any("错误码" in i for i in issues)


# ── compute_health ────────────────────────────────────────────

def test_compute_health_short_content():
    """< 50 字符 → 0 分"""
    h = compute_health("hi")
    assert h["score"] == 0
    assert h["grade"] == "待评估"


def test_compute_health_well_structured():
    """结构良好的文档应得高分"""
    text = """# 主标题

简短段落 A，介绍文档目的。

## 章节 1

内容段落 B。

## 章节 2

```python
print('hello')
```

参考 [链接](https://example.com) 和 [另一个](https://example.com/2)。
"""
    h = compute_health(text)
    assert h["score"] >= 50
    assert h["breakdown"]["heading"] >= 20
    assert h["breakdown"]["code"] >= 6


def test_compute_health_breakdown_keys():
    """breakdown 4 项必须都在"""
    text = """# 主标题

这是第一段有意义的说明文字，介绍文档目的。

## 章节

更多内容段落，确保超过 50 字符阈值，让 compute_health 真正进入评分流程。
"""
    h = compute_health(text)
    assert h["score"] > 0
    for k in ("heading", "code", "paragraph", "link"):
        assert k in h["breakdown"]


# ── extract_summary ───────────────────────────────────────────

def test_extract_summary_picks_descriptive_paragraph():
    """优先取说明性段落（非标题）"""
    text = "# 主标题\n\n这是一段有意义的说明文字，介绍文档目的和功能。"
    s = extract_summary(text)
    assert "说明文字" in s
    assert not s.startswith("#")


def test_extract_summary_strips_code_blocks():
    """代码块不应出现在摘要里"""
    text = "# API\n\n说明文字在这里。\n\n```python\nsecret_code()\n```\n"
    s = extract_summary(text)
    assert "secret_code" not in s


# ── find_related_docs ─────────────────────────────────────────

def test_find_related_docs_match_by_title():
    """基于标题匹配"""
    content = "本文档介绍 RAGFlow 系统的部署、配置和监控。系统采用分布式架构。"
    others = [
        {"id": "1", "title": "RAGFlow 架构设计"},
        {"id": "2", "title": "用户管理"},
    ]
    related = find_related_docs(content, current_doc_id=None, other_doc_titles=others)
    assert len(related) >= 1
    assert related[0]["id"] == "1"
    matched = str(related[0]["matched_terms"])
    assert "RAGFlow" in matched or "RAG" in matched or "架构" in matched


def test_find_related_docs_excludes_self():
    """current_doc_id 应被排除"""
    content = "测试内容。"
    others = [{"id": "self", "title": "测试"}]
    related = find_related_docs(content, current_doc_id="self", other_doc_titles=others)
    assert related == []


# ── analyze_document (集成) ──────────────────────────────────

def test_analyze_document_returns_all_sections():
    """返回 5 个 section"""
    text = """# API

## 鉴权

错误码 401。

### GET /api/v1/test

说明段落。
"""
    r = analyze_document(text)
    assert "summary" in r
    assert "health" in r
    assert "terminology" in r
    assert "interface" in r
    assert "knowledge" in r
    assert "text" in r["summary"]
    assert "confidence" in r["summary"]
    assert 401 in r["interface"]["error_codes"]


def test_analyze_document_empty():
    """空内容不报错"""
    r = analyze_document("")
    assert r["summary"]["text"] == ""
    assert r["health"]["score"] == 0
