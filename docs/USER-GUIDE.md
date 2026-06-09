# OpenDocX User Guide

> A complete guide to using OpenDocX - from your first login to advanced workflows.
> Last updated: 2026-06-08 · v0.1.0

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Keyboard Shortcuts](#2-keyboard-shortcuts)
3. [AI Assistant](#3-ai-assistant)
4. [AI Floating Tip](#4-ai-floating-tip)
5. [Command Palette](#5-command-palette)
6. [Projects & Versions](#6-projects--versions)
7. [Documents](#7-documents)
8. [Build & Publish](#8-build--publish)
9. [Pre-Build Confirmation](#9-pre-build-confirmation)
10. [Static Site Output](#10-static-site-output)
11. [Admin & Audit](#11-admin--audit)
12. [Settings](#12-settings)

---

## 1. Getting Started

### First Login

After running `bash scripts/seed_demo.sh`, your local OpenDocX instance has:

- **URL**: `http://localhost:3077` (Vite dev) or `http://localhost` (Docker)
- **Email**: `admin@opendocx.local`
- **Password**: `admin123`

The seed script creates:
- 1 admin account (above credentials)
- 1 demo project: "Welcome to OpenDocX"
- 2 sample documents (Getting Started + AI Floating Tip Demo)

You can log in, explore, and delete this demo project anytime - it won't affect other data.

### The Three Main Areas

After login, you land on the **Dashboard** with these areas:

| Area | Purpose |
|---|---|
| **Projects** | Browse / create / edit documentation projects |
| **Documents** | Edit Markdown with live preview, AI assistance, version control |
| **Published** | Browse generated static sites and download them for deployment |

---

## 2. Keyboard Shortcuts

| Shortcut | Action | Where |
|---|---|---|
| `Cmd K` / `Ctrl K` | Open command palette - search docs / projects / settings | Anywhere |
| `Cmd N` | Jump to "New Project" | Anywhere |
| `Cmd U` | Jump to upload Markdown | Anywhere |
| `Cmd B` | Jump to "Build & Publish" for current project | Anywhere |
| `Cmd Shift A` | Show AI floating tip (after selecting text in editor) | Editor |
| `Cmd Shift F` | Rewrite selection to be more formal | Editor (with selection) |
| `Cmd Shift S` | Rewrite selection to be more concise | Editor (with selection) |
| `Cmd Shift N` | Rewrite selection to be friendlier | Editor (with selection) |
| `Esc` | Close any popup (command palette, drawer, modal) | Anywhere |

> Mac users: use `Cmd`. Windows/Linux: use `Ctrl`.

---

## 3. AI Assistant

OpenDocX uses AI (LLM) to help you write and edit documentation. The AI is configured via your `.env` file - you can use OpenAI, Anthropic, or any OpenAI-compatible service (e.g., Xiaomi mimo, local Ollama).

### AI Capabilities

OpenDocX offers AI in two main places:

1. **AI Floating Tip** - select text in editor, get instant AI actions
2. **AI Panel** (right sidebar in editor) - longer-form AI assistance

### Configuration

Edit `.env` in your project root:

```bash
LLM_PROVIDER=openai              # openai | hermes
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT=60
```

After changing, restart the backend:
```

After changing, restart the backend:
```bash
bash backend/scripts/start-backend.sh
```

---

## 4. AI Floating Tip

The fastest way to use AI: select any text in the Markdown editor.

### How to Use

1. **Select text** with your mouse (drag to highlight)
2. Wait for the floating tip to appear near your selection
3. Click an action, or press the hotkey

### Available Actions

| Action | What it does |
|---|---|
| **Rewrite** | Improve clarity while keeping meaning |
| **Continue** | Keep writing in the same style |
| **Translate** | Translate to English (more languages coming) |
| **Summarize** | Compress long paragraphs into 1-2 sentences |
| **Fix** | Correct grammar and typos |
| **Change Tone** | Switch between formal / friendly / concise |
| **More Formal** | One-click formal rewrite |
| **More Concise** | One-click shorter rewrite |
| **Friendlier** | One-click warmer rewrite |

### Review and Apply

After you trigger an action:
- The AI response streams in real-time (you see words appear as the model generates)
- A **review modal** appears with two buttons:
  - **Accept & Replace** - replaces your selected text with the AI's output
  - **Reject** - discards the AI output, keeps your original

### Selection-Aware Q&A (v0.1.0+)

The AI can answer questions about your **selection** specifically, without pulling from the rest of the document. For example:

- Select a paragraph about "API rate limits"
- Open the AI tip
- Type: "what's the 429 status code meaning?"
- The AI answers based on your selection, not the whole document

This is useful when you want focused, contextual answers.

---

## 5. Command Palette

Press `Cmd K` (or `Ctrl K`) anywhere to open the command palette.

### What You Can Do

- **Search**: Find documents, projects, versions, settings
- **Navigate**: Jump to any page in the app
- **Create**: New project, new document, new version
- **Actions**: Switch theme, log out, view audit logs

The search uses **semantic embeddings** (via sentence-transformers), so you can search by meaning, not just exact keywords. For example, searching "rate limit" will find docs containing "throttling" or "429 status code".

---

## 6. Projects & Versions

### What is a Project?

A **project** is a documentation workspace. Each project has:
- A name and description
- One or more **versions** (e.g., v1.0, v2.0)
- A list of **users** with permissions (admin / editor / viewer)
- A **brand color** and logo (for the static site output)

### What is a Version?

A **version** is a snapshot of your documentation at a point in time. Common use cases:
- **Product versions**: v1.0, v1.1, v2.0 - one version per release
- **Stage versions**: draft, beta, stable - same docs at different maturity levels

Each version has its own:
- Set of documents
- Static site output
- Build history

### Creating a New Project

1. Go to **Projects** in the sidebar
2. Click **New Project** in the top-right
3. Fill in:
   - Name (required)
   - Slug (URL-friendly, auto-generated, editable)
   - Description (optional)
   - Brand color (default: indigo)
4. Click **Create**

A default version `v1.0` is created automatically.

### Project Statuses

| Status | Meaning |
|---|---|
| `active` | Default, working state |
| `paused` | Temporarily disabled, not shown in default lists |
| `draft` | Not yet ready for public viewing |
| `archived` | Old, hidden from main views |

---

## 7. Documents

### Document Tree

The left sidebar of any project shows the **document tree**:
- **Folders** (gray icon) can contain documents and sub-folders (unlimited nesting)
- **Documents** (file icon) are individual Markdown files
- **Status badges** next to each document:
  - Green = published
  - Orange = draft
  - Gray = archived
  - Red = error (e.g., failed build)

Click any document to open it in the editor.

### The Editor

OpenDocX uses a **three-column editor**:

1. **Left**: Document tree (collapsible folders, status indicators)
2. **Center**: Markdown editor with live preview
   - Edit Markdown in the top half
   - See rendered HTML in the bottom half
   - Scroll syncs between them
3. **Right**: AI panel (longer-form AI assistance, separate from floating tip)

### Markdown Features

OpenDocX supports extended Markdown:

- **GFM** (GitHub Flavored Markdown): tables, task lists, strikethrough, autolinks
- **Code blocks** with syntax highlighting (13 languages: Python, JavaScript, TypeScript, Bash, JSON, YAML, SQL, HTML, CSS, Markdown, Go, Rust, Java)
- **Mermaid diagrams**: use ` ```mermaid ` code block
- **Admonitions** (5 types): `> [!NOTE]`, `> [!TIP]`, `> [!WARNING]`, `> [!DANGER]`, `> [!INFO]`
- **Images**: drag-drop, paste, or `![alt](url)`
- **Video & iframes**: embed YouTube / Vimeo / GitHub gists
- **Math**: KaTeX (optional, not enabled by default)

### Saving

OpenDocX auto-saves every 30 seconds. You can also:
- `Cmd S` to save manually
- The status bar at the bottom shows "Saved" / "Saving..." / "Unsaved changes"

### Document Statuses

| Status | Meaning |
|---|---|
| `draft` | Being edited, not in static site output |
| `published` | Included in static site output |
| `archived` | Hidden from views, kept for history |

---

## 8. Build & Publish

### What is "Build"?

The **Build** button generates a complete **static HTML site** from your database documents. The output is in `data/builds/<project>/<version>/` and can be:
- Opened locally by double-clicking `index.html`
- Deployed to any static host (Vercel, Netlify, GitHub Pages, S3, Nginx)

### How to Build

1. Go to your project
2. Click **Build** in the top-right
3. **Pre-Build Confirmation modal** appears (see next section)
4. Review and confirm
5. Wait for build to complete (typically 5-30 seconds)
6. Click **Open Static Site** to preview
7. Click **Download** to get a ZIP

### Build Output

After a successful build, you have:
- `data/builds/<project>/<version>/index.html` - landing page
- `data/builds/<project>/<version>/docs/<slug>/index.html` - one HTML per document
- `data/builds/<project>/<version>/static/css/tokens.css` - design tokens
- `data/builds/<project>/<version>/static/css/main.css` - main styles
- `data/builds/<project>/<version>/static/images/` - all images
- `data/builds/<project>/<version>/sitemap.xml` - for SEO

### Build Performance

- Small project (10 docs): 2-5 seconds
- Medium project (50 docs): 10-20 seconds
- Large project (200+ docs): 30-60 seconds

---

## 9. Pre-Build Confirmation

Before building, OpenDocX shows a **Pre-Build Modal** so you can:

1. **See all your documents** in a tree
2. **See statistics**:
   - Total documents
   - Published count
   - Draft count
   - Empty content count
3. **Publish drafts** before building (so they appear in static site)
4. **Bulk publish** multiple drafts at once

### Modal Components

**Top stats bar**:
```
Total: 14 · Published: 10 · Draft: 4 · Empty: 0
```

**Action buttons**:
- **Select All Unpublished** - check all draft checkboxes
- **Clear Selection** - uncheck everything
- **Bulk Publish Selected (N)** - publish all checked drafts at once

**Per-document actions**:
- **Publish** - publish this single draft
- **Save & Publish** - if you have unsaved changes, this saves + publishes in one step

**Bottom buttons**:
- **Start Build** (primary) - proceed with build
- **Cancel** - close modal without building

### Why This Matters

Without this modal, you might click "Build" and forget to publish your drafts - then the static site is missing pages. The modal catches this **before** the build, not after.

---

## 10. Static Site Output

### Deployment Options

Once you've built, you can deploy the `data/builds/<project>/<version>/` folder to:

| Host | Best for |
|---|---|
| **Vercel** | Easiest, free tier, auto-deploy from git |
| **Netlify** | Similar to Vercel, great DX |
| **GitHub Pages** | Free for public repos, no build step needed |
| **AWS S3 + CloudFront** | Enterprise, scalable, pay-as-you-go |
| **Nginx (self-hosted)** | Full control, your own server |
| **Any static host** | Just upload the folder - no server-side code needed |

### Self-Hosting Example (Nginx)

```bash
# After build, copy output to nginx
sudo cp -r data/builds/my-project/v1.0/* /var/www/html/

# nginx config (/etc/nginx/sites-enabled/default)
server {
    listen 80;
    server_name docs.example.com;
    root /var/www/html;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
```

### Themes

The static site supports both **light** and **dark** themes. A toggle button in the top-right switches between them. The user's preference is saved in `localStorage`.

Theme is determined by the user's OS preference on first visit, then they can override.

### Features Included in Static Site

- Full-text search (client-side, instant)
- Sidebar navigation with collapsible folders
- Code block syntax highlighting
- Mermaid diagram rendering
- Admonition blocks
- Image lazy loading
- Mobile responsive (tested on phones / tablets / desktop)
- SEO optimized (meta tags, sitemap.xml, Open Graph)
- Zero external dependencies (no JS framework at runtime)

---

## 11. Admin & Audit

### User Roles

| Role | Permissions |
|---|---|
| **admin** | Full access: manage users, edit any doc, build, view audit logs |
| **editor** | Edit assigned docs, cannot manage users |
| **viewer** | Read-only access |

### User Management (Admin Only)

Go to **Settings → Users** (admin only) to:
- View all users
- Create new user
- Change user role
- Reset password
- Disable / re-enable user

### Audit Logs

Every administrative action is logged:
- Who did what (`actor_email`)
- When (timestamp)
- What changed (before / after)
- From which IP

Go to **Settings → Audit** (admin only) to view logs. Filter by:
- Date range
- Action type (create / update / delete / login)
- User
- IP

Audit logs are **append-only** - you cannot edit or delete them. They are required for compliance in many industries (GDPR, SOC 2, HIPAA).

---

## 12. Settings

### Profile

- **Name**: Display name (shown in comment threads, audit logs)
- **Email**: Used for login (cannot be changed without admin)
- **Avatar**: Profile picture (upload or use Gravatar)

### Change Password

Go to **Settings → Security**:
1. Enter old password
2. Enter new password (min 8 characters, recommend 12+ with mixed case + numbers + symbols)
3. Confirm new password
4. Click **Update Password**

### Preferences

- **Theme**: Light / Dark / System (auto)
- **Language**: English / 中文 (interface only, not static site content)
- **Timezone**: For displaying timestamps
- **Editor font size**: Small / Medium / Large

---

## Common Questions

### Q: How do I add a new language to the static site?

OpenDocX generates one static site per project. For multi-language, create one project per language (e.g., `my-project-en`, `my-project-zh`). See [docs/ROADMAP.md](ROADMAP.md#i18n) for the rationale.

### Q: Can I edit the same doc in two browsers at once?

Yes, but the last save wins. OpenDocX doesn't have real-time collaborative editing (no operational transform). If both users save, the later save overwrites the earlier one. Use branches (separate versions) for parallel work.

### Q: How do I delete a project?

**Project card → ⚙️ Settings → Delete Project** (admin only). This is a soft delete - the project is archived, not removed. To permanently delete, contact your instance admin.

### Q: Why is my AI tip not appearing?

Check:
1. Backend is running (`bash backend/scripts/start-backend.sh`)
2. `.env` has valid `LLM_API_KEY` (not `***` placeholder)
3. `LLM_BASE_URL` is reachable from your network
4. You selected at least 1 character of text

If still not working, check backend logs for errors.

### Q: How do I deploy the static site to my own server?

1. Build the project (see Section 8)
2. Copy `data/builds/<project>/<version>/*` to your server's web root
3. Configure your web server (Nginx / Apache) to serve the folder
4. Test by visiting your domain

For HTTPS, use Let's Encrypt (free) or your hosting provider's cert.

---

## Getting Help

- **Documentation**: This file
- **Issues**: [GitHub Issues](https://github.com/wangliu/opendocx/issues)
- **Discussions**: [GitHub Discussions](https://github.com/wangliu/opendocx/discussions)
- **Email**: support@opendocx.dev (placeholder, TBD)

---

<sub>Last revised: 2026-06-08 · Version: v0.1.0</sub>
