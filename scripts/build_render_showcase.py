#!/usr/bin/env python3
"""Build the OpenDocX Markdown rendering showcase as a standalone HTML page."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SOURCE = ROOT / "examples" / "markdown-rendering-showcase.md"
OUT_DIR = ROOT / "docs" / "showcase"
OUT_HTML = OUT_DIR / "render-showcase.html"

sys.path.insert(0, str(BACKEND))

from app.services.build_service import (  # noqa: E402
    _md_to_html,
    _pyg_css_dark_scoped,
    _pyg_css_light,
    _render_toc,
)


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    return re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)


def copy_demo_assets() -> None:
    src = ROOT / "examples" / "static" / "images" / "opendocx-arch-placeholder.svg"
    dst = OUT_DIR / "static" / "images" / "opendocx-arch-placeholder.svg"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def page_template(body: str, toc: str) -> str:
    build_label = os.environ.get("OPENDOCX_SHOWCASE_BUILD_LABEL", "v0.1.0-alpha")
    return f"""<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%232563eb'/%3E%3Cpath d='M18 18h28v28H18z' fill='white' opacity='.95'/%3E%3Cpath d='M24 27h16M24 35h12' stroke='%232563eb' stroke-width='4' stroke-linecap='round'/%3E%3C/svg%3E">
  <title>OpenDocX 静态站渲染能力速查</title>
  <style>
    :root {{
      --brand: #2563eb;
      --brand-strong: #1d4ed8;
      --brand-soft: #eff6ff;
      --bg: #f8fafc;
      --surface: #ffffff;
      --surface-soft: #f6f8fb;
      --surface-raised: #ffffff;
      --fg: #172033;
      --fg-muted: #5f6b7a;
      --fg-subtle: #8b96a5;
      --border: #e2e8f0;
      --border-soft: #eef2f7;
      --code-bg: #f7f9fc;
      --code-fg: #1e293b;
      --inline-code-bg: #eef4ff;
      --inline-code-fg: #1d4ed8;
      --blockquote-bg: #f4f6fa;
      --blockquote-border: #d3d8e0;
      --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
      --shadow-md: 0 18px 50px rgba(15, 23, 42, 0.08);
      --radius: 12px;
      --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    }}
    :root[data-theme="dark"] {{
      --brand: #60a5fa;
      --brand-strong: #93c5fd;
      --brand-soft: rgba(96, 165, 250, 0.14);
      --bg: #0f172a;
      --surface: #111827;
      --surface-soft: #162033;
      --surface-raised: #182235;
      --fg: #e5e7eb;
      --fg-muted: #aab4c2;
      --fg-subtle: #7f8b9b;
      --border: #2a3547;
      --border-soft: #202b3c;
      --code-bg: #0b1220;
      --code-fg: #dbeafe;
      --inline-code-bg: rgba(96, 165, 250, 0.16);
      --inline-code-fg: #bfdbfe;
      --blockquote-bg: #141e31;
      --blockquote-border: #465266;
      --shadow-sm: none;
      --shadow-md: 0 18px 50px rgba(0, 0, 0, 0.25);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--font-sans);
      font-size: 16px;
      line-height: 1.72;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }}
    a {{ color: var(--brand); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .progress {{ position: fixed; top: 0; left: 0; right: 0; height: 3px; z-index: 20; background: transparent; }}
    .progress span {{ display: block; width: 0; height: 100%; background: linear-gradient(90deg, var(--brand), #14b8a6); }}
    .topbar {{
      position: sticky; top: 0; z-index: 10;
      display: flex; align-items: center; gap: 16px;
      min-height: 64px; padding: 0 32px;
      border-bottom: 1px solid var(--border);
      background: color-mix(in srgb, var(--surface) 88%, transparent);
      backdrop-filter: blur(18px);
    }}
    .brand {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
    .brand strong {{ font-size: 16px; line-height: 1.2; }}
    .brand span {{ color: var(--fg-muted); font-size: 12px; line-height: 1.2; }}
    .topbar-spacer {{ flex: 1; }}
    .theme-toggle {{
      height: 34px; padding: 0 12px;
      border: 1px solid var(--border); border-radius: 999px;
      background: var(--surface); color: var(--fg-muted);
      font: inherit; font-size: 13px; cursor: pointer;
    }}
    .theme-toggle:hover {{ border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }}
    .shell {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 260px;
      gap: 36px;
      width: min(1440px, 100%);
      margin: 0 auto;
      padding: 48px 36px 72px;
    }}
    .content-card {{
      min-width: 0;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow-md);
      overflow: hidden;
    }}
    .hero {{
      padding: 38px 44px 28px;
      border-bottom: 1px solid var(--border-soft);
      background: linear-gradient(135deg, var(--surface) 0%, var(--surface-soft) 100%);
    }}
    .eyebrow {{ margin: 0 0 10px; color: var(--brand); font-size: 13px; font-weight: 700; letter-spacing: 0.06em; }}
    .hero h1 {{ margin: 0; font-size: clamp(30px, 4vw, 48px); line-height: 1.1; letter-spacing: -0.02em; }}
    .hero p {{ max-width: 760px; margin: 16px 0 0; color: var(--fg-muted); }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }}
    .meta span {{ padding: 5px 10px; border-radius: 999px; background: var(--brand-soft); color: var(--brand-strong); font-size: 13px; }}
    .content {{ padding: 10px 44px 56px; min-width: 0; }}
    .content h1, .content h2, .content h3 {{ position: relative; color: var(--fg); line-height: 1.25; scroll-margin-top: 88px; }}
    .content h1 {{ margin: 40px 0 18px; font-size: 34px; letter-spacing: -0.02em; }}
    .content h2 {{ margin: 46px 0 18px; padding-top: 18px; border-top: 1px solid var(--border-soft); font-size: 27px; letter-spacing: -0.015em; }}
    .content h3 {{ margin: 32px 0 14px; font-size: 21px; }}
    .content h4, .content h5, .content h6 {{ margin: 18px 0 8px; font-size: 16px; }}
    .content h4 {{ font-weight: 800; }}
    .content h5 {{ font-weight: 700; color: var(--fg-muted); }}
    .content h6 {{ font-weight: 500; color: var(--fg-muted); font-style: italic; }}
    .content p {{ margin: 0 0 18px; }}
    .content ul, .content ol {{ margin: 0 0 20px 24px; padding: 0; }}
    .content li {{ margin: 6px 0; }}
    .content .anchor {{
      position: absolute; left: -24px; opacity: 0; color: var(--fg-subtle);
      font-weight: 400; text-decoration: none; transition: opacity 0.15s ease;
    }}
    .content h1:hover .anchor, .content h2:hover .anchor, .content h3:hover .anchor {{ opacity: 1; }}
    .content code, .content pre {{ font-family: var(--font-mono); }}
    .content p code, .content li code {{
      padding: 2px 6px; border-radius: 7px;
      background: var(--inline-code-bg); color: var(--inline-code-fg);
      font-size: 0.88em;
    }}
    .content blockquote {{
      margin: 22px 0; padding: 18px 22px;
      border-left: 4px solid var(--blockquote-border);
      border-radius: 0 var(--radius) var(--radius) 0;
      background: var(--blockquote-bg); color: var(--fg-muted);
    }}
    .content blockquote p:last-child {{ margin-bottom: 0; }}
    .content hr {{
      border: 0; height: 1px; margin: 38px 0;
      background: linear-gradient(90deg, transparent, var(--border), transparent);
    }}
    .syntax-hint {{
      display: block; margin: -8px 0 22px;
      color: var(--fg-subtle); text-align: right;
      font-family: var(--font-mono); font-size: 13px;
    }}
    .table-wrap {{
      width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;
      margin: 24px 0; border: 1px solid var(--border);
      border-radius: var(--radius); box-shadow: var(--shadow-sm);
      background: var(--surface);
    }}
    table {{ width: 100%; min-width: 620px; border-spacing: 0; border-collapse: separate; font-variant-numeric: tabular-nums; }}
    th, td {{ padding: 13px 15px; border: 0; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ position: sticky; top: 0; background: var(--surface-soft); color: var(--fg); font-weight: 700; white-space: nowrap; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover td {{ background: var(--surface-soft); }}
    .code-block {{
      margin: 24px 0; overflow: hidden;
      border: 1px solid var(--border); border-radius: var(--radius);
      background: var(--code-bg); box-shadow: var(--shadow-sm);
    }}
    .code-block-header {{
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      min-height: 40px; padding: 0 12px 0 16px;
      border-bottom: 1px solid var(--border);
      background: var(--surface-soft); color: var(--fg-muted);
      font-family: var(--font-mono); font-size: 12px;
    }}
    .code-block-header span {{
      display: inline-flex; align-items: center; height: 24px; padding: 0 8px;
      border-radius: 7px; background: var(--surface); border: 1px solid var(--border);
    }}
    .code-copy-btn {{
      height: 26px; padding: 0 9px; border: 1px solid var(--border);
      border-radius: 7px; background: var(--surface); color: var(--fg-muted);
      font: inherit; font-size: 12px; cursor: pointer;
    }}
    .code-copy-btn:hover {{ color: var(--brand); border-color: var(--brand); background: var(--brand-soft); }}
    .highlight {{ margin: 0; background: var(--code-bg) !important; color: var(--code-fg); overflow-x: auto; }}
    .highlight pre, .content pre {{
      margin: 0; padding: 18px 20px; overflow-x: auto;
      background: transparent; color: inherit; line-height: 1.6; font-size: 14px;
    }}
    .diagram-block .mermaid {{
      display: flex; justify-content: center; min-width: 720px;
      padding: 22px; margin: 0; background: var(--surface);
    }}
    .admonition {{
      margin: 24px 0; padding: 17px 20px;
      border: 1px solid; border-left-width: 5px;
      border-radius: var(--radius); box-shadow: var(--shadow-sm);
    }}
    .admonition-title {{ display: flex; align-items: center; gap: 9px; margin-bottom: 8px; font-weight: 700; }}
    .admonition-title svg {{ width: 18px; height: 18px; flex: 0 0 auto; }}
    .admonition-label {{ white-space: nowrap; }}
    .admonition p:last-child {{ margin-bottom: 0; }}
    .admonition-note {{ background: #f6f8fa; border-color: #d8dee4; border-left-color: #6b7785; }}
    .admonition-tip {{ background: #f0fdf4; border-color: #bbf7d0; border-left-color: #1a7f37; }}
    .admonition-info {{ background: #eff6ff; border-color: #bfdbfe; border-left-color: #0969da; }}
    .admonition-important {{ background: #faf5ff; border-color: #e9d5ff; border-left-color: #7c3aed; }}
    .admonition-warning {{ background: #fff8e1; border-color: #fde68a; border-left-color: #9a6700; }}
    .admonition-caution {{ background: #fff7ed; border-color: #fed7aa; border-left-color: #ea580c; }}
    .admonition-danger {{ background: #ffebe9; border-color: #fecaca; border-left-color: #d1242f; }}
    .admonition-tip .admonition-label {{ color: #1a7f37; }}
    .admonition-info .admonition-label {{ color: #0969da; }}
    .admonition-important .admonition-label {{ color: #7c3aed; }}
    .admonition-warning .admonition-label {{ color: #9a6700; }}
    .admonition-caution .admonition-label {{ color: #ea580c; }}
    .admonition-danger .admonition-label {{ color: #d1242f; }}
    :root[data-theme="dark"] .admonition-note {{ background: #161b22; border-color: #30363d; border-left-color: #6b7785; }}
    :root[data-theme="dark"] .admonition-tip {{ background: #0f2419; border-color: #1f5130; border-left-color: #3fb950; }}
    :root[data-theme="dark"] .admonition-info {{ background: #0b1f3a; border-color: #1d4d8f; border-left-color: #58a6ff; }}
    :root[data-theme="dark"] .admonition-important {{ background: #221432; border-color: #5b2c82; border-left-color: #a78bfa; }}
    :root[data-theme="dark"] .admonition-warning {{ background: #341a00; border-color: #633c01; border-left-color: #d29922; }}
    :root[data-theme="dark"] .admonition-caution {{ background: #321500; border-color: #7c2d12; border-left-color: #fb923c; }}
    :root[data-theme="dark"] .admonition-danger {{ background: #2d0a0e; border-color: #7f1d1d; border-left-color: #f85149; }}
    .task-list-wrap {{
      margin: 22px 0; padding: 12px 18px;
      border: 1px solid var(--border); border-radius: var(--radius);
      background: var(--surface-soft);
    }}
    .task-list-wrap ul {{ margin: 0; list-style: none; }}
    li.task-list-item {{ display: flex; align-items: flex-start; gap: 10px; margin: 0; padding: 8px 0; }}
    li.task-list-item input[type="checkbox"] {{ width: 17px; height: 17px; margin: 4px 0 0; accent-color: var(--brand); flex: 0 0 auto; }}
    li.task-list-item:has(input[checked]) {{ color: var(--fg-muted); text-decoration: line-through; text-decoration-color: var(--fg-subtle); }}
    .media-figure {{
      margin: 28px auto; overflow: hidden;
      border: 1px solid var(--border); border-radius: var(--radius);
      background: var(--surface-soft); box-shadow: var(--shadow-sm);
    }}
    .media-figure img {{ width: 100%; margin: 0; border-radius: 0; }}
    .media-figure figcaption {{
      padding: 10px 14px; border-top: 1px solid var(--border);
      color: var(--fg-muted); font-size: 14px; text-align: center;
    }}
    img, video {{ display: block; max-width: 100%; height: auto; margin: 24px auto; border-radius: var(--radius); }}
    iframe {{ display: block; max-width: 100%; margin: 24px auto; border: 1px solid var(--border); border-radius: var(--radius); }}
    .math-inline {{
      display: inline-flex; padding: 1px 8px; border-radius: 8px;
      background: var(--inline-code-bg); color: var(--fg);
      font-family: Georgia, "Times New Roman", serif; font-style: italic;
    }}
    .math-inline code {{ padding: 0; background: transparent; color: inherit; font-family: inherit; }}
    .math-block {{
      margin: 24px 0; padding: 22px;
      border: 1px solid var(--border); border-radius: var(--radius);
      background: var(--surface-soft); text-align: center;
      font-family: Georgia, "Times New Roman", serif; font-style: italic;
      overflow-x: auto;
    }}
    .math-block code {{ padding: 0; background: transparent; color: var(--fg); font-family: inherit; font-size: 1.08em; white-space: pre-wrap; }}
    .footnotes {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--border); color: var(--fg-muted); font-size: 14px; }}
    .toc {{
      position: sticky; top: 88px; align-self: start;
      max-height: calc(100vh - 112px); overflow: auto;
      padding: 18px; border: 1px solid var(--border);
      border-radius: 16px; background: var(--surface);
      box-shadow: var(--shadow-sm);
    }}
    .toc-title {{ margin-bottom: 10px; color: var(--fg-subtle); font-size: 12px; font-weight: 800; letter-spacing: 0.06em; }}
    .toc-list {{ margin: 0; padding: 0; list-style: none; }}
    .toc-list li {{ margin: 1px 0; }}
    .toc-list a {{
      display: block; padding: 5px 8px; border-left: 2px solid transparent;
      color: var(--fg-muted); border-radius: 0 8px 8px 0;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 13px;
    }}
    .toc-list a:hover {{ color: var(--fg); background: var(--surface-soft); text-decoration: none; }}
    .toc-list a.active {{ color: var(--brand); border-left-color: var(--brand); background: var(--brand-soft); font-weight: 700; }}
    .footer {{ padding: 26px 44px; border-top: 1px solid var(--border-soft); color: var(--fg-subtle); font-size: 13px; }}
    { _pyg_css_light }
    { _pyg_css_dark_scoped }
    @media (max-width: 1080px) {{
      .shell {{ grid-template-columns: 1fr; padding: 24px 18px 56px; }}
      .toc {{ position: static; order: -1; max-height: 260px; }}
      .content-card {{ border-radius: 14px; }}
      .hero, .content, .footer {{ padding-left: 24px; padding-right: 24px; }}
    }}
    @media (max-width: 640px) {{
      .topbar {{ min-height: 58px; padding: 0 16px; }}
      .brand span {{ display: none; }}
      .content h1 {{ font-size: 28px; }}
      .content h2 {{ font-size: 23px; }}
      .content h3 {{ font-size: 19px; }}
      .content .anchor {{ position: static; opacity: 0.55; margin-right: 6px; }}
      .syntax-hint {{ text-align: left; }}
      .hero, .content, .footer {{ padding-left: 18px; padding-right: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="progress" aria-hidden="true"><span id="readingProgress"></span></div>
  <header class="topbar">
    <div class="brand">
      <strong>OpenDocX</strong>
      <span>静态站渲染能力速查</span>
    </div>
    <div class="topbar-spacer"></div>
    <button class="theme-toggle" type="button" id="themeToggle">切换深浅色</button>
  </header>
  <main class="shell">
    <article class="content-card">
      <section class="hero">
        <p class="eyebrow">MARKDOWN RENDERING SHOWCASE</p>
        <h1>OpenDocX 静态站渲染能力速查</h1>
        <p>这是一份可直接发布到 GitHub Pages 的渲染示例页，用来展示 OpenDocX 静态站对 Markdown、提示块、表格、代码高亮、图片、任务列表、Mermaid 和公式占位的支持效果。</p>
        <div class="meta">
          <span>v0.1.0-alpha</span>
          <span>中文示例数据</span>
          <span>构建标识 {build_label}</span>
        </div>
      </section>
      <section class="content">
        {body}
      </section>
      <footer class="footer">Built with OpenDocX Markdown renderer. Source: examples/markdown-rendering-showcase.md</footer>
    </article>
    {toc}
  </main>
  <script type="module">
    const root = document.documentElement;
    const storedTheme = localStorage.getItem('opendocx-showcase-theme');
    if (storedTheme) root.dataset.theme = storedTheme;
    document.getElementById('themeToggle')?.addEventListener('click', () => {{
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      localStorage.setItem('opendocx-showcase-theme', next);
    }});

    const progress = document.getElementById('readingProgress');
    const updateProgress = () => {{
      const max = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = max <= 0 ? '0%' : `${{Math.min(100, window.scrollY / max * 100)}}%`;
    }};
    updateProgress();
    window.addEventListener('scroll', updateProgress, {{ passive: true }});

    document.querySelectorAll('.code-copy-btn').forEach((button) => {{
      button.addEventListener('click', async () => {{
        const block = button.closest('.code-block');
        const text = block?.querySelector('.highlight pre, pre.mermaid')?.textContent || '';
        await navigator.clipboard.writeText(text);
        button.textContent = '已复制';
        setTimeout(() => button.textContent = '复制', 1200);
      }});
    }});

    const tocLinks = [...document.querySelectorAll('[data-toc-id]')];
    const headings = tocLinks.map((link) => document.getElementById(link.dataset.tocId)).filter(Boolean);
    const observer = new IntersectionObserver((entries) => {{
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!visible) return;
      tocLinks.forEach((link) => link.classList.toggle('active', link.dataset.tocId === visible.target.id));
    }}, {{ rootMargin: '-90px 0px -72% 0px', threshold: 0.01 }});
    headings.forEach((heading) => observer.observe(heading));

    const mermaidBlocks = document.querySelectorAll('pre.mermaid');
    if (mermaidBlocks.length) {{
      import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs').then((mermaid) => {{
        mermaid.default.initialize({{ startOnLoad: false, theme: root.dataset.theme === 'dark' ? 'dark' : 'default' }});
        mermaid.default.run({{ nodes: mermaidBlocks }});
      }}).catch(() => {{}});
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    md = strip_frontmatter(SOURCE.read_text(encoding="utf-8"))
    body, toc_data = _md_to_html(md)
    toc_html = _render_toc(toc_data)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copy_demo_assets()
    OUT_HTML.write_text(page_template(body, toc_html), encoding="utf-8")
    print(f"Built {OUT_HTML.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
