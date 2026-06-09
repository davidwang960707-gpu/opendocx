# OpenDocX Roadmap

> What's done, what's next, and where we're going.
> Last updated: 2026-06-08 · Version: v0.1.0

---

## Project Philosophy

OpenDocX exists because **writing documentation is hard, and most tools make it harder**.

Our principles:
- **AI is a tool, not a replacement** - we help you write, not write for you
- **Web-native** - no Git, no local files, no command line required
- **Real-time collaboration-ready** - the data model supports it (multi-version, audit log)
- **Open by default** - Apache 2.0 licensed, no enterprise tier

---

## Current Status: v0.1.0 (Released)

**v0.1.0** is the first public release. It includes:
- All core features (Markdown editor, AI integration, build & publish)
- Pre-Build Confirmation modal (v0.1.0 innovation)
- Selection-aware AI Q&A (v0.1.0 innovation)
- Full admin panel with audit logs
- Docker Compose for one-command setup
- 58+ screenshots, complete user guide

**Code stats (v0.1.0):**
- 6,567 lines Python backend
- 8,897 lines TypeScript frontend
- 10 backend test files
- 80 commits in the main branch
- 11 projects / 73+ HTML files generated

---

## Short-term (v0.2.0 - Q3 2026)

### Static Site AI Features

**Goal**: Bring AI capabilities to the published static site, not just the editor.

- **AI chat widget** in the bottom-right of the static site
- **Per-page "explain this"** button
- **AI-powered search** with semantic ranking
- **Visitor feedback collection** (already in editor, extend to static site)

**Why this matters**: Currently OpenDocX helps authors write. After publishing, readers have no AI help. We're closing that gap.

**Estimated effort**: 1 month

### Live Demo URL

**Goal**: A public URL where anyone can try OpenDocX without installing.

- Deploy to Vercel (frontend) + Railway (backend) + Supabase (PostgreSQL)
- Free tier for everyone
- Custom domain `demo.opendocx.dev`

**Why this matters**: The #1 reason people don't try open source projects is friction. A live demo removes that.

**Estimated effort**: 1 week

### Hacker News Launch

**Goal**: Get on Hacker News front page.

- Write a "Show HN" post: "Show HN: OpenDocX - Open-source AI-native doc platform"
- Target: top 10 of the day
- Expected: 500-2000 stars in 1 week

**Why this matters**: Distribution > development. We've built the product; now we need users.

**Estimated effort**: 1 day (post + landing page prep)

### Better Search

**Goal**: Move from basic embedding search to hybrid (keyword + semantic).

- Add BM25 keyword search (Postgres `ts_vector`)
- Combine with vector search using reciprocal rank fusion
- Highlight matched terms

**Why this matters**: Vector search alone misses exact technical terms. Hybrid is the proven approach.

**Estimated effort**: 1 week

---

## Medium-term (v0.3.0 - Q4 2026)

### MDX Support

**Goal**: Allow JSX in Markdown.

- Parse MDX (Markdown + JSX)
- Sandbox component execution
- Provide pre-built components (`<Note>`, `<Warning>`, `<YouTubeEmbed>`)
- Allow user-defined components via project config

**Why this matters**: MDX is Docusaurus's killer feature. We're behind on this.

**Estimated effort**: 3 weeks

### Real-time Collaboration

**Goal**: Multiple users editing the same document at the same time.

- Operational Transform (OT) or CRDT (Yjs)
- Show other users' cursors
- Live character-level sync

**Why this matters**: The #1 user request (in informal feedback) is "can I collaborate with my team?"

**Estimated effort**: 2 months (this is hard)

### Workflow Improvements

**Goal**: Support real editorial workflows.

- Document review / approval
- Comment threads
- Track changes (like Microsoft Word)
- Lock documents when someone is editing

**Estimated effort**: 1 month

### Performance: Build Time

**Goal**: Build 200-doc projects in under 10 seconds.

- Parallel document processing
- Cache Mermaid renders
- Incremental builds (only changed docs)

**Estimated effort**: 2 weeks

---

## Long-term (v1.0 - 2027)

### v1.0 Quality Bar

For v1.0, we want:
- **1000+ GitHub stars**
- **10+ real external users** running OpenDocX in production
- **99.9% uptime** for the demo URL (monitored)
- **Complete API stability** (no breaking changes after v1.0)
- **Comprehensive documentation** (all features documented)
- **Performance budgets** met (build < 10s for 200 docs, p99 API < 200ms)

### v1.0+ Features

- **Multi-tenant**: One OpenDocX instance, many organizations
- **SSO**: OAuth, SAML, OIDC
- **Audit log export**: For compliance audits
- **Webhooks**: Notify external systems on document changes
- **API rate limits per user**: Not just per IP
- **GraphQL API**: As alternative to REST
- **Mobile app**: iOS + Android (read-only first)

### Vision: AI-First Documentation

Long-term, we believe documentation should be:
- **Conversational**: Chat with your docs, not just read
- **Predictive**: AI suggests what to document next based on code changes
- **Multi-modal**: Images, video, interactive demos, not just text
- **Auto-maintained**: AI keeps docs in sync with code (the holy grail)

We're not there yet, but every release moves us closer.

---

## Why Not Compete With Docusaurus?

We don't. Docusaurus is the **authoring tool of choice** for mature file-based static sites. OpenDocX is the **documentation and publishing workspace for AI-built projects**.

Our positioning: "Use Docusaurus if you already have a Git-native docs workflow. Use OpenDocX if your AI-built project needs manuals, publishing, feedback, and handoff workflows."

Read our full [competitive analysis](OpenDocX-vs-Docusaurus-对标报告-2026-06-08.md) (1万字, 7段, 10458 bytes).

---

## Feature Comparison

| Feature | OpenDocX v0.1.0 | Docusaurus 3.x | Notion |
|---|---|---|---|
| Markdown editor in browser | Yes | No (file-based) | Yes |
| AI floating tip on selection | Yes | Plugin needed | Yes (Notion AI) |
| Pre-Build Confirmation modal | Yes (v0.1.0) | No | N/A |
| Build to static site | Yes | Yes (its main feature) | No |
| Multi-version support | Yes | Yes | N/A |
| Full-text search | Basic (embedding) | Algolia (free tier) | Yes |
| Multi-language | Per-project | Native | Yes |
| Database-driven | Yes (PostgreSQL) | No (Markdown files) | Yes |
| Audit logs | Yes (all admin actions) | No | Yes |
| Real-time collaboration | No (planned v0.3.0) | No (planned) | Yes |
| MDX / JSX | No (planned v0.3.0) | Yes | No |
| Open source | Apache 2.0 | MIT | No (proprietary) |

---

## Success Metrics (v1.0 Goals)

| Metric | Target | Current (v0.1.0) |
|---|---|---|
| GitHub stars | 1000+ | 0 (not yet launched) |
| Active installations | 50+ | 0 |
| External contributors | 10+ | 0 |
| Production users (in business) | 5+ | 0 |
| Public demo uptime | 99.9% | N/A |
| Issues closed per month | 30+ | N/A |

---

## Decision Log

Major decisions and their rationale:

### Why Apache 2.0 over MIT?

- Explicit patent grant protects users from infringement claims
- NOTICE file requirement enables clean attribution chains
- Trademark clause lets us protect "OpenDocX" brand for future commercial use
- Mirrors TensorFlow, Kubernetes, Angular - the established AI/cloud norm

### Why PostgreSQL + pgvector over a dedicated vector DB?

- One less service to operate
- pgvector's HNSW index is competitive with Pinecone for our scale
- We can use the same DB for transactions and vectors (atomicity)
- Future-proof: can scale to dedicated vector DB later if needed

### Why React over Vue/Svelte?

- Largest ecosystem (we need Ant Design's breadth)
- Most hires know React
- Server components not needed (we're a SPA)
- Future: Can add Next.js for SSR if needed

### Why FastAPI over Django/Flask?

- Async-first (better for AI streaming responses)
- Auto OpenAPI docs (free, accurate)
- Pydantic integration is excellent
- Type hints everywhere

### Why a Pre-Build Modal?

- We saw users click "Build" then realize they forgot to publish drafts
- Catching the error **before** the build is much better UX than after
- Inspired by code review tools that show diffs before applying

### Why Selection-Aware AI Q&A?

- Users asked "what's in this paragraph?" expecting paragraph-level answer
- Without selection, the AI would answer the whole document (confusing)
- We modified the prompt template to constrain to the selection

---

## Contributing to the Roadmap

We welcome input! Open an issue with:
1. The user pain point (concrete scenario, not "it would be nice if...")
2. The proposed solution (specific, actionable)
3. Alternative solutions considered
4. Your willingness to implement

For major changes (new feature, API change), please open a RFC issue first (we have a template for it).

---

## License

Apache 2.0 - see [LICENSE](../LICENSE).

---

<sub>Last revised: 2026-06-08 · Version: v0.1.0</sub>
