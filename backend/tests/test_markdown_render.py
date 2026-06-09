"""Markdown 渲染回归测试

P0-A-4: 验证 _md_to_html 对图片、表格、任务列表、嵌套列表、删除线、嵌套引用的渲染。
"""
import pytest
from app.services.build_service import _md_to_html


def test_image_renders():
    md = "![alt text](https://example.com/x.png)"
    out = _md_to_html(md)[0]
    assert '<figure class="media-figure">' in out
    assert 'src="https://example.com/x.png"' in out
    assert 'alt="alt text"' in out
    assert "<figcaption>alt text</figcaption>" in out
    # Phase 6 加的 img 优化: 提升阅读体验
    assert 'loading="lazy"' in out
    assert 'decoding="async"' in out


def test_table_renders():
    md = """
| 参数 | 类型 | 必填 |
|------|------|------|
| file | file | 是   |
| id   | int  | 否   |
""".strip()
    out = _md_to_html(md)[0]
    assert '<div class="table-wrap">' in out
    assert "<table" in out
    assert "<th>参数</th>" in out
    assert "<td>file</td>" in out


def test_task_list_renders():
    md = """
- [x] 已完成
- [ ] 未完成
""".strip()
    out = _md_to_html(md)[0]
    assert '<div class="task-list-wrap">' in out
    assert 'type="checkbox"' in out
    assert "checked" in out
    assert "已完成" in out
    assert "未完成" in out


def test_nested_list_renders():
    md = """
- 一级 A
  - 二级 A1
  - 二级 A2
- 一级 B
""".strip()
    out = _md_to_html(md)[0]
    # 应该是嵌套的 <ul>...</ul><ul>...</ul></ul>
    assert out.count("<ul>") >= 2
    assert out.count("</ul>") >= 2


def test_strikethrough_renders():
    md = "~~删除~~"
    out = _md_to_html(md)[0]
    assert "<del>删除</del>" in out


def test_nested_blockquote_renders():
    md = """
> 一级引用
> > 嵌套引用
> > > 三级
""".strip()
    out = _md_to_html(md)[0]
    # 至少 3 层 <blockquote>
    assert out.count("<blockquote>") >= 3


def test_inline_code_not_eaten_by_bold():
    md = "这不是 **加粗** 也不是 `code` 加粗"
    out = _md_to_html(md)[0]
    assert "<strong>加粗</strong>" in out
    assert "<code>code</code>" in out


def test_image_in_text_renders():
    md = "看这个图：![截图](https://x.com/y.png) 然后继续。"
    out = _md_to_html(md)[0]
    assert '<img' in out
    assert '<figure' not in out
    assert "然后继续" in out


@pytest.mark.parametrize(
    ("marker", "klass", "label"),
    [
        ("INFO", "admonition-info", "信息"),
        ("NOTE", "admonition-note", "注"),
        ("TIP", "admonition-tip", "提示"),
        ("IMPORTANT", "admonition-important", "重要"),
        ("WARNING", "admonition-warning", "警告"),
        ("CAUTION", "admonition-caution", "注意"),
        ("DANGER", "admonition-danger", "危险"),
    ],
)
def test_admonitions_render(marker, klass, label):
    md = f"> [!{marker}] 标题\n> 提示正文"
    out = _md_to_html(md)[0]
    assert f'class="admonition {klass}"' in out
    assert f'<span class="admonition-label">{label}</span>' in out
    assert '<span class="admonition-text">标题</span>' in out
    assert "提示正文" in out


def test_math_placeholders_render():
    md = "行内公式 $E=mc^2$。\n\n$$\na^2 + b^2 = c^2\n$$"
    out = _md_to_html(md)[0]
    assert '<span class="math-inline" role="math"><code>E=mc^2</code></span>' in out
    assert '<div class="math-block" role="math"><code>a^2 + b^2 = c^2</code></div>' in out
