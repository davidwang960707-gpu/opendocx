"""构建服务 — Markdown → 静态 HTML 站（mistune + pygments）"""
import os
import re
import html
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BuildLog, BuildStatus, Document, DocumentAsset, Version, Project
from app.config import get_settings

# mistune 3.x Markdown 渲染器（GFM 完整支持）
import mistune
# Pygments 服务端语法高亮
from pygments import highlight as _pyg_highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

settings = get_settings()

# ── 共享 mistune 实例（避免每次重复构建） ─────────────────
_md = mistune.create_markdown(
    plugins=['table', 'task_lists', 'strikethrough', 'url', 'footnotes', 'abbr', 'def_list'],
    escape=True,
    hard_wrap=False,
)

# ── Pygments 双主题 stylesheet（注入到每个页面 <style> 末尾） ──
# 段 B: 切到 .replace 模式后, 模板里的 {} 不会被 .format 解析, 不需要转义
_pyg_css_light = HtmlFormatter(style='default').get_style_defs('.highlight')
_pyg_css_dark = HtmlFormatter(style='github-dark').get_style_defs('.highlight')


def _scope_pyg_dark(css: str) -> str:
    """R7 反馈: pygments 深色 CSS 没有父选择器限定, 浅色主题下也生效
    → 浅色主题下字色深 token + 容器浅背景 = 难读

    修法: 给每条规则加 :root[data-theme="dark"] 前缀, 深色才生效
    """
    out: list[str] = []
    for line in css.splitlines():
        # 跳过空行 + 注释
        s = line.strip()
        if not s or s.startswith("/*"):
            out.append(line)
            continue
        # 跳过 @media / @keyframes 等 at-rule 容器 (保留原样, 由深色模式浏览器自行启用)
        if s.startswith("@"):
            out.append(line)
            continue
        # 找第一个 { 位置
        brace = line.find("{")
        if brace == -1:
            out.append(line)
            continue
        # 注释内的 { 不算 (Pygments 输出没有这种情况, 跳过)
        selectors = line[:brace].rstrip()
        rest = line[brace:]
        out.append(f':root[data-theme="dark"] {selectors}{rest}')
    return "\n".join(out)


_pyg_css_dark_scoped = _scope_pyg_dark(_pyg_css_dark)


def _attrs_to_dict(attrs: str) -> dict[str, str]:
    """Parse simple HTML attributes emitted by mistune for post-processing."""
    return {
        m.group(1): html.unescape(m.group(2) or m.group(3) or "")
        for m in re.finditer(r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', attrs)
    }


# ── 反馈区/评论区 HTML (内联到每页, 不依赖外部静态服务) ────────
# 文档页 (slug-pages) 渲染这段; 首页/章节页 build 时整段替换为空
_FEEDBACK_SECTION = r"""
      <!-- 反馈区 (点赞/点踩/收藏) -->
      <div class="feedback-bar" id="feedbackBar" data-doc-slug="{doc_slug}" data-version-id="{version_id}">
        <div class="feedback-bar-left">
          <span class="feedback-label">这篇文章有帮助吗？</span>
          <button class="fb-btn" id="fbLike" type="button" aria-label="点赞">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
            <span id="fbLikeCount">0</span>
          </button>
          <button class="fb-btn" id="fbDislike" type="button" aria-label="点踩">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>
            <span id="fbDislikeCount">0</span>
          </button>
        </div>
        <button class="fb-btn" id="fbBookmark" type="button" aria-label="收藏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
          <span id="fbBookmarkLabel">收藏</span>
        </button>
      </div>
      <!-- 评论区 -->
      <section class="comments-section" id="commentsSection" data-doc-id="{doc_id}">
        <h3>读者反馈与讨论</h3>
        <form class="comment-form" id="commentForm">
          <input type="text" id="commentInput" placeholder="留下你的问题或建议..." maxlength="500" required>
          <button type="submit">提交</button>
        </form>
        <div class="comment-list" id="commentList">
          <div class="comment-empty">加载中...</div>
        </div>
      </section>
"""

# ── 反馈区/评论区 JS (内联到每页, 不依赖外部静态服务) ────────
# JS 内有大量 {} 对象字面量, 不能走 .format(), 改用 .replace() 注入
_FEEDBACK_JS = r"""
(function() {
  // === 访客 ID 持久化 (localStorage uuid) ===
  function getVisitorId() {
    var key = 'opendocx_visitor_id';
    var v = localStorage.getItem(key);
    if (!v) {
      v = 'v-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem(key, v);
    }
    return v;
  }
  var visitorId = getVisitorId();
  var API_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://localhost:8001/api/v1'  // dev: 直接打后端 (Vite proxy 不到 static 站)
    : '/api/v1';

  // === Toast ===
  var fbToast = document.getElementById('fbToast');
  var fbToastTimer = null;
  function showToast(msg, ok) {
    if (!fbToast) return;
    fbToast.textContent = msg;
    fbToast.style.background = ok ? 'var(--brand)' : 'var(--fg)';
    fbToast.style.color = ok ? '#fff' : 'var(--bg)';
    fbToast.classList.add('show');
    if (fbToastTimer) clearTimeout(fbToastTimer);
    fbToastTimer = setTimeout(function() { fbToast.classList.remove('show'); }, 1800);
  }

  // === 反馈区 (点赞/点踩/收藏) ===
  var fbBar = document.getElementById('feedbackBar');
  var commentsSection = document.getElementById('commentsSection');
  if (!fbBar || !commentsSection) return;  // 首页无反馈区
  var docId = commentsSection.getAttribute('data-doc-id');
  if (!docId) return;

  var likeBtn = document.getElementById('fbLike');
  var dislikeBtn = document.getElementById('fbDislike');
  var bookmarkBtn = document.getElementById('fbBookmark');
  var likeCount = document.getElementById('fbLikeCount');
  var dislikeCount = document.getElementById('fbDislikeCount');
  var bookmarkLabel = document.getElementById('fbBookmarkLabel');

  function setActive(btn, on) { btn.classList.toggle('active', on); }

  function loadReactions() {
    fetch(API_BASE + '/feedbacks/' + encodeURIComponent(docId) + '/reactions', {
      headers: { 'X-Visitor-Id': visitorId }
    })
    .then(function(r) { return r.json(); })
    .then(function(j) {
      if (!j.success) return;
      var d = j.data || {};
      likeCount.textContent = d.like_count || 0;
      dislikeCount.textContent = d.dislike_count || 0;
      bookmarkLabel.textContent = (d.my_reaction === 'bookmark') ? '已收藏' : '收藏';
      setActive(likeBtn, d.my_reaction === 'like');
      setActive(dislikeBtn, d.my_reaction === 'dislike');
      setActive(bookmarkBtn, d.my_reaction === 'bookmark');
      currentReactionId = d.my_reaction_id || null;
    })
    .catch(function() { showToast('加载反馈统计失败', false); });
  }

  function react(kind) {
    // 切换语义: 如果当前 my_reaction === kind, 走 DELETE; 否则 POST
    if (likeBtn.classList.contains('active') && kind === 'like') {
      deleteReaction(currentReactionId);
      return;
    }
    if (dislikeBtn.classList.contains('active') && kind === 'dislike') {
      deleteReaction(currentReactionId);
      return;
    }
    fetch(API_BASE + '/feedbacks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Visitor-Id': visitorId },
      body: JSON.stringify({
        document_id: docId,
        version_id: fbBar.getAttribute('data-version-id'),
        kind: kind
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(j) {
      if (j.success) {
        showToast(kind === 'like' ? '已点赞' : kind === 'dislike' ? '已点踩' : '已收藏', true);
        loadReactions();
      } else {
        showToast('操作失败: ' + (j.detail || '未知错误'), false);
      }
    })
    .catch(function() { showToast('网络错误', false); });
  }

  // 缓存当前 reaction id (用于 toggle off)
  var currentReactionId = null;
  // ↑ loadReactions 已在 117 行定义, 这里只补 currentReactionId 赋值

  function deleteReaction(fid) {
    if (!fid) {
      // fallback: 全量刷新后重试
      loadReactions();
      return;
    }
    fetch(API_BASE + '/feedbacks/' + fid, {
      method: 'DELETE',
      headers: { 'X-Visitor-Id': visitorId }
    })
    .then(function(r) { return r.json(); })
    .then(function(j) {
      if (j.success) {
        showToast('已取消', true);
        loadReactions();
      } else {
        showToast('取消失败: ' + (j.detail || '未知错误'), false);
      }
    })
    .catch(function() { showToast('网络错误', false); });
  }

  if (likeBtn) likeBtn.addEventListener('click', function() { react('like'); });
  if (dislikeBtn) dislikeBtn.addEventListener('click', function() { react('dislike'); });
  if (bookmarkBtn) bookmarkBtn.addEventListener('click', function() { react('bookmark'); });

  // === 评论区 ===
  var commentList = document.getElementById('commentList');
  var commentForm = document.getElementById('commentForm');
  var commentInput = document.getElementById('commentInput');

  function timeAgo(iso) {
    var d = new Date(iso);
    var diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return Math.floor(diff) + ' 秒前';
    if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
    if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
    if (diff < 2592000) return Math.floor(diff / 86400) + ' 天前';
    return d.toLocaleDateString('zh-CN');
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function renderComment(c, depth) {
    depth = depth || 0;
    var replies = (c.replies || []).map(function(r) { return renderComment(r, depth + 1); }).join('');
    var safe = escapeHtml(c.body || '');
    var name = escapeHtml(c.user_name || '匿名读者');
    var ago = timeAgo(c.created_at);
    return '' +
        '<div class="comment-item" data-depth="' + depth + '">' +
          '<div class="comment-meta">' +
            '<strong>' + name + '</strong>' +
            '<span>' + ago + '</span>' +
          '</div>' +
          '<div class="comment-body">' + safe + '</div>' +
          '<div class="comment-actions">' +
            '<button data-reply="' + c.id + '" type="button" aria-label="回复">' +
              '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>' +
              '<span>回复</span>' +
            '</button>' +
            '<button data-delete="' + c.id + '" type="button" aria-label="删除">' +
              '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>' +
              '<span>删除</span>' +
            '</button>' +
          '</div>' +
          (replies ? '<div class="comment-replies" data-parent-depth="' + depth + '">' + replies + '</div>' : '') +
        '</div>';
  }

  function loadComments() {
    fetch(API_BASE + '/feedbacks/' + encodeURIComponent(docId) + '/comments')
      .then(function(r) { return r.json(); })
      .then(function(j) {
        if (!j.success) { commentList.innerHTML = '<div class="comment-empty">加载失败</div>'; return; }
        var items = (j.data && j.data.items) || [];
        if (items.length === 0) {
          commentList.innerHTML = '<div class="comment-empty">还没有反馈, 抢沙发 →</div>';
        } else {
          commentList.innerHTML = items.map(function(c) { return renderComment(c, 0); }).join('');
        }
      })
      .catch(function() {
        commentList.innerHTML = '<div class="comment-empty">网络错误</div>';
      });
  }

  function postComment(body, parentId) {
    fetch(API_BASE + '/feedbacks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Visitor-Id': visitorId },
      body: JSON.stringify({
        document_id: docId,
        version_id: fbBar.getAttribute('data-version-id'),
        kind: 'comment',
        body: body,
        parent_id: parentId || null
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(j) {
      if (j.success) {
        showToast(parentId ? '已回复' : '已提交', true);
        loadComments();
      } else {
        showToast('提交失败: ' + (j.detail || '未知错误'), false);
      }
    })
    .catch(function() { showToast('网络错误', false); });
  }

  if (commentForm) {
    commentForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var v = (commentInput.value || '').trim();
      if (!v) return;
      postComment(v, null);
      commentInput.value = '';
    });
  }

  // 事件委托: 回复/删除
  if (commentList) {
    commentList.addEventListener('click', function(e) {
      var replyBtn = e.target.closest && e.target.closest('button[data-reply]');
      var deleteBtn = e.target.closest && e.target.closest('button[data-delete]');
      if (replyBtn) {
        var pid = replyBtn.getAttribute('data-reply');
        var item = replyBtn.closest('.comment-item');
        if (!item) return;
        if (item.querySelector('.comment-reply-form')) {
          item.querySelector('.comment-reply-form').remove();
          return;
        }
        var form = document.createElement('div');
        form.className = 'comment-reply-form';
        form.innerHTML = '<input type="text" placeholder="回复 ' + escapeHtml(replyBtn.parentElement.previousElementSibling.previousElementSibling.querySelector('strong').textContent) + '..." maxlength="500"><button type="button">发送</button>';
        var input = form.querySelector('input');
        var btn = form.querySelector('button');
        btn.addEventListener('click', function() {
          var v = (input.value || '').trim();
          if (!v) return;
          postComment(v, pid);
        });
        item.appendChild(form);
        input.focus();
      } else if (deleteBtn) {
        var did = deleteBtn.getAttribute('data-delete');
        if (!confirm('删除这条反馈？')) return;
        fetch(API_BASE + '/feedbacks/' + did, {
          method: 'DELETE',
          headers: { 'X-Visitor-Id': visitorId }
        })
        .then(function(r) { return r.json(); })
        .then(function(j) {
          if (j.success) { showToast('已删除', true); loadComments(); }
          else { showToast('删除失败: ' + (j.detail || '权限不足'), false); }
        })
        .catch(function() { showToast('网络错误', false); });
      }
    });
  }

  loadReactions();
  loadComments();
})();
"""


_INTERACTION_JS = r"""
(function() {
  // === 进度条: scrollY / (scrollHeight - clientHeight) ===
  var bar = document.querySelector('.progress-bar');
  if (bar) {
    var update = function() {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var pct = max > 0 ? (window.scrollY / max) * 100 : 0;
      bar.style.width = pct + '%';
    };
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  }

  // === 键盘 ← → 翻页: 复用 sidebar 文档目录顺序 ===
  // sidebar 链接 href 形如 foo.html, 按 DOM 顺序拿到所有 doc 路径
  var sidebarLinks = Array.prototype.slice.call(
    document.querySelectorAll('.sidebar a[href$=".html"]')
  );
  if (sidebarLinks.length > 0) {
    var paths = sidebarLinks.map(function(a) {
      // href 是 foo.html, 拼成当前路径 foo.html
      return a.getAttribute('href');
    });
    document.addEventListener('keydown', function(e) {
      // 编辑器/输入框内不响应
      var tag = (e.target && e.target.tagName) || '';
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(tag)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      var currentPath = location.pathname.split('/').pop();
      var idx = paths.indexOf(currentPath);
      if (idx < 0) return;

      if (e.key === 'ArrowLeft' && idx > 0) {
        e.preventDefault();
        location.href = paths[idx - 1];
      } else if (e.key === 'ArrowRight' && idx < paths.length - 1) {
        e.preventDefault();
        location.href = paths[idx + 1];
      }
    });
  }

  // === 章节页脚: 已在 build 时渲染同 folder 文档列表, 无需 JS ===
})();
"""

# ── Markdown → HTML 转换（纯 Python 实现，无需 markdown 库）──────────

def _md_to_html(text: str) -> tuple[str, list[dict]]:
    """Markdown → HTML 转换器（基于 mistune 3.x, pygments 高亮代码块）

    流程:
      1) mistune 直接渲染 → 完整 GFM (表格/任务列表/删除线/脚注/自动链接...)
      2) 后处理 1: <h1-3> 补 id (slug + 去重), 抽 toc
      3) 后处理 2: <pre><code class="language-xxx"> → pygments 高亮
      4) 后处理 3: 头标签内嵌 <a class="anchor" href="#id">#</a> (toc / 复制链接用)

    返回: (html, toc) — toc 是 h1/h2/h3 列表 [{id, level, text}]
    """
    toc: list[dict] = []
    heading_id_count: dict[str, int] = {}

    # ── 1) mistune 渲染 ──────────────────────────────
    body = _md(text or "")

    # ── 2) 后处理 heading: 补 id + 抽 toc + 嵌 anchor ──
    def _replace_heading(m: re.Match) -> str:
        level = int(m.group(1))
        inner = m.group(2)
        plain = re.sub(r"<[^>]+>", "", inner).strip()
        if level <= 3 and plain:
            base = _slugify(plain) or f"heading-{len(toc) + 1}"
            cnt = heading_id_count.get(base, 0)
            heading_id_count[base] = cnt + 1
            hid = base if cnt == 0 else f"{base}-{cnt}"
            toc.append({"id": hid, "level": level, "text": plain})
            # anchor 在 heading 前面, hover 时显示 (#) 复制链接
            return f'<h{level} id="{hid}"><a class="anchor" href="#{hid}" data-anchor-id="{hid}" title="复制锚点链接">#</a>{inner}</h{level}>'
        return m.group(0)

    body = re.sub(r"<h([1-3])>(.+?)</h\1>", _replace_heading, body, flags=re.S)

    # ── 2.5) 后处理 img: 补 lazy, 独占图片转 figure/caption ─
    def _enhance_img(m: re.Match) -> str:
        attrs = m.group(1).strip()
        if attrs.endswith("/"):
            attrs = attrs[:-1].rstrip()
        if "loading=" not in attrs:
            attrs += ' loading="lazy"'
        if "decoding=" not in attrs:
            attrs += ' decoding="async"'
        return f"<img {attrs}>" if attrs else "<img>"

    body = re.sub(r"<img([^>]*)>", _enhance_img, body)

    def _replace_image_paragraph(m: re.Match) -> str:
        img_attrs = m.group(1)
        attrs = _attrs_to_dict(img_attrs)
        caption = attrs.get("alt", "").strip()
        caption_html = f'<figcaption>{html.escape(caption)}</figcaption>' if caption else ''
        return f'<figure class="media-figure"><img{img_attrs}>{caption_html}</figure>'

    body = re.sub(r'<p>\s*<img([^>]*)>\s*</p>', _replace_image_paragraph, body, flags=re.S)

    # ── 3) 后处理代码块: pygments 高亮 ────────────────
    def _replace_codeblock(m: re.Match) -> str:
        lang = (m.group(1) or "").strip()
        code = html.unescape(m.group(2))

        # R7 反馈: mermaid 块走 mermaid.js 渲染 (Pygments 没 mermaid lexer, 走默认会当 text)
        if lang.lower() == "mermaid":
            # mistune escape 了 mermaid 源码 (< > &), 用 unescape 还回来
            decoded = html.unescape(code)
            return (
                f'<div class="code-block mermaid-block diagram-block" data-lang="mermaid">'
                f'<div class="code-block-header"><span>mermaid</span><button type="button" class="code-copy-btn">复制</button></div>'
                f'<pre class="mermaid">{decoded}</pre>'
                f'</div>'
            )

        # 解开 mistune 的 HTML escape (它对 & < > 做转义, pygments 自己会再转)
        try:
            lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
        except ClassNotFound:
            lexer = get_lexer_by_name("text")
        # 保留 lang class 让 pygments 也用, 主题切换的 cssclass 复用 .highlight
        formatter = HtmlFormatter(nowrap=False, cssclass=f"highlight lang-{lang or 'text'}", linenos=False)
        highlighted = _pyg_highlight(code, lexer, formatter)
        lang_label = html.escape(lang or "text")
        return (
            f'<div class="code-block" data-lang="{lang_label}">'
            f'<div class="code-block-header"><span>{lang_label}</span><button type="button" class="code-copy-btn">复制</button></div>'
            f'{highlighted}'
            f'</div>'
        )

    # 先处理有 language 标注的 (mistune 输出 <pre><code class="language-xxx">)
    body = re.sub(
        r'<pre><code class="language-([^"]*)">(.+?)</code></pre>',
        _replace_codeblock,
        body,
        flags=re.S,
    )
    # 再处理无 language 的 (裸 ``` 围栏, mistune 输出 <pre><code>)
    # 这些走 guess_lexer 自动猜,猜不到降级 text
    def _replace_codeblock_nolang(m: re.Match) -> str:
        code = html.unescape(m.group(1))
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = get_lexer_by_name("text")
        formatter = HtmlFormatter(nowrap=False, cssclass="highlight lang-text", linenos=False)
        highlighted = _pyg_highlight(code, lexer, formatter)
        return (
            '<div class="code-block" data-lang="text">'
            '<div class="code-block-header"><span>text</span><button type="button" class="code-copy-btn">复制</button></div>'
            f'{highlighted}'
            '</div>'
        )
    body = re.sub(
        r'<pre><code>(.+?)</code></pre>',
        _replace_codeblock_nolang,
        body,
        flags=re.S,
    )

    # ── 4) 数学公式轻量美化: 先做占位级容器, 后续可接 KaTeX/MathJax ─────
    math_blocks: list[str] = []

    def _stash_math_block(m: re.Match) -> str:
        expr = m.group(1).strip()
        token = f"@@OPENDOCX_MATH_BLOCK_{len(math_blocks)}@@"
        math_blocks.append(
            f'<div class="math-block" role="math"><code>{html.escape(expr)}</code></div>'
        )
        return token

    body = re.sub(r'\$\$([\s\S]+?)\$\$', _stash_math_block, body)

    def _replace_inline_math(m: re.Match) -> str:
        expr = m.group(1).strip()
        return f'<span class="math-inline" role="math"><code>{html.escape(expr)}</code></span>'

    body = re.sub(r'(?<!\$)\$([^$\n]+?)\$(?!\$)', _replace_inline_math, body)
    for i, block in enumerate(math_blocks):
        body = body.replace(f"@@OPENDOCX_MATH_BLOCK_{i}@@", block)
    body = re.sub(r'<p>\s*(<div class="math-block"[\s\S]*?</div>)\s*</p>', r'\1', body)

    # ── 5) 表格响应式包裹: 窄屏横向滚动, 不挤压正文 ─────────
    body = re.sub(r'(<table>.*?</table>)', r'<div class="table-wrap">\1</div>', body, flags=re.S)

    # ── 6) 任务列表包裹: checkbox / 完成态 / 间距统一 ─────────
    body = re.sub(
        r'(<ul>\s*(?:<li class="task-list-item">[\s\S]*?</li>\s*)+</ul>)',
        r'<div class="task-list-wrap">\1</div>',
        body,
    )

    # ── 7) Admonition 提示块 (GitHub / Obsidian 通用语法) ────
    # 语法: > [!NOTE] / > [!TIP] / > [!IMPORTANT] / > [!WARNING] / > [!CAUTION] / > [!INFO] / > [!DANGER]
    # mistune 渲染后第一个段落是 <p>[!NOTE] 标题...</p>, 紧跟 <p>正文</p>...
    # 整段包在 <blockquote>...</blockquote>
    #
    # R8 修复 (regression): 原 regex '<blockquote>([\s\S]*?\[!...]...)</blockquote>'
    # 在前有 raw blockquote 时, group1 跨越</blockquote> 起点, _replace 拒绝替换
    # 修法: 起点必须 <blockquote>\s*<p>[!TYPE], 杜绝跨 blockquote 误匹配
    def _replace_admonition(m: re.Match) -> str:
        # group 1 = 整个 blockquote 内部 (从 <p> 开始)
        # group 2 = TYPE 字符串
        inner = m.group(1)
        kind = m.group(2).lower()
        if kind not in ('note', 'tip', 'important', 'warning', 'caution', 'info', 'danger'):
            return m.group(0)
        # 提 [!TYPE] 后的标题文字
        title_m = re.match(r'<p>\[!\w+\]\s*([\s\S]*?)</p>', inner)
        title_payload = title_m.group(1).strip() if title_m else ''
        title_text = title_payload
        # body = 去掉首个 <p>[!TYPE]...</p> 段
        body_inner = re.sub(r'<p>\[!\w+\][\s\S]*?</p>', '', inner, count=1).strip()
        if "\n" in title_payload:
            title_text, first_body = title_payload.split("\n", 1)
            first_body = first_body.strip()
            if first_body:
                body_inner = f"<p>{first_body}</p>{body_inner}"
        title_text = title_text.strip()
        # 图标用纯 SVG (零 emoji 红线)
        icon_svgs = {
            'note':    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
            'tip':     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.5.4 1 1 1 2v.3h6v-.3c0-1 .5-1.6 1-2A7 7 0 0 0 12 2z"/></svg>',
            'info':    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/><line x1="12" y1="12" x2="12" y2="12.01"/></svg>',
            'important': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l2.6 6.7L22 9.2l-5.7 4.5 1.8 7.1L12 17l-6.1 3.8 1.8-7.1L2 9.2l7.4-.5L12 2z"/></svg>',
            'warning': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            'caution': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>',
            'danger':  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        }
        kind_label = {'note': '注', 'tip': '提示', 'important': '重要', 'warning': '警告', 'caution': '注意', 'info': '信息', 'danger': '危险'}.get(kind, kind.upper())
        title_html = f'<div class="admonition-title">{icon_svgs[kind]}<span class="admonition-label">{kind_label}</span>'
        if title_text:
            title_html += f'<span class="admonition-text">{title_text}</span>'
        title_html += '</div>'
        return f'<div class="admonition admonition-{kind}">{title_html}{body_inner}</div>'

    # 起点必须 <blockquote>\s*<p>[!TYPE], 杜绝跨 blockquote 误匹配
    # group 1 = inner 内容 (从 <p> 开始), group 2 = TYPE 字符串
    body = re.sub(
        r'<blockquote>\s*(<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|INFO|DANGER)\][\s\S]*?)</blockquote>',
        _replace_admonition,
        body,
        flags=re.I,
    )

    # ── 8) Syntax hint (R10): > MD语法: `code` → <p class="syntax-hint">───
    # 给 demo 文档用, 在示例后标注 MD 语法/使用方法
    # 关键: 不写 [MD语法]: (会被 mistune 当 link reference definition)
    # 用纯文本 MD语法: 开头, 后处理识别
    body = re.sub(
        r'<blockquote>\s*<p>MD语法[：:]\s*([\s\S]*?)</p>\s*</blockquote>',
        lambda m: f'<p class="syntax-hint">MD 语法:{m.group(1)}</p>',
        body,
    )

    return body, toc


def _slugify(text: str) -> str:
    """标题文本 → URL slug (小写, 空格/标点转 -)

    保留中文, 英文/数字/中文连字符.
    例: "API Quick Start" -> "api-quick-start"
         "第一章 概览" -> "第一章-概览"
    """
    import re
    # 小写
    s = text.lower()
    # 替换非字母/数字/中文/连字符 为 -
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^\w\u4e00-\u9fff\-]", "", s)
    # 压缩连续 -
    s = re.sub(r"-+", "-", s)
    # 去头尾 -
    return s.strip("-")



# ── HTML 模板 ─────────────────────────────────────────────
def _render_toc(toc: list[dict]) -> str:
    """TOC 渲染: 嵌套 <ul> 反映 heading 层级 (h1/h2/h3)

    设计: 右侧悬浮 sidebar, sticky, 跟随滚动, scroll 同步 active
    移动端 (<= 1024px) 隐藏, 改为底部抽屉按钮 (在 JS 控制)
    """
    if not toc:
        return '<aside class="toc" data-empty="true"><div class="toc-title">本页无目录</div></aside>'
    items: list[str] = []
    for entry in toc:
        indent = (entry["level"] - 1) * 16
        text = html.escape(entry["text"])
        items.append(
            f'<li style="padding-left:{indent}px">'
            f'<a href="#{entry["id"]}" data-toc-id="{entry["id"]}">{text}</a>'
            f'</li>'
        )
    return (
        '<aside class="toc">'
        '<div class="toc-title">本页目录</div>'
        f'<ul class="toc-list">{"".join(items)}</ul>'
        '</aside>'
    )


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>{title} - {project_name}</title>
<style>
/* === Design tokens: 6 段 Infima 骨架, 见 static/css/tokens.css === */
</style>
<link rel="stylesheet" href="static/css/tokens.css">
<style>
/* === P1-W3-L3-C8: 项目级 _config.yml 覆盖 — 必须在 tokens.css 之后, 优先级更高 === */
:root { --brand: __BRAND_COLOR__; }
__TAGLINE_BLOCK__
*{ margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--font-sans);
  font-size: var(--font-size-base);
  color: var(--fg); background: var(--bg); line-height: var(--line-height-base);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
/* === 代码字体: 等宽, 中英文回退 === */
pre, code, kbd, samp {
  font-family: var(--font-mono);
  font-size: 0.9em;
}
/* === 数字表格对齐 === */
table {
  font-variant-numeric: tabular-nums;
}
a { color: var(--brand); }
/* === Topbar (含主题切换按钮 + 进度条) === */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; height: var(--topbar-h);
  background: var(--bg-topbar); backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 var(--space-2xl); z-index: 100;
  gap: var(--space-md);
}
.topbar-brand { font-size: var(--font-size-lg); font-weight: 600; color: var(--fg); text-decoration: none; }
.topbar-version { font-size: var(--font-size-xs); color: var(--fg-subtle); margin-left: var(--space-sm); padding: 2px var(--space-sm); background: var(--bg-soft); border-radius: var(--radius-sm); }
.topbar-spacer { flex: 1; }
.theme-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent; border: 1px solid var(--border);
  color: var(--fg-muted); padding: 6px var(--space-md); border-radius: var(--radius-md);
  font-size: var(--font-size-xs); cursor: pointer; user-select: none;
  font-family: inherit; transition: all 0.15s;
}
.theme-toggle:hover { background: var(--border-soft); color: var(--fg); }
.theme-toggle svg { width: 14px; height: 14px; }
/* === 阅读进度条 (顶部 2px) === */
.progress-bar {
  position: fixed; top: var(--topbar-h); left: 0; right: 0;
  height: 2px; z-index: 99;
  background: var(--progress-bg);
  pointer-events: none;
}
.progress-bar-fill {
  height: 100%; width: 0%;
  background: var(--progress-fg);
  transition: width 0.05s linear;
  will-change: width;
}
/* === Layout (3 栏: sidebar / content / toc) === */
.layout {
  display: flex; padding-top: var(--topbar-h);
  min-height: 100vh;
}
.sidebar {
  position: fixed; top: var(--topbar-h); left: 0; bottom: 0;
  width: var(--sidebar-w); background: var(--bg-soft);
  border-right: 1px solid var(--border);
  overflow-y: auto; padding: var(--space-xl) 0;
}
.sidebar-title { font-size: var(--font-size-2xs); font-weight: var(--font-weight-semibold); color: var(--fg-subtle); text-transform: uppercase; letter-spacing: 0.5px; padding: 0 20px var(--space-md); }
.sidebar a { display: block; padding: var(--space-sm) 20px; color: var(--fg); text-decoration: none; font-size: var(--font-size-sm); border-left: 3px solid transparent; transition: all 0.15s; }
.sidebar a:hover { background: var(--border-soft); }
.sidebar a.active { color: var(--brand); border-left-color: var(--brand); background: var(--brand-soft); font-weight: 500; }
/* folder tree */
.sidebar details.nav-folder { margin: 2px 0; }
.sidebar details.nav-folder > summary {
  padding: var(--space-sm) 20px; font-size: var(--font-size-md); font-weight: var(--font-weight-semibold); color: var(--fg);
  cursor: pointer; user-select: none; list-style: none;
  display: flex; align-items: center; gap: var(--space-xs);
  border-left: 3px solid transparent; transition: all 0.15s;
}
.sidebar details.nav-folder > summary::-webkit-details-marker { display: none; }
.sidebar details.nav-folder > summary::before { content: '▸'; font-size: 10px; color: var(--fg-subtle); margin-right: var(--space-xs); transition: transform 0.15s; display: inline-block; width: 10px; }
.sidebar details.nav-folder[open] > summary::before { transform: rotate(90deg); }
.sidebar details.nav-folder > summary:hover { background: var(--border-soft); }
.sidebar details.nav-folder[data-depth="0"] > summary { font-size: var(--font-size-sm); padding: 10px 20px; border-top: 1px solid var(--border-soft); margin-top: var(--space-xs); }
.sidebar details.nav-folder[data-depth="1"] { padding-left: var(--space-lg); }
.sidebar details.nav-folder[data-depth="2"] { padding-left: var(--space-2xl); }
/* draft status */
.sidebar a.nav-draft { color: var(--fg-subtle) !important; cursor: not-allowed; display: flex; align-items: center; justify-content: space-between; }
.sidebar a.nav-draft:hover { background: var(--bg-soft); border-left-color: transparent !important; }
.sidebar a.nav-draft .nav-draft-tag { font-size: 10px; padding: 1px 6px; border-radius: var(--radius-sm); background: var(--bg-draft-tag); color: var(--fg-draft-tag); border: 1px solid var(--border-draft-tag); margin-left: var(--space-sm); }
/* === Content (中栏, 居中) === */
.content {
  margin-left: var(--sidebar-w);
  flex: 1;
  padding: var(--content-pad);
  max-width: calc(var(--content-max) + 2 * 64px);
  min-width: 0;
}
.content-inner { max-width: var(--content-max); margin: 0 auto; }
/* R9: 大屏(≥1600px)正文加宽到 1000px, 利用大屏空间 */
@media (min-width: 1600px) {
  .content-inner { max-width: var(--content-max-wide); }
}
/* === Typography rhythm (Docusaurus 精髓: H2 上方分割线 + 章节感) === */
.content p { margin-bottom: var(--space-lg); color: var(--fg); line-height: var(--line-height-base); }
.content h1 { font-size: var(--font-size-3xl); font-weight: var(--font-weight-bold); letter-spacing: -0.5px; margin-bottom: var(--space-lg); color: var(--fg); line-height: var(--line-height-heading); }
.content h2 { font-size: var(--font-size-2xl); font-weight: var(--font-weight-semibold); margin: var(--space-3xl) 0 var(--space-md); color: var(--fg); line-height: var(--line-height-heading); scroll-margin-top: calc(var(--topbar-h) + var(--space-xl)); }
.content h3 { font-size: var(--font-size-xl); font-weight: var(--font-weight-semibold); margin: var(--space-xl) 0 var(--space-sm); color: var(--fg); line-height: var(--line-height-heading); scroll-margin-top: calc(var(--topbar-h) + var(--space-xl)); }
/* R10: H4-H6 跟正文同字号, 视觉上不再分层, 改用字重/斜体区分 */
/* 原因: H4(17px)几乎跟正文(16px)平, H5/H6 默认 16/14 完全混乱 */
.content h4 { font-size: var(--font-size-base); font-weight: var(--font-weight-bold); margin: var(--space-lg) 0 var(--space-sm); color: var(--fg); }
.content h5 { font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); margin: var(--space-md) 0 var(--space-xs); color: var(--fg); }
.content h6 { font-size: var(--font-size-base); font-weight: var(--font-weight-normal); font-style: italic; margin: var(--space-md) 0 var(--space-xs); color: var(--fg-muted); }
.content ul, .content ol { margin: 0 0 var(--space-lg) 24px; color: var(--fg); }
.content li { margin-bottom: 6px; }
.content h1[id], .content h2[id], .content h3[id] { position: relative; }
.content h1 .anchor, .content h2 .anchor, .content h3 .anchor {
  position: absolute; left: -24px; top: 50%; transform: translateY(-50%);
  color: var(--fg-subtle); opacity: 0;
  text-decoration: none; font-weight: 400;
  font-size: 0.85em; padding: 0 6px;
  transition: opacity 0.15s;
  cursor: pointer;
}
.content h1:hover .anchor, .content h2:hover .anchor, .content h3:hover .anchor { opacity: 1; }
.content h1 .anchor:hover, .content h2 .anchor:hover, .content h3 .anchor:hover { color: var(--brand); }
/* === Pygments 高亮代码块 (双主题切换) === */
.content pre { background: var(--bg-code); color: var(--bg-code-fg); padding: var(--space-lg) var(--space-xl); border-radius: var(--radius-md); overflow-x: auto; margin-bottom: var(--space-lg); font-size: var(--font-size-sm); line-height: 1.55; }
.content .code-block {
  margin: var(--space-xl) 0;
  overflow: hidden;
  background: var(--bg-code);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.content .code-block-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-md);
  min-height: 38px;
  padding: 0 var(--space-md) 0 var(--space-lg);
  background: var(--bg-code-header);
  border-bottom: 1px solid var(--border);
  color: var(--fg-muted);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
}
.content .code-block-header span {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-soft);
  color: var(--fg-muted);
}
.content .code-copy-btn {
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--fg-muted);
  font-size: var(--font-size-xs);
  font-family: inherit;
  cursor: pointer;
}
.content .code-copy-btn:hover { color: var(--brand); border-color: var(--brand); background: var(--brand-soft); }
.content .highlight { background: var(--bg-code); color: var(--bg-code-fg); margin: 0; overflow-x: auto; }
.content .highlight, .content .highlight pre { -webkit-overflow-scrolling: touch; overscroll-behavior-x: contain; }
.content .highlight pre { background: transparent; margin: 0; padding: var(--space-lg) var(--space-xl); border-radius: 0; }
.content code { font-family: var(--font-mono); font-size: 0.9em; }
.content p code { background: var(--bg-inline-code); padding: 2px 6px; border-radius: var(--radius-sm); color: var(--bg-inline-code-fg); }
.content a { color: var(--brand); text-decoration: none; }
.content a:hover { text-decoration: underline; }
.content blockquote { border-left: 3px solid var(--bg-blockquote-border); padding: var(--space-md) var(--space-lg); margin: var(--space-xl) 0; color: var(--fg-muted); background: var(--bg-blockquote); border-radius: 0 var(--radius-md) var(--radius-md) 0; }
.content blockquote p:last-child { margin-bottom: 0; }
/* === Admonition 提示块 (GitHub / Obsidian 风格) === */
.content .admonition {
  position: relative;
  border: 1px solid;
  border-left-width: 4px;
  padding: var(--space-md) var(--space-lg);
  margin: var(--space-xl) 0;
  border-radius: var(--radius-md);
  background: var(--bg-admonition-default);
  box-shadow: var(--shadow-sm);
}
.content .admonition p:last-child { margin-bottom: 0; }
.content .admonition-title { display: flex; align-items: center; gap: 8px; font-weight: 600; margin-bottom: var(--space-sm); font-size: 0.95em; }
.content .admonition-title svg { width: 16px; height: 16px; flex-shrink: 0; }
.content .admonition-label { font-weight: 700; letter-spacing: 0.02em; white-space: nowrap; }
.content .admonition-text { font-weight: 500; color: var(--fg); }
.content .admonition p { margin-bottom: var(--space-sm); color: var(--fg); }
.content .admonition-note    { background: #f6f8fa; border-color: #d8dee4; border-left-color: #6b7785; color: #24292f; }
.content .admonition-note    .admonition-label { color: #57606a; }
.content .admonition-tip     { background: #f0fdf4; border-color: #bbf7d0; border-left-color: #1a7f37; color: #1a3a1f; }
.content .admonition-tip     .admonition-label { color: #1a7f37; }
.content .admonition-info    { background: #eff6ff; border-color: #bfdbfe; border-left-color: #0969da; color: #0c2d6b; }
.content .admonition-info    .admonition-label { color: #0969da; }
.content .admonition-important { background: #faf5ff; border-color: #e9d5ff; border-left-color: #7c3aed; color: #3b0764; }
.content .admonition-important .admonition-label { color: #7c3aed; }
.content .admonition-warning { background: #fff8e1; border-color: #fde68a; border-left-color: #9a6700; color: #4d3800; }
.content .admonition-warning .admonition-label { color: #9a6700; }
.content .admonition-caution { background: #fff7ed; border-color: #fed7aa; border-left-color: #ea580c; color: #431407; }
.content .admonition-caution .admonition-label { color: #ea580c; }
.content .admonition-danger  { background: #ffebe9; border-color: #fecaca; border-left-color: #d1242f; color: #5a0e12; }
.content .admonition-danger  .admonition-label { color: #d1242f; }
:root[data-theme="dark"] .admonition-note    { background: #161b22; border-color: #30363d; border-left-color: #6b7785; color: #c9d1d9; }
:root[data-theme="dark"] .admonition-note    .admonition-label { color: #8b949e; }
:root[data-theme="dark"] .admonition-tip     { background: #0f2419; border-color: #1f5130; border-left-color: #3fb950; color: #b6e3c1; }
:root[data-theme="dark"] .admonition-tip     .admonition-label { color: #3fb950; }
:root[data-theme="dark"] .admonition-info    { background: #0b1f3a; border-color: #1d4d8f; border-left-color: #58a6ff; color: #cae8ff; }
:root[data-theme="dark"] .admonition-info    .admonition-label { color: #58a6ff; }
:root[data-theme="dark"] .admonition-important { background: #221432; border-color: #5b2c82; border-left-color: #a78bfa; color: #e9d5ff; }
:root[data-theme="dark"] .admonition-important .admonition-label { color: #c4b5fd; }
:root[data-theme="dark"] .admonition-warning { background: #341a00; border-color: #633c01; border-left-color: #d29922; color: #f0d5a0; }
:root[data-theme="dark"] .admonition-warning .admonition-label { color: #d29922; }
:root[data-theme="dark"] .admonition-caution { background: #321500; border-color: #7c2d12; border-left-color: #fb923c; color: #fed7aa; }
:root[data-theme="dark"] .admonition-caution .admonition-label { color: #fdba74; }
:root[data-theme="dark"] .admonition-danger  { background: #2d0a0e; border-color: #7f1d1d; border-left-color: #f85149; color: #ffc1c1; }
:root[data-theme="dark"] .admonition-danger  .admonition-label { color: #f85149; }
:root[data-theme="dark"] .admonition .admonition-text { color: #e6edf3; }
:root[data-theme="dark"] .admonition p { color: #e6edf3; }
/* R10: syntax-hint - 灰小字右对齐, 用来在示例后标注 MD 语法/使用方法 */
.content .syntax-hint {
  display: block;
  margin: calc(var(--space-md) * -1 + var(--space-xs)) 0 var(--space-lg);
  padding: 0;
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  color: var(--fg-subtle);
  text-align: right;
  font-style: normal;
}
.content .syntax-hint code { font-size: var(--font-size-xs); background: var(--bg-soft); padding: 1px 6px; border-radius: var(--radius-sm); }
:root[data-theme="dark"] .content .syntax-hint { color: #6e7681; }
.content hr { border: none; height: 1px; background: linear-gradient(90deg, transparent, var(--border), transparent); margin: var(--space-2xl) 0; }
.content .table-wrap {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
  margin: var(--space-xl) 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.content table { border-collapse: separate; border-spacing: 0; width: 100%; min-width: 560px; font-variant-numeric: tabular-nums; }
.content th, .content td { padding: 13px var(--space-md); border: none; border-bottom: 1px solid var(--border); text-align: left; color: var(--fg-muted); vertical-align: top; }
.content th { background: var(--bg-soft); font-weight: 600; color: var(--fg); white-space: nowrap; }
.content tbody tr:last-child td { border-bottom: none; }
.content tbody tr:hover td { background: var(--border-soft); color: var(--fg); }
.content .task-list-wrap {
  margin: var(--space-xl) 0;
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}
.content .task-list-wrap ul { margin: 0; padding: 0; list-style: none; }
.content li.task-list-item { display: flex; align-items: flex-start; gap: 10px; margin: 0; padding: 8px 0; color: var(--fg); }
.content li.task-list-item input[type="checkbox"] { width: 17px; height: 17px; margin: 2px 0 0; accent-color: var(--brand); flex-shrink: 0; }
.content li.task-list-item:has(input[checked]) { color: var(--fg-muted); }
.content li.task-list-item:has(input[checked]) { text-decoration: line-through; text-decoration-color: var(--fg-subtle); }
.content .media-figure {
  margin: var(--space-2xl) auto;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-soft);
  box-shadow: var(--shadow-sm);
}
.content .media-figure img { margin: 0; border-radius: 0; width: 100%; }
.content .media-figure figcaption {
  padding: 10px var(--space-md);
  border-top: 1px solid var(--border);
  color: var(--fg-muted);
  font-size: var(--font-size-sm);
  text-align: center;
}
.content img, .content video { display: block; max-width: 100%; height: auto; border-radius: var(--radius-md); margin: var(--space-xl) auto; }
.content iframe { display: block; max-width: 100%; margin: var(--space-xl) auto; border: 1px solid var(--border); border-radius: var(--radius-md); }
.content .diagram-block, .content .math-block {
  margin: var(--space-xl) 0;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-soft);
  box-shadow: var(--shadow-sm);
}
.content .math-inline {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  background: var(--bg-inline-code);
  color: var(--fg);
  font-family: Georgia, "Times New Roman", serif;
  font-style: italic;
}
.content .math-inline code { background: transparent; color: inherit; padding: 0; font-family: inherit; }
.content .math-block { padding: var(--space-lg); text-align: center; font-family: Georgia, "Times New Roman", serif; font-style: italic; }
.content .math-block code { background: transparent; color: var(--fg); padding: 0; font-family: inherit; font-size: 1.08em; white-space: pre-wrap; }
.search-box { width: calc(100% - 40px); padding: 10px var(--space-lg); margin: 0 20px var(--space-lg); border: 1px solid var(--border); border-radius: var(--radius-md); font-size: var(--font-size-sm); outline: none; background: var(--bg); color: var(--fg); font-family: inherit; }
.search-box:focus { border-color: var(--brand); box-shadow: 0 0 0 3px var(--brand-soft); }
.nav-links { padding: var(--space-lg) 0; display: flex; justify-content: space-between; border-top: 1px solid var(--border); margin-top: var(--space-3xl); }
.nav-links a { color: var(--brand); text-decoration: none; font-size: var(--font-size-sm); font-weight: 500; }
.nav-links a:hover { text-decoration: underline; }
.footer { text-align: center; padding: var(--space-2xl); color: var(--fg-subtle); font-size: var(--font-size-xs); border-top: 1px solid var(--border); margin-top: var(--space-3xl); }
/* === TOC (右栏) === */
.toc {
  position: fixed; top: calc(var(--topbar-h) + var(--space-2xl)); right: var(--space-2xl);
  width: var(--toc-w);
  max-height: calc(100vh - var(--topbar-h) - 64px);
  overflow-y: auto;
  font-size: var(--font-size-md); line-height: 1.5;
}
.toc-title {
  font-size: var(--font-size-2xs); font-weight: var(--font-weight-semibold); color: var(--fg-subtle);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: var(--space-md);
}
.toc-list { list-style: none; }
.toc-list li { margin-bottom: var(--space-xs); }
.toc-list a {
  display: block; padding: var(--space-xs) var(--space-sm); border-left: 2px solid transparent;
  color: var(--fg-muted); text-decoration: none;
  font-size: var(--font-size-md); transition: all 0.15s;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.toc-list a:hover { color: var(--fg); background: var(--border-soft); }
.toc-list a.active {
  color: var(--brand); border-left-color: var(--brand);
  background: var(--brand-soft); font-weight: 500;
}
/* === 移动端 TOC 抽屉 (默认隐藏, 通过 .toc-drawer-open class 显示) === */
.toc-drawer-toggle {
  display: none; position: fixed; bottom: 24px; right: 24px;
  width: 48px; height: 48px; border-radius: 50%;
  background: var(--brand); color: white;
  border: none; cursor: pointer; z-index: 98;
  box-shadow: var(--shadow);
  font-size: 20px; align-items: center; justify-content: center;
}
.toc-drawer {
  display: none; position: fixed; bottom: 0; left: 0; right: 0;
  max-height: 60vh; overflow-y: auto;
  background: var(--bg); border-top: 1px solid var(--border);
  z-index: 99; padding: 20px 24px 32px;
  transform: translateY(100%);
  transition: transform 0.25s ease-out;
  box-shadow: var(--shadow-md);
}
.toc-drawer.open { transform: translateY(0); }
/* === 响应式: <= 1024px 隐藏右栏 TOC, 显示底部抽屉按钮 === */
@media (max-width: 1024px) {
  .toc { display: none; }
  .toc-drawer-toggle { display: flex; }
}
/* === 响应式: <= 768px 移动端 === */
@media (max-width: 768px) {
  :root { --content-pad: 24px 20px; --sidebar-w: 0px; }
  .topbar { padding: 0 16px; height: 48px; }
  :root[data-theme="light"], :root[data-theme="dark"] { --topbar-h: 48px; }
  .topbar-brand { font-size: 16px; }
  .topbar-version { display: none; }
  .theme-toggle span { display: none; }
  .theme-toggle { padding: 6px 8px; }
  .progress-bar { top: var(--topbar-h); }
  .sidebar {
    transform: translateX(-100%); transition: transform 0.2s;
    width: 260px; box-shadow: var(--shadow);
    z-index: 97;
  }
  .sidebar.open { transform: translateX(0); }
  .content { margin-left: 0; padding: 24px 20px; max-width: 100%; }
  .content h1 { font-size: 28px; }
  .content h2 { font-size: 20px; }
  .content h3 { font-size: 17px; }
  .content h1 .anchor, .content h2 .anchor, .content h3 .anchor {
    position: static; opacity: 0.5; margin-left: 6px; transform: none; display: inline-block;
  }
  .toc-drawer-toggle { display: flex; }
}
/* 移动端 sidebar 切换按钮 (汉堡) */
.sidebar-toggle {
  display: none; position: fixed; top: 8px; left: 8px; z-index: 101;
  background: transparent; border: none; color: var(--fg);
  width: 40px; height: 40px; padding: 8px; border-radius: 6px; cursor: pointer;
}
@media (max-width: 768px) {
  .sidebar-toggle { display: flex; align-items: center; justify-content: center; }
}
.sidebar-toggle svg { width: 20px; height: 20px; }
.sidebar-backdrop {
  display: none; position: fixed; inset: 0; background: var(--overlay);
  z-index: 96;
}
@media (max-width: 768px) {
  .sidebar-backdrop.open { display: block; }
}
/* === Pygments 浅色主题 (github-light) === */
{pyg_light_css}
/* === Pygments 深色主题 (github-dark) - 仅 data-theme=dark 时显示 === */
:root[data-theme="dark"] .highlight {
  background: #0d1117 !important;
  color: #c9d1d9;
}
:root[data-theme="dark"] .highlight pre {
  background: transparent;
}
{pyg_dark_css}
/* === 锚点复制提示 toast === */
.anchor-toast {
  position: fixed; top: 80px; left: 50%; transform: translateX(-50%);
  background: var(--fg); color: var(--bg);
  padding: 8px 16px; border-radius: var(--radius-md);
  font-size: var(--font-size-sm); font-weight: 500;
  z-index: 1000; opacity: 0; pointer-events: none;
  transition: opacity 0.2s, transform 0.2s;
  box-shadow: var(--shadow-lg);
}
.anchor-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
/* === 反馈区（点赞/点踩/收藏） === */
.feedback-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-xl) 0;
  margin-top: var(--space-2xl);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap; gap: var(--space-md);
}
.feedback-bar-left { display: flex; align-items: center; gap: var(--space-md); flex-wrap: wrap; }
.feedback-label { font-size: var(--font-size-sm); color: var(--fg-muted); }
.fb-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px var(--space-md);
  background: var(--bg-soft); border: 1px solid var(--border);
  color: var(--fg-muted);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm); font-family: inherit;
  cursor: pointer; user-select: none;
  transition: all 0.15s;
}
.fb-btn:hover { background: var(--border-soft); color: var(--fg); }
.fb-btn.active { background: var(--brand-soft); border-color: var(--brand); color: var(--brand); font-weight: 500; }
.fb-btn svg { width: 14px; height: 14px; }
/* === 评论区 === */
.comments-section {
  margin-top: var(--space-2xl);
  padding-top: var(--space-xl);
}
.comments-section h3 {
  font-size: var(--font-size-xl); font-weight: 600;
  margin-bottom: var(--space-lg);
  color: var(--fg);
}
.comment-form {
  display: flex; gap: var(--space-md);
  margin-bottom: var(--space-xl);
}
.comment-form input {
  flex: 1; padding: var(--space-md) var(--space-lg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg); color: var(--fg);
  font-family: inherit; font-size: var(--font-size-sm);
  outline: none;
}
.comment-form input:focus { border-color: var(--brand); box-shadow: 0 0 0 3px var(--brand-soft); }
.comment-form button {
  padding: var(--space-md) var(--space-xl);
  background: var(--brand); color: white;
  border: none; border-radius: var(--radius-md);
  font-size: var(--font-size-sm); font-weight: 500;
  cursor: pointer; font-family: inherit;
  transition: opacity 0.15s;
}
.comment-form button:hover { opacity: 0.85; }
.comment-list { display: flex; flex-direction: column; gap: var(--space-lg); }
.comment-item {
  padding: var(--space-lg);
  background: var(--bg-soft);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-soft);
}
.comment-meta {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-sm);
  font-size: var(--font-size-xs); color: var(--fg-subtle);
}
.comment-meta strong { color: var(--fg); font-weight: 600; }
.comment-body { color: var(--fg-muted); line-height: var(--line-height-base); white-space: pre-wrap; word-break: break-word; }
.comment-actions {
  display: flex; gap: var(--space-md);
  margin-top: var(--space-sm);
  font-size: var(--font-size-xs);
}
.comment-actions button {
  background: transparent; border: none;
  color: var(--fg-subtle); cursor: pointer;
  font-family: inherit; font-size: inherit;
  padding: 0;
  transition: color 0.15s;
}
.comment-actions button:hover { color: var(--brand); }
.comment-empty { text-align: center; color: var(--fg-subtle); padding: var(--space-2xl); font-size: var(--font-size-sm); }
.comment-replies {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px dashed var(--border);
  display: flex; flex-direction: column; gap: var(--space-sm);
}
/* F3 嵌套回复缩进: 1 级缩进 20px + 左边虚线, 2 级缩进 40px */
.comment-replies[data-parent-depth="0"] { margin-left: 0; }
.comment-replies[data-parent-depth="1"] { margin-left: 20px; padding-left: 12px; border-left: 2px solid var(--border-subtle, var(--border)); border-top: none; }
.comment-item[data-depth="1"] { background: var(--bg); }
.comment-reply-form {
  display: flex; gap: var(--space-sm);
  margin-top: var(--space-sm);
}
.comment-reply-form input {
  flex: 1; padding: 6px var(--space-md);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg); color: var(--fg);
  font-family: inherit; font-size: var(--font-size-xs);
  outline: none;
}
.comment-reply-form input:focus { border-color: var(--brand); }
.comment-reply-form button {
  padding: 6px var(--space-md);
  background: var(--brand); color: white;
  border: none; border-radius: var(--radius-md);
  font-size: var(--font-size-xs); font-weight: 500;
  cursor: pointer; font-family: inherit;
}
/* === 反馈 toast === */
.fb-toast {
  position: fixed; top: 80px; left: 50%; transform: translateX(-50%);
  background: var(--fg); color: var(--bg);
  padding: 8px var(--space-lg); border-radius: var(--radius-md);
  font-size: var(--font-size-sm); font-weight: 500;
  z-index: 1000; opacity: 0; pointer-events: none;
  transition: opacity 0.2s, transform 0.2s;
}
.fb-toast.show { opacity: 1; }

/* === Phase 4: Hero 首页 + Folder 网格 + 最近更新 === */
.home-hero {
  text-align: center;
  padding: var(--space-4xl) var(--space-2xl) var(--space-3xl);
  border-bottom: 1px solid var(--border-soft);
  margin-bottom: var(--space-3xl);
}
.home-hero h1 {
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -1px;
  margin: 0 0 var(--space-md);
  background: linear-gradient(135deg, var(--brand) 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.home-hero .home-desc {
  font-size: var(--font-size-lg);
  color: var(--fg-muted);
  max-width: 600px;
  margin: 0 auto var(--space-xl);
  line-height: 1.6;
}
.home-hero .home-cta-row {
  display: flex;
  gap: var(--space-md);
  justify-content: center;
  flex-wrap: wrap;
}
/* === Phase 5 段 C: index_doc markdown 渲染区 (CTA 下方) === */
.home-hero-content {
  max-width: 640px;
  margin: var(--space-2xl) auto 0;
  padding: var(--space-xl);
  background: var(--bg-soft);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-soft);
  text-align: left;
  color: var(--fg);
}
.home-hero-content p { color: var(--fg); margin-bottom: var(--space-md); }
.home-hero-content h2 { font-size: var(--font-size-xl); margin: var(--space-lg) 0 var(--space-sm); border-top: 0; padding-top: 0; }
.home-hero-content ul { color: var(--fg); }
.home-cta {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 10px 24px;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-sm);
  font-weight: 500;
  text-decoration: none;
  transition: transform 0.15s, box-shadow 0.15s;
}
.home-cta.primary {
  background: var(--brand);
  color: #fff;
}
.home-cta.primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-brand);
}
.home-cta.secondary {
  background: var(--bg-soft);
  color: var(--fg);
  border: 1px solid var(--border);
}
.home-cta.secondary:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.home-section {
  margin-bottom: var(--space-4xl);
}
.home-section-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin: 0 0 var(--space-lg);
  color: var(--fg);
}
.home-section-title .home-section-count {
  font-size: var(--font-size-sm);
  color: var(--fg-subtle);
  font-weight: 400;
}

/* folder 网格: 4 列宽屏, 2 列中屏, 1 列窄屏 */
.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-lg);
}
.folder-card {
  display: block;
  padding: var(--space-xl);
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  text-decoration: none;
  color: var(--fg);
  transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
  position: relative;
  overflow: hidden;
}
.folder-card:hover {
  transform: translateY(-2px);
  border-color: var(--brand);
  box-shadow: var(--shadow-lg);
}
:root[data-theme="dark"] .folder-card:hover {
  box-shadow: var(--shadow-lg);
}
.folder-card-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--brand-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-md);
}
.folder-card-icon svg {
  width: 20px;
  height: 20px;
  color: var(--brand);
}
.folder-card-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  margin: 0 0 var(--space-xs);
  color: var(--fg);
}
.folder-card-meta {
  font-size: var(--font-size-xs);
  color: var(--fg-subtle);
}
.folder-card-arrow {
  position: absolute;
  top: var(--space-lg);
  right: var(--space-lg);
  color: var(--fg-subtle);
  transition: transform 0.15s, color 0.15s;
}
.folder-card:hover .folder-card-arrow {
  transform: translateX(2px);
  color: var(--brand);
}

/* 最近更新: 紧凑列表 */
.recent-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.recent-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--border-soft);
  text-decoration: none;
  color: var(--fg);
  transition: background 0.1s;
}
.recent-item:last-child { border-bottom: none; }
.recent-item:hover { background: var(--bg-soft); }
.recent-item-icon {
  width: 16px;
  height: 16px;
  color: var(--fg-subtle);
  flex-shrink: 0;
}
.recent-item-title {
  flex: 1;
  font-size: var(--font-size-sm);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-item-time {
  font-size: var(--font-size-xs);
  color: var(--fg-subtle);
  flex-shrink: 0;
}

/* folder 章节页: 跟普通 doc 一样三栏, body 是 doc 列表卡片 */
.folder-overview-list {
  list-style: none;
  padding: 0;
  margin: var(--space-lg) 0 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
.folder-overview-item {
  display: block;
  padding: var(--space-lg) var(--space-xl);
  background: var(--bg-soft);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  text-decoration: none;
  color: var(--fg);
  transition: border-color 0.15s, background 0.15s;
}
.folder-overview-item:hover {
  border-color: var(--brand);
  background: var(--bg);
}
.folder-overview-item-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--font-size-base);
  font-weight: 600;
  margin: 0 0 var(--space-xs);
}
.folder-overview-item-meta {
  display: flex;
  gap: var(--space-md);
  font-size: var(--font-size-xs);
  color: var(--fg-subtle);
}
.folder-overview-empty {
  text-align: center;
  padding: var(--space-4xl) var(--space-xl);
  color: var(--fg-subtle);
}

/* sidebar folder 链接化: 整行可点 (原 details/summary 只展开, 现跳 overview 页) */
.nav-folder-as-link > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--fg);
  transition: background 0.1s;
}
.nav-folder-as-link > summary::-webkit-details-marker { display: none; }
.nav-folder-as-link > summary:hover { background: var(--bg-soft); }
.nav-folder-as-link > summary .nav-folder-label {
  flex: 1;
  text-decoration: none;
  color: inherit;
}
.nav-folder-as-link > summary .nav-folder-chevron {
  width: 12px;
  height: 12px;
  color: var(--fg-subtle);
  transition: transform 0.15s;
}
.nav-folder-as-link[open] > summary .nav-folder-chevron {
  transform: rotate(90deg);
}

/* === Pygments 双主题 (light + dark) — 已在前面 line ~729 注入 === */
</style>
</head>
<body>
<div class="topbar">
  <button class="sidebar-toggle" id="sidebarToggle" aria-label="切换导航">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
  </button>
  <a class="topbar-brand" href="index.html">{project_name}</a>
  <span class="topbar-version">{version}</span>
  <div class="topbar-spacer"></div>
  <button class="theme-toggle" id="themeToggle" aria-label="切换主题">
    <svg id="themeIconLight" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="6.93" y2="6.93"/><line x1="17.07" y1="17.07" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="6.93" y2="17.07"/><line x1="17.07" y1="6.93" x2="19.07" y2="4.93"/></svg>
    <svg id="themeIconDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:none"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
    <span id="themeLabel">深色</span>
  </button>
</div>
<div class="progress-bar"><div class="progress-bar-fill" id="progressFill"></div></div>
<div class="sidebar-backdrop" id="sidebarBackdrop"></div>
<div class="layout">
  <div class="sidebar" id="sidebar">
    <div class="sidebar-title">文档目录</div>
    <input class="search-box" type="text" placeholder="搜索文档..." id="searchBox">
    <nav id="docNav">{sidebar_links}</nav>
  </div>
  <div class="content">
    <div class="content-inner">
      {body}
      {nav_links}
      <!-- 反馈区占位 (首页/章节页 build 时整段替换为空, 文档页保留) -->
      <!--FEEDBACK_SECTION_PLACEHOLDER-->
      <div class="footer">由 OpenDocX 生成 · {project_name} {version}</div>
    </div>
  </div>
  {toc_html}
  <button class="toc-drawer-toggle" id="tocDrawerToggle" aria-label="打开目录">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="4" cy="6" r="1" fill="currentColor"/><circle cx="4" cy="12" r="1" fill="currentColor"/><circle cx="4" cy="18" r="1" fill="currentColor"/></svg>
  </button>
  <aside class="toc-drawer" id="tocDrawer">
    <div class="toc-title">本页目录</div>
    <ul class="toc-list" id="tocDrawerList"></ul>
  </aside>
</div>
<div class="anchor-toast" id="anchorToast">已复制锚点链接</div>
<div class="fb-toast" id="fbToast"></div>
<script>
<!--FEEDBACK_JS_PLACEHOLDER-->
</script>
<script>
<!--INTERACTION_JS_PLACEHOLDER-->
</script>
<script>
(function() {
  /* === 主题切换 (light/dark/auto) === */
  var html = document.documentElement;
  var stored = localStorage.getItem('opendocx-theme');
  function applyTheme(t) {
    if (t === 'light' || t === 'dark') {
      html.setAttribute('data-theme', t);
    } else {
      html.removeAttribute('data-theme');
    }
    var isDark = t === 'dark' || (t !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.getElementById('themeIconLight').style.display = isDark ? 'none' : '';
    document.getElementById('themeIconDark').style.display = isDark ? '' : 'none';
    document.getElementById('themeLabel').textContent = isDark ? '浅色' : '深色';
  }
  applyTheme(stored || 'auto');
  document.getElementById('themeToggle').addEventListener('click', function() {
    var isDark = html.getAttribute('data-theme') === 'dark' || (!html.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var next = isDark ? 'light' : 'dark';
    localStorage.setItem('opendocx-theme', next);
    applyTheme(next);
  });
  /* 跟随系统变化 */
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
    if (!localStorage.getItem('opendocx-theme')) applyTheme('auto');
  });
  /* === 阅读进度条 === */
  var fill = document.getElementById('progressFill');
  function updateProgress() {
    var doc = document.documentElement;
    var h = doc.scrollHeight - doc.clientHeight;
    var pct = h > 0 ? (doc.scrollTop / h * 100) : 0;
    fill.style.width = Math.min(100, Math.max(0, pct)) + '%';
  }
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
  updateProgress();
  /* === TOC active 同步 (scroll spy) === */
  var tocLinks = document.querySelectorAll('.toc-list a[data-toc-id]');
  if (tocLinks.length) {
    var headings = [];
    tocLinks.forEach(function(a) { var h = document.getElementById(a.getAttribute('data-toc-id')); if (h) headings.push(h); });
    function updateTocActive() {
      var scrollY = window.scrollY + 100;
      var current = headings[0];
      for (var i = 0; i < headings.length; i++) {
        if (headings[i].offsetTop <= scrollY) current = headings[i];
        else break;
      }
      if (!current) return;
      var activeId = current.id;
      tocLinks.forEach(function(a) {
        if (a.getAttribute('data-toc-id') === activeId) a.classList.add('active');
        else a.classList.remove('active');
      });
    }
    window.addEventListener('scroll', updateTocActive, { passive: true });
    updateTocActive();
  }
  /* === 移动端 TOC 抽屉 === */
  var drawerToggle = document.getElementById('tocDrawerToggle');
  var drawer = document.getElementById('tocDrawer');
  var drawerList = document.getElementById('tocDrawerList');
  if (drawerToggle && drawer) {
    /* 复制主 TOC 内容到 drawer */
    var mainTocList = document.querySelector('.toc .toc-list');
    if (mainTocList && drawerList) {
      drawerList.innerHTML = mainTocList.innerHTML;
    }
    drawerToggle.addEventListener('click', function() {
      drawer.classList.toggle('open');
    });
    /* 点击 drawer 中链接后自动关闭 */
    drawerList.addEventListener('click', function(e) {
      if (e.target.tagName === 'A') {
        setTimeout(function() { drawer.classList.remove('open'); }, 200);
      }
    });
  }
  /* === 移动端 sidebar 切换 === */
  var sidebar = document.getElementById('sidebar');
  var sidebarToggle = document.getElementById('sidebarToggle');
  var backdrop = document.getElementById('sidebarBackdrop');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function() {
      sidebar.classList.toggle('open');
      if (backdrop) backdrop.classList.toggle('open');
    });
    if (backdrop) {
      backdrop.addEventListener('click', function() {
        sidebar.classList.remove('open');
        backdrop.classList.remove('open');
      });
    }
  }
  /* === 搜索框 (原逻辑) === */
  var sb = document.getElementById('searchBox');
  if (sb) sb.addEventListener('input', function(e) {
    var q = e.target.value.toLowerCase();
    document.querySelectorAll('#docNav a').forEach(function(a) {
      a.style.display = a.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
  /* === 键盘 ← / → 翻页 (上一篇/下一篇) === */
  document.addEventListener('keydown', function(e) {
    // 忽略输入框/textarea/contenteditable 中的按键
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
    var nav = document.querySelector('.nav-links');
    if (!nav) return;
    if (e.key === 'ArrowLeft') {
      var prev = nav.getAttribute('data-prev');
      if (prev) { e.preventDefault(); window.location.href = prev; }
    } else if (e.key === 'ArrowRight') {
      var next = nav.getAttribute('data-next');
      if (next) { e.preventDefault(); window.location.href = next; }
    }
  });
  /* === 代码块复制 === */
  document.addEventListener('click', function(e) {
    var btn = e.target.closest && e.target.closest('.code-copy-btn');
    if (!btn) return;
    var block = btn.closest('.code-block');
    var pre = block && block.querySelector('pre');
    if (!pre) return;
    var text = pre.innerText || pre.textContent || '';
    function done(ok) {
      var old = btn.textContent;
      btn.textContent = ok ? '已复制' : '复制失败';
      setTimeout(function() { btn.textContent = old || '复制'; }, 1400);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function() { done(true); }).catch(function() { done(false); });
    } else {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(true); } catch (err) { done(false); }
      document.body.removeChild(ta);
    }
  });
  /* === 锚点复制 (点击 h1/h2/h3 hover 出来的 # 图标 → 复制 page.html#id) === */
  var anchorToast = document.getElementById('anchorToast');
  var anchorToastTimer = null;
  function showAnchorToast(msg) {
    if (!anchorToast) return;
    anchorToast.textContent = msg || '已复制锚点链接';
    anchorToast.classList.add('show');
    if (anchorToastTimer) clearTimeout(anchorToastTimer);
    anchorToastTimer = setTimeout(function() { anchorToast.classList.remove('show'); }, 1800);
  }
  document.addEventListener('click', function(e) {
    var a = e.target.closest && e.target.closest('.content .anchor');
    if (!a) return;
    e.preventDefault();
    var hid = a.getAttribute('data-anchor-id');
    if (!hid) return;
    var url = window.location.origin + window.location.pathname + '#' + hid;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function() { showAnchorToast('已复制: ' + hid); });
    } else {
      // 旧浏览器回退
      var ta = document.createElement('textarea');
      ta.value = url; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); showAnchorToast('已复制: ' + hid); } catch (err) { showAnchorToast('复制失败'); }
      document.body.removeChild(ta);
    }
  });
})();
// R7 反馈: mermaid.js loader + 初始化 (CDN 加载, 自动主题跟随)
(function() {
  if (!document.querySelector('pre.mermaid')) return;
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';
  s.defer = true;
  s.onload = function() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    window.mermaid.initialize({
      startOnLoad: true,
      theme: isDark ? 'dark' : 'default',
      securityLevel: 'loose',
      fontFamily: 'inherit',
    });
  };
  document.head.appendChild(s);
})();
</script>
</body>
</html>"""


def _build_nav_links(docs, current_idx):
    """生成上一篇/下一篇导航

    容器额外带 data-prev / data-next 给键盘 ←/→ 监听器用
    """
    prev_href = ""
    next_href = ""
    links = []
    if current_idx > 0:
        prev_doc = docs[current_idx - 1]
        prev_href = f"{prev_doc.slug}.html"
        links.append(f'<a href="{prev_href}">← {prev_doc.title}</a>')
    else:
        links.append("<span></span>")
    if current_idx < len(docs) - 1:
        next_doc = docs[current_idx + 1]
        next_href = f"{next_doc.slug}.html"
        links.append(f'<a href="{next_href}">{next_doc.title} →</a>')
    else:
        links.append("<span></span>")
    return (
        f'<div class="nav-links" data-prev="{prev_href}" data-next="{next_href}">'
        f'{"".join(links)}</div>'
    )


# ── Phase 4: Hero 首页 + Folder 章节页 ─────────────────

def _format_relative_time(dt, now=None) -> str:
    """把 datetime 转成 '2 小时前' / '3 天前' / '2026-06-01' 三档简短格式
    用于首页"最近更新"列表, 客户端 JS 也用 timeAgo 函数, 但 build 时算一次更可控.
    """
    if dt is None:
        return ""
    from datetime import timezone
    # both naive 和 aware 都规范化成 aware-UTC 然后算 diff
    if dt.tzinfo is None:
        dt_aware = dt.replace(tzinfo=timezone.utc)
    else:
        dt_aware = dt.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt_aware
    secs = int(delta.total_seconds())
    if secs < 0:  # clock skew, 显示刚刚
        return "刚刚"
    if secs < 60:
        return f"{secs} 秒前"
    if secs < 3600:
        return f"{secs // 60} 分钟前"
    if secs < 86400:
        return f"{secs // 3600} 小时前"
    if secs < 2592000:
        return f"{secs // 86400} 天前"
    return dt.strftime("%Y-%m-%d")


def _render_home_hero(project, sidebar_tree: list[dict], all_docs, first_doc_slug: str, index_doc=None) -> str:
    """Phase 4 真首页: Hero + folder 网格 + 最近更新 5 篇
    Phase 5 段 C: 如果项目存在 slug="index" 的 published doc, 用它的 markdown 覆盖 Hero
    段 C 增强 (Admin 2026-06-05 决策 B): index_doc published 时, 整段 Hero 交由它的 markdown 渲染
    输入: project obj (含 name/description), sidebar_tree (folder 节点), all_docs (含 updated_at), first_doc_slug (CTA 链接)
          index_doc (Phase 5 段 C): Document 或 None, 存在时 Hero 内容由它决定
    """
    # 1. Hero 区 (段 C 增强: index_doc published 时整段渲染, 不再只渲染"附加内容区")
    if index_doc and index_doc.status.value == "published" and (index_doc.content or "").strip():
        # 用 index_doc 的 markdown 整段渲染 hero body
        index_body_html, _ = _md_to_html(index_doc.content)
        # 如果 markdown 第一个 H1 存在, 用它替换默认的 project.name H1;
        # 如果 markdown 没 H1, 用 project.name 兜底
        # _replace_heading 会注入 <a class="anchor">#</a>, 所以先剥 anchor 再拿纯文本
        m_h1 = re.match(r"^\s*<h1[^>]*>(.*?)</h1>\s*", index_body_html, flags=re.DOTALL)
        if m_h1:
            inner = m_h1.group(1)
            # 去掉 anchor 链接, 只留纯文本标题
            inner_clean = re.sub(r'<a\s+class="anchor"[^>]*>.*?</a>', "", inner, flags=re.DOTALL)
            hero_title = re.sub(r"<[^>]+>", "", inner_clean).strip() or project.name
            index_body_html = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", index_body_html, count=1, flags=re.DOTALL)
        else:
            hero_title = project.name
        # 如果 markdown 紧跟 H1 后第一个元素是 <p> 段, 用它替换 home-desc;
        # 否则用 project.description 兜底
        m_p = re.match(r"^\s*<p>(.*?)</p>\s*", index_body_html, flags=re.DOTALL)
        if m_p:
            inner_p = m_p.group(1)
            hero_desc = re.sub(r"<[^>]+>", "", inner_p).strip() or (project.description or "项目文档中心, 系统化呈现知识与决策依据。")
            index_body_html = re.sub(r"^\s*<p>.*?</p>\s*", "", index_body_html, count=1, flags=re.DOTALL)
        else:
            hero_desc = project.description or "项目文档中心, 系统化呈现知识与决策依据。"
        hero = f'''
<section class="home-hero">
  <h1>{html.escape(hero_title)}</h1>
  <p class="home-desc">{html.escape(hero_desc)}</p>
  <div class="home-cta-row">
    <a class="home-cta primary" href="{html.escape(first_doc_slug)}.html">开始阅读 →</a>
    <a class="home-cta secondary" href="https://github.com" target="_blank" rel="noopener">GitHub 仓库</a>
  </div>
  <div class="home-hero-content">
    {index_body_html}
  </div>
</section>
'''.strip()
    else:
        # 默认 hardcode hero (index doc 不存在/未发布/无内容)
        hero = f'''
<section class="home-hero">
  <h1>{html.escape(project.name)}</h1>
  <p class="home-desc">{html.escape(project.description or "项目文档中心, 系统化呈现知识与决策依据。")}</p>
  <div class="home-cta-row">
    <a class="home-cta primary" href="{html.escape(first_doc_slug)}.html">开始阅读 →</a>
    <a class="home-cta secondary" href="https://github.com" target="_blank" rel="noopener">GitHub 仓库</a>
  </div>
</section>
'''.strip()

    # 2. Folder 网格 (只列 root folder)
    folder_cards: list[str] = []
    for node in sidebar_tree:
        if not node.get("is_folder"):
            continue
        # 数 published 子 doc (含嵌套)
        def _count_published(n):
            c = 0
            for child in n.get("children", []):
                if child.get("is_folder"):
                    c += _count_published(child)
                elif child.get("status") == "published":
                    c += 1
            return c
        n_pubs = _count_published(node)
        # 顶部 n_pubs 显示
        folder_cards.append(f'''
<a class="folder-card" href="{html.escape(node["slug"])}.html">
  <div class="folder-card-icon">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 7v11a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-7l-2-2H5a2 2 0 0 0-2 2z"/>
    </svg>
  </div>
  <h3 class="folder-card-title">{html.escape(node["title"])}</h3>
  <div class="folder-card-meta">{n_pubs} 篇文档</div>
  <div class="folder-card-arrow">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
      <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
    </svg>
  </div>
</a>
'''.strip())
    folders_section = ""
    if folder_cards:
        folders_section = f'''
<section class="home-section">
  <h2 class="home-section-title">
    <span>章节导航</span>
    <span class="home-section-count">{len(folder_cards)} 个分类</span>
  </h2>
  <div class="folder-grid">
    {"".join(folder_cards)}
  </div>
</section>
'''.strip()

    # 3. 最近更新: 5 个最新 published doc (排除 folder + 排除 slug=index 特殊 doc)
    published_docs = [d for d in all_docs if d.status.value == "published" and d.slug != "index" and (d.content or "").strip()]
    # 按 updated_at 倒序
    published_docs.sort(key=lambda d: d.updated_at or d.created_at, reverse=True)
    recent_items: list[str] = []
    for d in published_docs[:5]:
        ago = _format_relative_time(d.updated_at or d.created_at)
        recent_items.append(f'''
<a class="recent-item" href="{html.escape(d.slug)}.html">
  <svg class="recent-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
  </svg>
  <span class="recent-item-title">{html.escape(d.title)}</span>
  <span class="recent-item-time">{ago}</span>
</a>
'''.strip())
    recent_section = ""
    if recent_items:
        recent_section = f'''
<section class="home-section">
  <h2 class="home-section-title">
    <span>最近更新</span>
    <span class="home-section-count">最新 5 篇</span>
  </h2>
  <ul class="recent-list">
    {"".join(recent_items)}
  </ul>
</section>
'''.strip()

    return hero + "\n" + folders_section + "\n" + recent_section


def _render_folder_overview(folder_node: dict) -> str:
    """Phase 4 文件夹章节页 body: 标题 + 简介 + 该 folder 下所有 published doc 列表

    输入: folder_node (含 title/slug/children), children 递归展开后 flatten
    """
    # 递归 flatten 拿所有 published leaf docs
    def _collect(n, out):
        for c in n.get("children", []):
            if c.get("is_folder"):
                _collect(c, out)
            elif c.get("status") == "published":
                out.append(c)
    leaves: list[dict] = []
    _collect(folder_node, leaves)

    # 渲染每个 doc 卡片
    items: list[str] = []
    for leaf in leaves:
        dt = leaf.get("updated_at") or leaf.get("created_at")
        ago = _format_relative_time(dt) or "已发布"
        items.append(f'''
<a class="folder-overview-item" href="{html.escape(leaf["slug"])}.html">
  <h4 class="folder-overview-item-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
    </svg>
    {html.escape(leaf["title"])}
  </h4>
  <div class="folder-overview-item-meta">
    <span>{ago}</span>
  </div>
</a>
'''.strip())

    body = f'<h1>{html.escape(folder_node["title"])}</h1>\n'
    body += f'<p>本章节包含 {len(leaves)} 篇已发布文档。</p>\n'
    if items:
        body += f'<ul class="folder-overview-list">{"".join(items)}</ul>\n'
    else:
        body += '<div class="folder-overview-empty">本章节暂无已发布文档, 请在 OpenDocX 管理后台编辑后发布。</div>\n'
    return body


# ── 主构建函数 ─────────────────────────────────────────────

async def build_docusaurus(
    db: AsyncSession,
    project_id: str,
    version_id: str,
    triggered_by: str,
) -> BuildLog:
    """构建静态文档站"""
    build = BuildLog(
        project_id=project_id,
        version_id=version_id,
        status=BuildStatus.building,
        triggered_by=triggered_by,
    )
    db.add(build)
    await db.commit()
    await db.refresh(build)

    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one()
    version = (await db.execute(select(Version).where(Version.id == version_id))).scalar_one()

    # 拉取所有 docs (含 folder), 构树用
    all_docs = (await db.execute(
        select(Document)
        .where(Document.version_id == version_id)
        .order_by(Document.sort_order, Document.created_at)
    )).scalars().all()

    # 只有 status='published' 的真实 doc 才会生成 HTML 文件
    # folder (content 为空) 不产 HTML, 但参与 sidebar 树
    def _is_empty_content(d) -> bool:
        c = d.content
        return (not c) or (isinstance(c, str) and c.strip() == '')

    def _is_folder(d) -> bool:
        # 约定: content 为空 → folder-only
        return _is_empty_content(d)

    # 已发布的 doc (非 folder) 用于生成 HTML 文件
    publishable_docs = [d for d in all_docs if d.status == "published" and not _is_folder(d)]
    # 所有 doc (含 folder) 用于构 sidebar 树
    all_nodes_for_tree = list(all_docs)

    # === Phase 5 段 C: 找 slug="index" 的特殊 doc ===
    # 用途: index_doc published 时, 它的 markdown 覆盖首页 Hero
    # 过滤: 不出现在 sidebar 树 / 最近更新 / doc 列表, 只作为 Hero 内容源
    index_doc = next((d for d in all_docs if d.slug == "index"), None)
    if index_doc:
        all_nodes_for_tree = [d for d in all_nodes_for_tree if d.slug != "index"]
        publishable_docs = [d for d in publishable_docs if d.slug != "index"]
        # docs_by_id 给 sidebar 用 — 也过滤掉, 避免 folder 把它当 child
        # (sidebar 渲染时按 parent_id 查, index 不会有 parent_id, 但保险起见)

    start_time = datetime.now()

    try:
        build_dir = os.path.join(settings.data_dir, "builds", project.slug, version.version)
        os.makedirs(build_dir, exist_ok=True)

        # === 复制 design tokens CSS (Phase 5 段 B: Infima 6 段 token 抽离) ===
        # 源: backend/app/services/_static/tokens.css → 目标: build_dir/static/css/tokens.css
        _tokens_src = os.path.join(os.path.dirname(__file__), "_static", "css", "tokens.css")
        _tokens_dst_dir = os.path.join(build_dir, "static", "css")
        os.makedirs(_tokens_dst_dir, exist_ok=True)
        if os.path.exists(_tokens_src):
            import shutil
            shutil.copy(_tokens_src, os.path.join(_tokens_dst_dir, "tokens.css"))
        # tokens.css 缺失不阻塞 build (模板用 <link> 引用, 缺则浏览器 404 但页能渲染)

        # === R10: 复制项目级 static/ 资源 (img / video / 字体) ──
        # 源: backend/app/services/_static/static/ → 目标: build_dir/static/
        # 文档里用 ![alt](static/images/x.png) 引用, build 端整体复制过去
        _static_src = os.path.join(os.path.dirname(__file__), "_static", "static")
        _static_dst = os.path.join(build_dir, "static")
        if os.path.isdir(_static_src):
            # 用 copytree 同步, 允许存在 (再次 build 不报错)
            try:
                shutil.copytree(_static_src, _static_dst, dirs_exist_ok=True)
            except Exception as e:
                # 复制失败不阻塞 build (单文件失败 = 文档图片 404, 但页能渲染)
                print(f"warn: _static/static 复制失败: {e}")

        # === 用户上传资产: 复制到 build_dir/assets 并准备 URL 重写 ===
        version_assets = (await db.execute(
            select(DocumentAsset).where(DocumentAsset.version_id == version_id)
        )).scalars().all()
        assets_dir = os.path.join(build_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        asset_url_map: dict[str, str] = {}
        for asset in version_assets:
            src = os.path.join(settings.data_dir, asset.storage_path)
            dst = os.path.join(assets_dir, asset.stored_filename)
            asset_url_map[f"/api/v1/assets/{asset.id}/file"] = asset.public_path
            if not os.path.exists(src):
                print(f"warn: asset missing: {asset.storage_path}")
                continue
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"warn: asset copy failed {asset.storage_path}: {e}")

        def _rewrite_asset_urls(markup: str) -> str:
            for api_url, public_path in asset_url_map.items():
                escaped_api = html.escape(api_url, quote=True)
                escaped_public = html.escape(public_path, quote=True)
                markup = markup.replace(f'src="{escaped_api}"', f'src="{escaped_public}"')
                markup = markup.replace(f"src='{escaped_api}'", f"src='{escaped_public}'")
                markup = markup.replace(f'href="{escaped_api}"', f'href="{escaped_public}"')
                markup = markup.replace(f"href='{escaped_api}'", f"href='{escaped_public}'")
            return markup

        if not publishable_docs:
            build.status = BuildStatus.failed
            build.output = "没有已发布的文档"
            build.duration = 0
            await db.commit()
            await db.refresh(build)
            return build

        # === 构 sidebar 树 (用 all_docs 含 folder) ===
        # 树结构按 parent_id + sort_order 排序
        def _build_tree() -> list[dict]:
            # children_count + is_folder 算
            children_count: dict[str, int] = {}
            for d in all_nodes_for_tree:
                if d.parent_id:
                    children_count[d.parent_id] = children_count.get(d.parent_id, 0) + 1
            def _meta(d) -> dict:
                return {
                    "id": d.id,
                    "title": d.title,
                    "slug": d.slug,
                    "status": d.status.value,
                    "is_folder": _is_folder(d) or children_count.get(d.id, 0) > 0,
                    # 章节页要显示 doc 列表的发布时间, 所以保留 updated_at
                    "updated_at": d.updated_at,
                    "created_at": d.created_at,
                }
            node_map: dict[str, dict] = {d.id: {**_meta(d), "children": []} for d in all_nodes_for_tree}
            roots: list[dict] = []
            for d in all_nodes_for_tree:
                if d.parent_id and d.parent_id in node_map:
                    node_map[d.parent_id]["children"].append(node_map[d.id])
                else:
                    roots.append(node_map[d.id])
            return roots

        sidebar_tree = _build_tree()

        def _render_sidebar(nodes: list[dict], depth: int = 0) -> str:
            """递归渲染: folder=<details><summary>📁 name</summary>... </details>, doc=<a>
            注意: sidebar 列出 folder 全部子节点 (不按 status 过滤), 但只有 published 的 doc 生成 HTML 链接
            (draft 渲染成 <a class='nav-draft'>, 点击显示提示而非 404)

            Phase 4 改动: folder 整行可点 → 跳到 <folder-slug>.html 章节页
            """
            out: list[str] = []
            for n in nodes:
                if n["is_folder"]:
                    sub = _render_sidebar(n["children"], depth + 1) if n["children"] else ""
                    # open 给 depth=0 (root folder) 默认展开, 其它折叠
                    open_attr = " open" if depth == 0 else ""
                    label = html.escape(n["title"])
                    # folder 自己跳到 overview 页
                    folder_url = f"{html.escape(n['slug'])}.html"
                    folder_icon = '<svg class="nav-icon-folder" viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h2.379a1.5 1.5 0 0 1 1.06.44L8.5 5h4A1.5 1.5 0 0 1 14 6.5v5A1.5 1.5 0 0 1 12.5 13h-9A1.5 1.5 0 0 1 2 11.5v-7z"/></svg>'
                    chevron = '<svg class="nav-folder-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>'
                    out.append(
                        f'<details class="nav-folder nav-folder-as-link"{open_attr} data-depth="{depth}" data-slug="{html.escape(n["slug"])}">'
                        f'<summary>{folder_icon}'
                        f'<a class="nav-folder-label" href="{folder_url}">{label}</a>'
                        f'{chevron}'
                        f'</summary>'
                        f'{sub}'
                        f'</details>'
                    )
                else:
                    # doc: 全部渲染. published 才出 HTML, draft/draft 标灰禁用提示
                    if n["status"] == "published":
                        out.append(
                            f'<a href="{html.escape(n["slug"])}.html" data-folder="false">{html.escape(n["title"])}</a>'
                        )
                    else:
                        # draft 状态: 仍显示在目录, 但不可点击 (避免点开 404)
                        out.append(
                            f'<a href="#" class="nav-draft" data-status="{html.escape(n["status"])}" '
                            f'title="该文档尚未发布, 构建不会生成页面" '
                            f'onclick="event.preventDefault(); alert(\'该文档状态: {html.escape(n["status"])}\\n请先在 OpenDocX 文档编辑页点击「发布」, 然后重新构建。\')">'
                            f'{html.escape(n["title"])} <span class="nav-draft-tag">草稿</span></a>'
                        )
            return "".join(out)

        sidebar_links = _render_sidebar(sidebar_tree)

        # === P1-W3-L3-C8: 项目级配置 (_config.yml) 注入 ===
        from app.services.project_config import load_project_config
        project_config = load_project_config(project.slug, settings.data_dir)
        # brand_color: ProjectConfig.theme.primary_color 覆盖 Project.brand_color
        if project_config.theme.primary_color:
            brand_color = project_config.theme.primary_color
        else:
            brand_color = project.brand_color or "#4F46E5"
        # project_name 显示: ProjectConfig.nav.title 覆盖 Project.name
        project_display_name = project_config.nav.title or project.name
        # tagline 注入 (P1-W3-L3-C8: 静态站 Hero 副标题)
        project_tagline = project_config.tagline or project.description or ""

        # === 为每个已发布 doc 生成 HTML 页面 ===
        # 注意：不再额外包裹 <h1>{title}</h1>，由 markdown 自身的 # 决定标题层级，
        # 避免 H1 重复（之前 template body 里的 h1 + md 转出的 h1 共两个）。
        for idx, doc in enumerate(publishable_docs):
            body, toc = _md_to_html(doc.content or "")
            body = _rewrite_asset_urls(body)
            # 如果 markdown 没有以 # 开头，自动补一个 H1（保持视觉一致）
            if not body.lstrip().startswith("<h1"):
                # 手动补的 H1 也加 id, 跟 TOC 对齐
                h1_id = _slugify(doc.title) or "page-title"
                body = f'<h1 id="{h1_id}"><a class="anchor" href="#{h1_id}">#</a>{html.escape(doc.title)}</h1>\n' + body
                # 补 TOC
                if not any(e["id"] == h1_id for e in toc):
                    toc.insert(0, {"id": h1_id, "level": 1, "text": doc.title})
            nav_links = _build_nav_links(publishable_docs, idx)
            toc_html = _render_toc(toc)

            # .replace 模式 (替代 .format, 避免解析 CSS/JS 里的 {} 引发 Single '}' / KeyError)
            # 见 skill §3: JS 里有 {} 对象字面量, CSS 里有 @media 块, .format 容易炸
            page_html = _HTML_TEMPLATE
            page_html = page_html.replace("{title}", html.escape(doc.title))
            page_html = page_html.replace("{project_name}", html.escape(project_display_name))
            page_html = page_html.replace("{version}", html.escape(version.version))
            page_html = page_html.replace("{brand_color}", brand_color)
            page_html = page_html.replace("__BRAND_COLOR__", brand_color)
            # C8 tagline 注入 (空时不输出任何 CSS)
            tagline_block = f"/* tagline: {html.escape(project_tagline)} */" if project_tagline else ""
            page_html = page_html.replace("__TAGLINE_BLOCK__", tagline_block)
            page_html = page_html.replace("{sidebar_links}", sidebar_links)
            page_html = page_html.replace("{body}", body)
            page_html = page_html.replace("{nav_links}", nav_links)
            page_html = page_html.replace("{toc_html}", toc_html)
            page_html = page_html.replace("{doc_slug}", html.escape(doc.slug))
            page_html = page_html.replace("{doc_id}", html.escape(doc.id))
            page_html = page_html.replace("{version_id}", html.escape(version.id))
            page_html = page_html.replace("{pyg_light_css}", _pyg_css_light)
            page_html = page_html.replace("{pyg_dark_css}", _pyg_css_dark_scoped)
            # 反馈区 (文档页用, 含 doc_id) 必须在 .replace 链末端
            feedback_section = _FEEDBACK_SECTION.replace("{doc_slug}", html.escape(doc.slug)).replace("{doc_id}", html.escape(doc.id)).replace("{version_id}", html.escape(version.id))
            page_html = page_html.replace("<!--FEEDBACK_SECTION_PLACEHOLDER-->", feedback_section)
            # .replace 之后再注入 JS (JS 含 {} 字面量, 不能走 .format)
            page_html = page_html.replace("<!--FEEDBACK_JS_PLACEHOLDER-->", _FEEDBACK_JS)
            page_html = page_html.replace("<!--INTERACTION_JS_PLACEHOLDER-->", _INTERACTION_JS)

            with open(os.path.join(build_dir, f"{doc.slug}.html"), "w", encoding="utf-8") as f:
                f.write(page_html)

        # 生成首页 (Phase 4: 真 Hero + folder 网格 + 最近更新)
        # Phase 5 段 C: 传 index_doc — published 时用其 markdown 覆盖 Hero
        first_slug = publishable_docs[0].slug if publishable_docs else "index"
        index_body = _render_home_hero(project, sidebar_tree, all_docs, first_slug, index_doc=index_doc)
        index_body = _rewrite_asset_urls(index_body)
        index_html = _HTML_TEMPLATE
        index_html = index_html.replace("{title}", "首页")
        index_html = index_html.replace("{project_name}", html.escape(project_display_name))
        index_html = index_html.replace("{version}", html.escape(version.version))
        index_html = index_html.replace("{brand_color}", brand_color)
        index_html = index_html.replace("__BRAND_COLOR__", brand_color)
        tagline_block_idx = f"/* tagline: {html.escape(project_tagline)} */" if project_tagline else ""
        index_html = index_html.replace("__TAGLINE_BLOCK__", tagline_block_idx)
        index_html = index_html.replace("{sidebar_links}", sidebar_links)
        index_html = index_html.replace("{body}", index_body)
        index_html = index_html.replace("{nav_links}", "")
        index_html = index_html.replace("{toc_html}", '<aside class="toc" data-empty="true"></aside>')
        index_html = index_html.replace("{doc_slug}", "")
        index_html = index_html.replace("{doc_id}", "")
        index_html = index_html.replace("{version_id}", html.escape(version.id))
        index_html = index_html.replace("{pyg_light_css}", _pyg_css_light)
        index_html = index_html.replace("{pyg_dark_css}", _pyg_css_dark_scoped)
        # 首页无 doc_id, 也不需要 feedback JS (反馈区 JS 内部检查 docId 为空直接 return)
        index_html = index_html.replace("<!--FEEDBACK_SECTION_PLACEHOLDER-->", "")
        index_html = index_html.replace("<!--FEEDBACK_JS_PLACEHOLDER-->", "")
        index_html = index_html.replace("<!--INTERACTION_JS_PLACEHOLDER-->", "")
        with open(os.path.join(build_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        # === Phase 4: 为每个 folder 生成章节页 (folder-slug.html) ===
        def _generate_folder_pages(nodes: list[dict]):
            for n in nodes:
                if not n.get("is_folder"):
                    continue
                # 递归先生成子 folder
                _generate_folder_pages(n.get("children", []))
                # 渲染本页
                folder_body = _render_folder_overview(n)
                folder_html = _HTML_TEMPLATE
                folder_html = folder_html.replace("{title}", html.escape(n["title"]))
                folder_html = folder_html.replace("{project_name}", html.escape(project_display_name))
                folder_html = folder_html.replace("{version}", html.escape(version.version))
                folder_html = folder_html.replace("{brand_color}", brand_color)
                folder_html = folder_html.replace("__BRAND_COLOR__", brand_color)
                tagline_block_fld = f"/* tagline: {html.escape(project_tagline)} */" if project_tagline else ""
                folder_html = folder_html.replace("__TAGLINE_BLOCK__", tagline_block_fld)
                folder_html = folder_html.replace("{sidebar_links}", sidebar_links)
                folder_html = folder_html.replace("{body}", folder_body)
                folder_html = folder_html.replace("{nav_links}", "")
                folder_html = folder_html.replace("{toc_html}", '<aside class="toc" data-empty="true"></aside>')
                folder_html = folder_html.replace("{doc_slug}", "")
                folder_html = folder_html.replace("{doc_id}", "")
                folder_html = folder_html.replace("{version_id}", html.escape(version.id))
                folder_html = folder_html.replace("{pyg_light_css}", _pyg_css_light)
                folder_html = folder_html.replace("{pyg_dark_css}", _pyg_css_dark_scoped)
                folder_html = folder_html.replace("<!--FEEDBACK_SECTION_PLACEHOLDER-->", "")
                folder_html = folder_html.replace("<!--FEEDBACK_JS_PLACEHOLDER-->", "")
                folder_html = folder_html.replace("<!--INTERACTION_JS_PLACEHOLDER-->", "")
                with open(os.path.join(build_dir, f"{n['slug']}.html"), "w", encoding="utf-8") as f:
                    f.write(folder_html)
        _generate_folder_pages(sidebar_tree)

        # 统计输出: 真实生成的 HTML 页数 + sidebar 树结构概览
        def _count_in_tree(nodes: list[dict], published: list[int] = [0], folders: list[int] = [0]) -> tuple[int, int]:
            for n in nodes:
                if n["is_folder"]:
                    folders[0] += 1
                elif n["status"] == "published":
                    published[0] += 1
                if n["children"]:
                    _count_in_tree(n["children"], published, folders)
            return published[0], folders[0]

        published_count, folder_count = _count_in_tree(sidebar_tree)
        duration = int((datetime.now() - start_time).total_seconds())
        build.status = BuildStatus.success
        build.output = f"构建成功：{published_count} 篇已发布文档 + {folder_count} 个文件夹，耗时 {duration}s"
        build.duration = duration

    except Exception as e:
        build.status = BuildStatus.failed
        build.output = str(e)
        build.duration = int((datetime.now() - start_time).total_seconds())

    await db.commit()
    await db.refresh(build)
    return build
