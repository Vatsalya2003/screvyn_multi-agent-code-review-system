# Screvyn Frontend — Complete Design & Build Spec

## Project setup

```
Tech: Next.js 15 (App Router) + TypeScript + Tailwind CSS v4
Directory: frontend/ (inside screvyn_multi-agent-code-review-system/)
Created with: npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir
```

**Tailwind v4 note:** This project uses Tailwind CSS v4.2+. Custom colors are defined via `@theme` in `globals.css`, NOT in `tailwind.config.ts`. Delete `tailwind.config.ts` if it exists — v4 doesn't use it.

---

## Brand & Design System

### Color palette

**Light theme (landing page):**
```
Background:     #F5F0EB (warm cream)
Surface:        #FDFBF8 (lighter cream)
Border:         #DDD8D0 (warm gray)
Text primary:   #2D2D2D (soft black)
Text secondary: #777777 (medium gray)
Text muted:     #999999 (light gray)
CTA button:     #1A1A1A bg, #F5F0EB text
Outline button: #C8C0B8 border, #2D2D2D text
```

**Dark theme (dashboard, review page):**
```
Background:     #080808 (near black)
Surface:        #0D0D0D (card bg)
Surface raised: #141414 (input bg, hover)
Border:         rgba(85,85,85,0.2) (subtle)
Text primary:   #F5F0EB (cream)
Text secondary: #999999 (muted)
Text muted:     #555555 (hint)
```

**Severity colors:**
```
P0 (blocking):   #E24B4A (red)
P1 (important):  #EF9F27 (amber)
P2 (nit):        #B8B0A8 (warm gray)
```

**Agent colors:**
```
Security:     #7F77DD (purple)
Performance:  #1D9E75 (teal)
Code smell:   #D85A30 (coral)
Architecture: #378ADD (blue)
```

### Typography
```
Font family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", system-ui, sans-serif
Mono font:   "SF Mono", "Fira Code", monospace

Hero heading:    56px, font-weight 600, letter-spacing -2px, line-height 1.08
Section heading: 36px, font-weight 600, letter-spacing -1px
Card heading:    15px, font-weight 500
Body text:       15-16px, font-weight 400
Small/label:     12-13px
Tiny:            10-11px
```

### Design principles
- **Apple-minimal:** Lots of whitespace, no noise, every element earns its space
- **No gradients, no shadows** (except subtle card borders)
- **Rounded corners:** 8px for small elements, 12px for cards, 20-24px for buttons/pills
- **Animations:** Only hover transitions (colors, opacity). No page animations.
- **Two themes:** Landing page = cream/light. Dashboard + Review = dark.

---

## Tailwind v4 globals.css

```css
@import "tailwindcss";

@theme {
  --color-cream-50: #FDFBF8;
  --color-cream-100: #F5F0EB;
  --color-cream-200: #EDE6DD;
  --color-cream-300: #DDD8D0;
  --color-cream-400: #C8C0B8;
  --color-cream-500: #B8B0A8;

  --color-ink-50: #F5F5F5;
  --color-ink-100: #E0E0E0;
  --color-ink-200: #999999;
  --color-ink-300: #777777;
  --color-ink-400: #555555;
  --color-ink-500: #2D2D2D;
  --color-ink-600: #1A1A1A;
  --color-ink-700: #141414;
  --color-ink-800: #0D0D0D;
  --color-ink-900: #080808;

  --color-severity-p0: #E24B4A;
  --color-severity-p1: #EF9F27;
  --color-severity-p2: #B8B0A8;

  --color-agent-security: #7F77DD;
  --color-agent-performance: #1D9E75;
  --color-agent-smell: #D85A30;
  --color-agent-architecture: #378ADD;
}

@layer base {
  html { color-scheme: light; scroll-behavior: smooth; }
  body {
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
}
```

If Tailwind v4 custom colors don't generate utility classes, use inline styles with the hex values directly. Better to have a working site than fight the toolchain.

---

## File structure

```
frontend/src/
├── app/
│   ├── globals.css              # Tailwind v4 theme + base styles
│   ├── layout.tsx               # Root layout (just html + body + metadata)
│   ├── page.tsx                 # Landing page (cream/light theme)
│   ├── review/
│   │   └── page.tsx             # Paste code → get review (dark theme)
│   ├── dashboard/
│   │   ├── layout.tsx           # Dashboard shell (sidebar + topbar, dark)
│   │   ├── page.tsx             # Overview with metrics + charts
│   │   ├── reviews/
│   │   │   └── page.tsx         # Review history list
│   │   └── settings/
│   │       └── page.tsx         # Webhook + notification config
│   └── not-found.tsx            # 404 page
├── components/
│   ├── landing/
│   │   ├── Navbar.tsx
│   │   ├── Hero.tsx
│   │   ├── TerminalPreview.tsx
│   │   ├── AgentCards.tsx
│   │   ├── HowItWorks.tsx
│   │   └── CTA.tsx
│   ├── dashboard/
│   │   ├── Sidebar.tsx
│   │   ├── TopBar.tsx
│   │   ├── MetricCard.tsx
│   │   ├── SeverityBar.tsx
│   │   ├── AgentPerformance.tsx
│   │   ├── WeeklyChart.tsx
│   │   ├── ReviewTable.tsx
│   │   └── QuickActions.tsx
│   ├── review/
│   │   ├── CodeEditor.tsx       # Textarea or Monaco wrapper
│   │   ├── FindingCard.tsx
│   │   └── SeverityBadge.tsx
│   └── shared/
│       ├── Logo.tsx
│       └── LoadingSpinner.tsx
├── lib/
│   ├── api.ts                   # Backend API client
│   └── types.ts                 # TypeScript interfaces
└── public/
    └── assets/
        ├── screvyn-banner.png   # Wide logo
        └── screvyn-icon.png     # Square icon
```

---

## API integration

Backend runs at `http://localhost:8000` (dev) or via env var `NEXT_PUBLIC_API_URL`.

### POST /api/review — manual review
```typescript
// Request
{ code: string, language: "python" | "javascript" | "java" }

// Response
{
  repo: string,
  findings: Finding[],
  p0_count: number,
  p1_count: number,
  p2_count: number,
  agents_completed: string[],
  agents_failed: string[],
  review_duration_seconds: number
}
```

### TypeScript interfaces (lib/types.ts)
```typescript
export interface Finding {
  type: "security" | "performance" | "smell" | "architecture";
  severity: "P0" | "P1" | "P2";
  title: string;
  line_range: string;
  explanation: string;
  flagged_code: string;
  fixed_code: string;
  owasp_ref?: string;
  complexity_before?: string;
  complexity_after?: string;
  pattern_suggestion?: string;
}

export interface ReviewResponse {
  repo: string;
  findings: Finding[];
  p0_count: number;
  p1_count: number;
  p2_count: number;
  agents_completed: string[];
  agents_failed: string[];
  review_duration_seconds: number;
}

export interface ReviewHistory {
  id: string;
  repo: string;
  pr_number: number;
  pr_title: string;
  pr_author: string;
  findings_count: number;
  p0_count: number;
  p1_count: number;
  p2_count: number;
  duration_seconds: number;
  created_at: string;
}
```

---

## Page-by-page specs

### 1. Landing page (`/`)

**Theme:** Cream/light (#F5F0EB background)

**Sections in order:**
1. **Navbar** — Logo (S icon + "Screvyn"), nav links (How it works, Agents, GitHub), Dashboard button (dark pill)
2. **Hero** — Pill badge "CODE REVIEW ON AUTOPILOT", big 56px heading "Every pull request. Reviewed by AI. Before a human looks.", subtitle paragraph, two buttons (Try a review = dark pill, View on GitHub = outline pill)
3. **Terminal preview** — Dark rounded card (#1A1A1A bg) showing a real Screvyn review output with colored severity labels (blocking = red, important = amber, nit = gray), flagged code in red tint, fix code in green tint, footer showing agent names + duration
4. **Agent cards** — "Four agents. One review." heading, 4 cards in a row. Each card: colored tint background matching the agent, icon square, agent name, short description. Colors: Security = purple tint, Performance = teal tint, Smell = coral tint, Architecture = blue tint
5. **How it works** — "How it works" heading, 3 numbered steps with dark circle numbers (1, 2, 3), title + description, separated by horizontal lines
6. **CTA block** — Dark rounded card (#1A1A1A), heading "Start reviewing in 5 minutes.", subtitle, cream CTA button
7. **Footer** — Centered "Built by Vatsalya Dabhi"

**Reference vibe:** Apple product page — massive heading, tons of whitespace, one CTA per section

---

### 2. Review page (`/review`)

**Theme:** Dark (#080808 background)

**Layout:** Full-width, two-column split

**Left column:**
- Language selector tabs (python, javascript, java) — pill toggle buttons
- Code textarea (monospace font, dark surface bg, minimal border)
  - Pre-filled with sample vulnerable Python code
  - "Load sample" link to reset
- "Run review" button (cream bg, dark text, full width below textarea)
  - Loading state: "Reviewing... (~25s)" with disabled style
  - Spinner animation while loading

**Right column:**
- "Results" label with severity badge pills
- Empty state: centered gray text "Paste code and click Run review"
- Loading state: spinner + "4 agents analyzing your code..."
- Error state: red-tinted card with error message
- Results state: scrollable list of FindingCard components

**FindingCard component:**
- Dark card with subtle border
- Top: severity badge + agent type label (colored)
- Title (15px, medium weight)
- Explanation (13px, muted color)
- Flagged code block (dark bg, red-tinted mono text)
- Fix code block (dark bg, green-tinted mono text)
- Line number (tiny, muted)

**Top nav:** Logo + "Dashboard →" link

---

### 3. Dashboard overview (`/dashboard`)

**Theme:** Dark (#080808 background)

**Layout:** Sidebar (fixed, 224px wide) + main content

**Sidebar:**
- Logo (cream on dark)
- Nav items with icons: Overview, Reviews, Try review, Settings
- Active state: subtle bg highlight
- Bottom: "← Back to site" link

**Top bar:** Search input (dark surface bg) + user avatar circle

**Main content — Overview page:**

**Row 1 — 4 metric cards:**
- Total reviews (number + % change badge, green if up)
- Total findings (same)
- Avg duration (in seconds)
- P0 this week (count)

Card style: Dark surface bg (#0D0D0D), subtle border, 12px radius
Number: 30px, semibold. Label: 12px, muted. Change badge: tiny pill with arrow

**Row 2 — 3 cards:**
- Severity breakdown: horizontal stacked bar (P0 red, P1 amber, P2 gray) + legend with counts
- Agent findings: 4 horizontal progress bars (one per agent, each in agent color) with name + count
- Weekly chart: vertical bar chart (7 bars for Mon-Sun), highlight best day in green, total count above

**Row 3 — 2 cards:**
- Recent reviews table (spans 2 cols): columns = Repository, Findings (severity badges), Duration, Time. 5 rows. Dropdown for time filter.
- Quick actions card: 3 links styled as dark surface buttons (Paste code, Configure webhooks, View on GitHub)

**Design reference:** Similar to the dark dashboard image shared — dark cards with very subtle borders, colored accent data, clean table layout, small text for labels

---

### 4. Reviews history (`/dashboard/reviews`)

**Theme:** Dark, same shell as dashboard

**Content:**
- Heading "Reviews" + filter dropdown (Last 7 days / 30 days / All time)
- Full-width table: Repository, PR, Findings (severity badges), Agents, Duration, Date
- Each row clickable (future: expand to show findings)
- Pagination at bottom
- Empty state if no reviews

---

### 5. Settings (`/dashboard/settings`)

**Theme:** Dark, same shell as dashboard

**Content:**
- Heading "Settings"
- Sections with cards:

**Webhook configuration:**
- GitHub App status (connected/not connected indicator)
- Webhook URL display (read-only, copy button)

**Notifications:**
- Teams webhook URL input + test button
- Email recipients input
- Resend API status indicator

**Rate limiting:**
- Current usage display (X/50 this month)
- Progress bar showing usage

---

## Component details

### SeverityBadge
```
P0: bg = red/15%, text = red, label = "blocking" or "3 P0"
P1: bg = amber/15%, text = amber, label = "important" or "2 P1"
P2: bg = gray/20%, text = light gray, label = "nit" or "5 P2"
Shape: pill (border-radius 9999px), padding 4px 10px, font-size 11-12px
```

### MetricCard
```
Background: #0D0D0D
Border: 0.5px rgba(85,85,85,0.1)
Border-radius: 12px
Padding: 20px
Label: 12px, #999
Value: 30px, semibold, #F5F0EB
Change badge: tiny pill, green bg for up, red bg for down
```

### Logo
```
Icon: 32px square, #1A1A1A bg (or #F5F0EB on dark), rounded-lg, white "S" centered
Text: "Screvyn", 18px, medium weight, tracking-tight
```

---

## Important implementation notes

1. **Tailwind v4 color classes:** If `bg-cream-100` doesn't work, use `bg-[#F5F0EB]` with arbitrary values. Better to ship than fight the toolchain.

2. **No client-side fetching on dashboard (yet):** Use static/mock data for now. Phase 8 can connect to Firestore later. The important thing is the UI looks professional.

3. **The review page DOES call the real API:** `POST http://localhost:8000/api/review` — this is the interactive demo. Set `NEXT_PUBLIC_API_URL` in `.env.local`.

4. **No auth yet:** No login/signup. Dashboard is open. Add Firebase Auth later if needed.

5. **Mobile responsive:** Landing page should be responsive. Dashboard can be desktop-only (sidebar collapses at breakpoint).

6. **Delete tailwind.config.ts** — Tailwind v4 uses CSS-only config via @theme in globals.css.

---

## What exists now

The project is created with `create-next-app`. Files exist at:
- `src/app/globals.css` — has @theme colors defined
- `src/app/layout.tsx` — root layout with metadata
- `src/app/page.tsx` — landing page (needs style fixes for Tailwind v4)
- `src/app/dashboard/layout.tsx` — dashboard shell with sidebar
- `src/app/dashboard/page.tsx` — overview with mock metrics
- `src/app/review/page.tsx` — paste code review page

**The problem:** Tailwind v4 custom color classes (`bg-cream-100`, `text-ink-500`) aren't generating properly. If Claude Code can't fix the @theme approach, switch ALL color references to arbitrary values: `bg-[#F5F0EB]` instead of `bg-cream-100`.