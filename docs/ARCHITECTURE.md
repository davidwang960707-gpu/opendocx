# OpenDocX Architecture

> How OpenDocX works under the hood.
> Audience: developers who want to understand, modify, or contribute to OpenDocX.

---

## High-Level Overview

OpenDocX is a **3-tier application**:

```
┌─────────────────────────────────────────────────────────┐
│  Browser (React 18 SPA)                                 │
│  - Ant Design 5 components                              │
│  - Vite dev server / Nginx production                   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON + SSE
┌──────────────────────▼──────────────────────────────────┐
│  FastAPI Backend (Python 3.12)                          │
│  - REST API for CRUD operations                         │
│  - SSE for AI streaming responses                       │
│  - Static site generator (mistune + pygments)           │
└──────────────────────┬──────────────────────────────────┘
                       │ SQLAlchemy 2.0 (async)
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌────────────────┐          ┌──────────────────┐
│  PostgreSQL 16 │          │  Redis 7         │
│  + pgvector    │          │  (rate limiting) │
└────────────────┘          └──────────────────┘
```

**Why this design?**

- **React SPA + REST API** is the standard pattern, easy to understand and extend
- **FastAPI** is async-first and gives us free OpenAPI docs (good DX)
- **SSE instead of WebSocket** for AI: simpler, works through HTTP proxies, sufficient for one-way streaming
- **PostgreSQL + pgvector** keeps docs and embeddings in one DB (no separate vector store to manage)
- **Redis** is just for rate limiting (could be in-memory for small scale)

---

## Tech Stack

| Layer | Technology | Version | Why |
|---|---|---|---|
| **Frontend** | React | 18.3 | Stable, well-supported, large ecosystem |
| **Frontend** | TypeScript | 5.6 | Catch errors at compile time |
| **Frontend** | Vite | 6.0 | Fast HMR, simple build |
| **Frontend** | Ant Design | 5.22 | Comprehensive component library, MIT license |
| **Frontend** | Zustand | 5.0 | Lightweight state management |
| **Frontend** | Axios | 1.7 | HTTP client with interceptors |
| **Frontend** | React Router | 6.28 | Standard React routing |
| **Frontend** | React Markdown | 9.0 | Markdown rendering |
| **Frontend** | @uiw/react-md-editor | 4.0 | Markdown editor with toolbar |
| **Backend** | Python | 3.12 | Modern async support, type hints |
| **Backend** | FastAPI | 0.115 | Async, fast, auto OpenAPI docs |
| **Backend** | SQLAlchemy | 2.0 | Async ORM, type-safe queries |
| **Backend** | asyncpg | 0.30 | Fast async PostgreSQL driver |
| **Backend** | Alembic | 1.14 | Database migrations |
| **Backend** | pgvector | 0.7 | Vector similarity search |
| **Backend** | Pydantic | 2.10 | Data validation |
| **Backend** | python-jose | 3.3 | JWT token handling |
| **Backend** | bcrypt | 4.2 | Password hashing (via passlib) |
| **Backend** | httpx | 0.28 | Async HTTP client (for LLM API) |
| **Backend** | mistune | 3.2 | Markdown parser |
| **Backend** | pygments | 2.20 | Syntax highlighting |
| **Backend** | bleach | 6.3 | HTML sanitization |
| **Database** | PostgreSQL | 16 | Reliable, pgvector support |
| **Database** | Redis | 7 | Rate limiting, caching |
| **AI** | OpenAI API | - | LLM provider (configurable) |
| **AI** | sentence-transformers | 3.3 | Local embeddings (BAAI/bge-m3) |
| **Build** | mistune + pygments + custom | - | Static site generation |
| **Testing** | pytest + pytest-asyncio | 8.3 / 0.24 | Standard Python testing |
| **CI** | GitHub Actions | - | Free for public repos |
| **Deploy** | Docker Compose | 3.9 | Single command to run |

---

## Backend Architecture

### Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings (Pydantic)
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── version.py
│   │   ├── document.py
│   │   ├── feedback.py
│   │   ├── audit.py
│   │   ├── build_log.py
│   │   └── document_embedding.py
│   ├── schemas/                # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── document.py
│   │   ├── build.py
│   │   ├── feedback.py
│   │   ├── search.py
│   │   └── common.py
│   ├── routers/                # FastAPI route handlers
│   │   ├── auth.py             # POST /auth/login, /auth/register
│   │   ├── users.py            # GET/PUT /users/*
│   │   ├── projects.py         # GET/POST/PUT/DELETE /projects/*
│   │   ├── documents.py        # CRUD on documents
│   │   ├── build.py            # POST /build/{vid}
│   │   ├── editor.py           # POST /editor/ai (SSE)
│   │   ├── search.py           # POST /search
│   │   ├── stats.py            # GET /stats
│   │   └── feedback.py         # GET/POST /feedback/*
│   ├── services/               # Business logic
│   │   ├── build_service.py    # Static site generation (the big one)
│   │   ├── editor_ai_actions.py# AI prompt construction
│   │   ├── llm/                # LLM provider abstraction
│   │   │   ├── base.py
│   │   │   ├── openai_provider.py
│   │   │   ├── hermes_provider.py
│   │   │   └── config.py
│   │   └── _static/            # Static assets copied into builds
│   ├── utils/                  # Helpers
│   │   ├── auth.py             # JWT + password hashing
│   │   └── ...
│   └── scripts/                # Standalone scripts
│       └── seed_demo.py
├── tests/                      # pytest test files
├── alembic/                    # Database migrations
├── scripts/                    # Shell scripts (start-backend.sh, etc.)
├── requirements.txt
└── Dockerfile
```

### Request Lifecycle

A typical API request goes through:

1. **CORS middleware** (allow frontend origin)
2. **Authentication middleware** (extract JWT, attach user)
3. **Rate limiter** (Redis-backed, 300 req/min/IP default)
4. **Route handler** in `routers/`
5. **Pydantic validation** (request body)
6. **Database query** via `Depends(get_db)`
7. **Service layer** for business logic
8. **Response serialization** via Pydantic

Example: `GET /api/v1/projects`

```python
@router.get("", response_model=ApiResponse)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch user's projects
    result = await db.execute(
        select(Project)
        .where(Project.created_by == current_user.id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return {"data": [ProjectOut.from_orm(p) for p in projects]}
```

### Authentication

- **JWT tokens** with HS256 signing
- **Token lifetime**: 7 days (configurable in `.env` via `JWT_EXPIRE_MINUTES`)
- **Refresh**: Re-login (no refresh token flow in v0.1.0)
- **Password hashing**: bcrypt via passlib (4.2.1)

Login flow:
1. `POST /auth/login` with email + password
2. Backend verifies password hash
3. Backend creates JWT with user ID + role
4. Frontend stores JWT in `localStorage`
5. Frontend sends JWT in `Authorization: Bearer <token>` for all subsequent requests

### AI Integration

OpenDocX uses a **provider abstraction** for LLMs:

```python
# app/services/llm/base.py
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages, **kwargs) -> str: ...

    @abstractmethod
    def stream(self, messages, **kwargs) -> AsyncGenerator[str, None]: ...

# app/services/llm/openai_provider.py
class OpenAIProvider(LLMProvider):
    """Works with any OpenAI-compatible API"""
    async def stream(self, messages, **kwargs):
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk = json.loads(line[6:])
                        if chunk.get("choices"):
                            yield chunk["choices"][0]["delta"].get("content", "")
```

The `OpenAIProvider` works with:
- OpenAI official (`https://api.openai.com/v1`)
- Azure OpenAI
- Local Ollama (`http://localhost:11434/v1`)
- Xiaomi mimo (`https://token-plan-cn.xiaomimimo.com/v1`)
- Any other OpenAI-compatible service

Configuration in `.env`:
```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
LLM_API_KEY=***
L...# At startup, we validate:
```python
class LLMConfig:
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("LLM_API_KEY is required")
        if self.api_key in ("***", "sk-test"):
            raise ValueError("LLM_API_KEY is still a placeholder")
        if len(self.api_key) < 20:
            raise ValueError("LLM_API_KEY is too short")
```

This fail-fast catches config errors at startup, not at first request.

### Static Site Generation

The `build_service.py` is the heart of OpenDocX - it transforms database documents into static HTML.

**Pipeline:**

1. **Fetch all published documents** for a version
2. **Build the sidebar tree** from document hierarchy
3. **For each document**:
   a. Parse Markdown with mistune
   b. Post-process code blocks with pygments
   c. Extract Mermaid blocks for client-side rendering
   d. Process admonitions (`> [!NOTE]` etc.)
   e. Generate TOC (table of contents) from headings
4. **Write index.html** (landing page)
5. **Write one HTML per document** at `docs/<slug>/index.html`
6. **Copy static assets** (`tokens.css`, `main.css`, images)
7. **Generate sitemap.xml**

The output is a **fully static, zero-dependency** site. No JS framework runs in the browser. No API calls. Just HTML + CSS + a small bit of JS for the search and theme toggle.

---

## Frontend Architecture

### Project Structure

```
frontend/
├── src/
│   ├── main.tsx                # Entry point
│   ├── App.tsx                 # Root component + routing
│   ├── pages/                  # Route components
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Projects.tsx
│   │   ├── ProjectOverview.tsx
│   │   ├── Documents.tsx
│   │   ├── Published.tsx
│   │   ├── Settings.tsx
│   │   ├── AdminUsers.tsx
│   │   ├── AdminAudit.tsx
│   │   └── AdminFeedbacks.tsx
│   ├── components/             # Reusable components
│   │   ├── Editor/
│   │   │   ├── AIFloatingActions.tsx
│   │   │   ├── PreBuildModal.tsx
│   │   │   └── ...
│   │   ├── CommandPalette.tsx
│   │   ├── FolderOverview.tsx
│   │   ├── StatusBadges.tsx
│   │   └── ...
│   ├── services/               # API clients
│   │   ├── api.ts              # Main REST client
│   │   └── editorApi.ts        # Editor-specific (SSE)
│   ├── types/                  # TypeScript types
│   │   └── api.ts
│   ├── styles/                 # Global CSS
│   │   ├── tokens.css          # Design tokens (colors, spacing)
│   │   ├── ai-floating.css
│   │   └── ...
│   ├── i18n/                   # Internationalization
│   │   ├── en.json
│   │   └── zh.json
│   └── utils/                  # Helpers
├── public/                     # Static assets served as-is
├── index.html                  # HTML entry
├── vite.config.ts              # Vite config (port 3077, /api proxy)
├── package.json
├── tsconfig.json
├── Dockerfile
└── nginx.conf                  # Production nginx config
```

### Routing

OpenDocX uses **React Router 6** with the following routes:

| Path | Component | Auth |
|---|---|---|
| `/login` | Login | Public |
| `/` | Dashboard | Required |
| `/projects` | Projects list | Required |
| `/projects/:id` | ProjectOverview | Required |
| `/projects/:id/docs` | Documents editor | Required |
| `/projects/:id/published` | Published | Required |
| `/settings` | Settings | Required |
| `/admin/users` | AdminUsers | Admin only |
| `/admin/audit` | AdminAudit | Admin only |
| `/admin/feedbacks` | AdminFeedbacks | Admin only |

### State Management

Most state is **local to components** (useState, useReducer). Global state uses **Zustand**:

```typescript
// stores/user.ts
import { create } from 'zustand';
export const useUserStore = create<UserState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  logout: () => set({ user: null }),
}));
```

We chose Zustand over Redux for simplicity - most state is server-state (fetched via React Query / SWR pattern, but we use plain `useEffect` + `useState` for now).

### Styling

- **Ant Design 5** for most components
- **CSS Modules** for component-specific styles
- **Global tokens** in `tokens.css` (colors, spacing, font sizes)
- **No CSS-in-JS** (we tried `styled-components` early but reverted - it conflicted with Ant Design's theming)

### Build Output

- `npm run build` produces `frontend/dist/`:
  - `dist/index.html` - entry
  - `dist/assets/*.js` - bundled JS (code-split by route)
  - `dist/assets/*.css` - bundled CSS
  - ~1 MB total (gzipped: ~300 KB)

In production, `dist/` is served by Nginx (see `frontend/nginx.conf`).

---

## Data Model

### Core Entities

```
users
  id (uuid, PK)
  email (unique, indexed)
  name
  password_hash
  role (admin | editor | viewer)
  is_active
  last_login_at
  created_at, updated_at

projects
  id (uuid, PK)
  name
  slug (unique, indexed)
  description
  brand_color (hex)
  logo_url
  status (active | paused | draft | archived)
  created_by (FK -> users.id)
  created_at, updated_at

versions
  id (uuid, PK)
  project_id (FK -> projects.id, cascade)
  version (string, e.g., "v1.0")
  is_default (boolean)
  status (draft | published | archived)
  created_at

documents
  id (uuid, PK)
  version_id (FK -> versions.id, cascade)
  parent_id (FK -> documents.id, nullable, for folder hierarchy)
  title
  slug
  content (markdown text)
  file_path
  status (draft | published | archived)
  sort_order
  created_by (FK -> users.id)
  created_at, updated_at

feedback
  id (uuid, PK)
  document_id (FK -> documents.id, cascade)
  visitor_id (string, anonymous)
  type (like | comment)
  content
  created_at

audit_logs
  id (uuid, PK)
  actor_id (FK -> users.id, nullable for anonymous)
  actor_email
  action (string, e.g., "user.create", "document.delete")
  resource_type
  resource_id
  changes (JSON, before/after)
  ip_address
  created_at

build_logs
  id (uuid, PK)
  version_id (FK -> versions.id)
  status (pending | running | success | failed)
  output_path
  duration_seconds
  error_message
  created_at

document_embeddings
  id (uuid, PK)
  document_id (FK -> documents.id, cascade)
  chunk_index
  chunk_text
  embedding (vector(1024)) -- BAAI/bge-m3 is 1024-dim
  created_at
  INDEX (embedding vector_cosine_ops) -- pgvector HNSW index
```

### Why This Design?

- **UUIDs instead of auto-increment IDs**: harder to enumerate, can be generated client-side
- **Soft delete via `is_active` / `status`**: never lose data, easy to recover
- **Audit log for every mutation**: required for compliance, debugging
- **Separate `versions` table**: allows multiple parallel doc states (draft + stable)
- **Document hierarchy via `parent_id`**: simple adjacency list, sufficient for typical doc trees

### Migrations

We use **Alembic** for schema migrations:

```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "add audit_logs"
alembic upgrade head
```

Migrations are version-controlled in `backend/alembic/versions/`.

---

## API Design Principles

### REST Conventions

- **Resource-based URLs**: `/projects`, `/projects/{id}/documents`
- **HTTP methods**: GET (read), POST (create), PUT (update), DELETE (remove)
- **Status codes**: 200 (OK), 201 (created), 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 422 (validation error), 500 (server error)
- **JSON request and response bodies** (no form data except file uploads)
- **Snake_case in JSON**: `created_at` not `createdAt`

### Response Envelope

All responses use a standard envelope:

```json
{
  "success": true,
  "data": { ... },
  "message": null
}
```

For errors:

```json
{
  "success": false,
  "data": null,
  "message": "User not found",
  "error_code": "USER_NOT_FOUND"
}
```

This makes error handling consistent on the frontend.

### Authentication

All non-public endpoints require:

```
Authorization: Bearer <jwt_token>
```

The JWT is verified by `Depends(get_current_user)`, which extracts the user from the token and attaches it to the request.

### Pagination

For list endpoints, we use **offset-based pagination**:

```json
GET /api/v1/documents?offset=0&limit=20
{
  "success": true,
  "data": {
    "items": [...],
    "total": 142,
    "offset": 0,
    "limit": 20,
    "has_more": true
  }
}
```

For very large datasets, consider cursor-based pagination (not implemented in v0.1.0).

### File Uploads

Use `multipart/form-data` for file uploads (Markdown files, images):

```python
@router.post("/documents/import")
async def import_documents(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    for file in files:
        content = await file.read()
        # ... process
```

File size limit: 10 MB per file (configurable in Nginx).

---

## Security

### Authentication Security

- **bcrypt** for password hashing (via passlib)
- **JWT** with HS256, 7-day expiry
- **HTTPS required** in production (self-signed OK for local dev)
- **CORS** configured per environment (not `*` in production)

### Authorization

- **Role-based**: admin / editor / viewer
- **Resource-based**: Some actions (delete own feedback) don't require admin
- **Row-level security**: User can only edit their own projects (unless admin)

### Input Validation

- **Pydantic** for all request body validation
- **SQLAlchemy parameterized queries** (no string concatenation)
- **HTML sanitization** via bleach (in static site generation)
- **Markdown escape** via mistune (escapes raw HTML by default)

### Rate Limiting

- **300 requests per minute per IP** (configurable)
- **Redis-backed** for multi-instance deployment
- **Bypass for authenticated admin** (so admins don't get throttled)

### Data Protection

- **`.env` never committed** to git
- **Passwords hashed** (never stored in plain text)
- **JWT secret** rotated periodically
- **API keys** for LLM services stored in `.env` only
- **Database backups** recommended daily (not automated in v0.1.0)

### Known Security Considerations

- **LLM prompt injection**: User content is concatenated into prompts - we use system prompts to constrain, but a determined attacker could bypass. Future: structured prompt templates.
- **Markdown XSS**: We use `mistune.escape=True` and `bleach.clean()` to sanitize. No known bypasses.
- **JWT expiration**: Default 7 days. Long-lived sessions are a risk - consider refresh tokens in v0.2.0.

See [SECURITY.md](../SECURITY.md) for vulnerability reporting.

---

## Performance

### Backend Performance

- **Async-first** with FastAPI + asyncpg
- **Connection pooling**: 10 connections + 20 overflow
- **Database indexes**: on all foreign keys, slug, email
- **Vector index**: HNSW on `document_embeddings.embedding` for fast KNN

Typical response times (local dev):
- Simple GET: 5-20 ms
- List with pagination: 20-50 ms
- Vector search (k=10): 50-200 ms
- Build (50 docs): 10-20 seconds

### Frontend Performance

- **Code splitting** by route (React.lazy)
- **Vite** for fast dev builds
- **Production bundle**: ~1 MB (gzipped: ~300 KB)
- **Initial load**: < 2 seconds on fast 3G

### Static Site Performance

The generated static site is **very fast**:
- **No JS framework runtime** (just a small bit of JS for search + theme)
- **Lazy-loaded images**
- **No external dependencies** (all CSS/JS bundled)
- **CDN-friendly** (can be served from any static host)

Lighthouse score: 95+ on a typical page.

---

## Deployment

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
bash scripts/start-backend.sh  # auto-sources .env

# Frontend (separate terminal)
cd frontend
npm install
npx vite --port 3077
```

### Docker (Production-like)

```bash
# 1. Configure
cp .env.example .env
# Edit .env: set LLM_API_KEY, JWT_SECRET, etc.

# 2. Build and run
docker compose up -d

# 3. Verify
curl http://localhost:3077
curl http://localhost:8001/api/v1/health

# 4. View logs
docker compose logs -f backend
```

### Production Deployment

For production:
1. **Use HTTPS** (Let's Encrypt or your cert provider)
2. **Set strong JWT_SECRET** (`openssl rand -base64 64`)
3. **Use a real PostgreSQL** (not SQLite in dev)
4. **Set up backups** (daily `pg_dump`)
5. **Configure monitoring** (Sentry / DataDog / Grafana)
6. **Run behind a reverse proxy** (Nginx / Caddy / Cloudflare)
7. **Use a process manager** (systemd / supervisord / k8s)

See [docs/deployment/](../docs/deployment/) (TODO) for detailed guides.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](../CONTRIBUTING.md).

Key principles:
- **Real data, no mocks** - every PR must be tested with real API + real DB
- **Root cause first** - in your PR description, explain the actual root cause
- **One commit per fix** - "fix + verify" should be one commit, not two
- **0 emoji in UI text** - use SVG, Chinese, or plain text
- **Document your changes** - update relevant docs in the same PR

---

<sub>Last revised: 2026-06-08 · Version: v0.1.0</sub>
