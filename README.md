<p align="center">
  <img src="Asset/Screvyn_banner.png" alt="Screvyn" width="600" />
</p>

<p align="center">
  Code review on autopilot. Four AI agents. Every pull request.
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;·&nbsp;
  <a href="#how-it-works">How it works</a> &nbsp;·&nbsp;
  <a href="#architecture">Architecture</a> &nbsp;·&nbsp;
  <a href="docs/CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <img src="https://github.com/Vatsalya2003/screvyn_multi-agent-code-review-system/actions/workflows/ci.yml/badge.svg" />
  <img src="https://img.shields.io/badge/tests-174_passing-brightgreen" />
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue" />
</p>

---

Screvyn runs four specialist AI agents on every pull request — security, performance, code quality, and architecture — in parallel. Findings are ranked P0/P1/P2, posted directly on the PR with explanations and fixes, and fanned out to Teams and email. The whole thing takes about 25 seconds.

It's not a wrapper around a single LLM call. Each agent has its own system prompt, its own focus area, and its own failure boundary. If one agent hits a rate limit, the other three still deliver. The AST parser (tree-sitter) gives agents structural context — functions, classes, imports, line ranges — so they produce specific findings, not generic advice.

<p align="center">
  <img src="Asset/screvyn-pr-review.png" alt="Screvyn reviewing a pull request" width="680" />
</p>

---

## Quick start

You need Python 3.12+, a [Gemini API key](https://aistudio.google.com/apikey) (free tier), and an [Upstash Redis](https://upstash.com) instance (free tier).

```bash
git clone https://github.com/Vatsalya2003/screvyn_multi-agent-code-review-system.git
cd screvyn_multi-agent-code-review-system/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your keys
pytest tests/ -v        # 174 tests, <3 seconds
```

Start the server:

```bash
# terminal 1
celery -A celery_app worker --loglevel=info --concurrency=2

# terminal 2
uvicorn main:app --reload --port 8000
```

Try a review:

```bash
curl -s -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"code": "import sqlite3\ndef get_user(uid):\n    return sqlite3.connect(\"db\").execute(f\"SELECT * FROM users WHERE id={uid}\")", "language": "python"}' \
  | python -m json.tool
```

You'll get back a JSON response with severity-ranked findings, flagged code, and fixes.

For automatic PR reviews, set up a [GitHub App](docs/GITHUB_APP_SETUP.md) and point the webhook at your server. Screvyn verifies the HMAC signature, enqueues a Celery task, and posts the review as a PR comment — all within 30 seconds of the push.

---

## How it works

```
PR opened
  → GitHub sends webhook (HMAC-SHA256 signed)
  → FastAPI verifies signature, checks rate limit, returns 202
  → Celery worker picks up the job from Redis

Worker:
  → Fetches changed files via GitHub API
  → tree-sitter parses each file into an AST
  → LangGraph runs 4 agents in parallel:
      Security     — OWASP Top 10, leaked secrets, injections
      Performance  — N+1 queries, O(n²), memory leaks, blocking calls
      Code smell   — dead code, god classes, magic numbers, naming
      Architecture — SOLID violations, coupling, missing patterns

  → Severity aggregator deduplicates and ranks findings P0/P1/P2
  → Comment posted on the PR
  → Teams notification sent (Adaptive Card)
  → Email sent for P0/P1 findings (via Resend)
  → Review saved to Firebase Firestore
```

The webhook responds in under 200ms. The full review takes 20–30 seconds depending on file count and Gemini response times. If an agent fails (rate limit, timeout, parse error), the others continue — partial results always ship.

---

## Architecture

<p align="center">
  <img src="Asset/screvyn_full_architecture.svg" alt="Architecture" width="680" />
</p>

### Stack

| What | Tech | Why |
|---|---|---|
| API server | FastAPI | async, Pydantic validation, auto docs at `/docs` |
| LLM | Gemini 2.5 Flash | free tier, fast, structured JSON output |
| Agent orchestration | LangGraph | parallel execution with typed shared state |
| Code parsing | tree-sitter | same parser VS Code uses, error-tolerant |
| Job queue | Celery + Upstash Redis | async processing so GitHub never times out |
| GitHub integration | GitHub App (JWT) | bot identity, installation tokens, webhook HMAC |
| Rate limiting | Redis INCR + EXPIRE | atomic counters, per-repo, per-month |
| Notifications | Teams webhooks, Resend | Adaptive Cards, HTML email for P0/P1 only |
| Storage | Firebase Firestore | review history, repo stats |
| CI | GitHub Actions | tests + gitleaks on every push |

### Agents

Each agent receives the raw code plus an AST context string (extracted functions, classes, imports with line ranges). Each has a separate system prompt tuned for its domain. All four run simultaneously via LangGraph's parallel node execution.

| Agent | Focus | Example finding |
|---|---|---|
| Security | OWASP Top 10, secrets, injection, auth bypass | SQL injection via f-string in `get_user` (line 12) |
| Performance | N+1, complexity, memory, blocking calls | 1000 users = 1001 DB queries in `get_all_orders` |
| Code smell | dead code, duplication, naming, magic numbers | `0.15` on line 36 — use `PREMIUM_DISCOUNT` |
| Architecture | SOLID, coupling, missing abstractions | `UserManager` handles DB, email, validation, and logging |

### Severity

| Level | Tag | Meaning |
|---|---|---|
| P0 | `blocking` | must fix before merge — security vulns, data loss |
| P1 | `important` | should fix before merge — perf issues, design violations |
| P2 | `nit` | fix when convenient — style, minor improvements |

The aggregator deduplicates findings from different agents that flag the same code region (50% line overlap + 60% title similarity). The highest severity wins. PR comments cap at 7 findings shown — all P0s always appear, remaining slots filled by P1 then P2.

---

## Project layout

```
backend/
├── main.py                          # FastAPI app, health check, /api/review
├── celery_app.py                    # Celery config, Redis broker, SSL setup
├── agents/
│   ├── orchestrator.py              # LangGraph graph, parallel fan-out + merge
│   ├── security_agent.py
│   ├── performance_agent.py
│   ├── smell_agent.py
│   └── architecture_agent.py
├── core/
│   ├── ast_parser.py                # tree-sitter: Python, JS, Java
│   ├── config.py                    # settings dataclass, env vars
│   ├── firebase_client.py           # Firestore CRUD + repo stats
│   ├── github_client.py             # JWT auth, fetch files, post comments
│   ├── llm_client.py                # Gemini wrapper, JSON extraction, retries
│   ├── rate_limiter.py              # Redis INCR, fail-open on error
│   ├── review_style.py              # tone rules shared across agents
│   └── severity.py                  # dedup, merge, sort by severity
├── notifications/
│   ├── github_comment_formatter.py  # Markdown PR comment
│   ├── dispatcher.py                # fan-out: Teams + email + Firestore
│   ├── teams.py                     # Adaptive Card builder + sender
│   └── email_notify.py              # Resend HTML, P0/P1 only
├── routers/
│   ├── reviews.py                   # POST /api/review
│   └── webhook.py                   # POST /api/webhook, HMAC verify
├── tasks/
│   └── review_task.py               # Celery task: full pipeline
└── tests/                           # 174 tests, <3s, zero external deps
    ├── test_models.py
    ├── test_ast_parser.py
    ├── test_agents.py
    ├── test_orchestrator.py
    ├── test_severity.py
    ├── test_github_comment.py
    ├── test_rate_limiter.py
    ├── test_webhook.py
    ├── test_notifications.py
    └── test_firebase.py
```

---

## API

**`POST /api/review`** — paste code, get findings back.

```bash
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"code": "your code", "language": "python"}'
```

Returns findings array with severity, explanation, flagged code, and fix for each.

**`POST /api/webhook`** — receives GitHub `pull_request` events, verifies HMAC-SHA256 signature, enqueues async review. Returns `202 Accepted`.

**`GET /`** — health check.

---

## Environment variables

```bash
# required
GEMINI_API_KEY=your_gemini_key
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# GitHub App (for PR reviews)
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=./your-app.private-key.pem
GITHUB_WEBHOOK_SECRET=your_secret
GITHUB_INSTALLATION_ID=12345678

# notifications (optional)
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxx
RESEND_API_KEY=re_xxx
FIREBASE_PROJECT_ID=your-project
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
```

---

## Contributing

The easiest way to contribute:

- **Add a language** — tree-sitter supports 50+ languages. Adding one takes ~15 minutes: install the grammar, map node types in `ast_parser.py`, add a test fixture.
- **Improve agent prompts** — better examples in system prompts = better findings. Test with `pytest tests/test_agents.py`.
- **Add a notification channel** — Discord, Slack, PagerDuty. The dispatcher pattern makes this a single-file addition.
- **Report false positives** — open an issue with the code snippet and the incorrect finding.

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for local setup instructions.

---

## Roadmap

- [x] Gemini integration, Pydantic models, structured JSON parsing
- [x] Security agent with OWASP-focused prompts
- [x] tree-sitter AST parser (Python, JavaScript, Java)
- [x] 4 parallel agents via LangGraph
- [x] Severity aggregator with deduplication
- [x] Celery + Redis async queue, GitHub webhook, PR comments
- [x] Teams + Email notifications, Firebase storage
- [ ] Next.js dashboard with review history and severity trends
- [ ] VS Code extension (review on save)
- [ ] Slack Block Kit notifications
- [ ] Additional languages (Go, Rust, TypeScript)

---

## License

[AGPL-3.0](LICENSE). Free for personal and open-source use. If your company modifies Screvyn and deploys it internally without open-sourcing the changes, you need a commercial license — [get in touch](mailto:vatsalya@screvyn.dev).

---

<p align="center">
  Built by <a href="https://github.com/Vatsalya2003">Vatsalya Dabhi</a>
</p>
