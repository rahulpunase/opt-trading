---
name: frontend
description: "Tailwind v4 class patterns, component conventions, and data-fetching rules for the opt-trading frontend"
trigger: /frontend
---

# /frontend

Load this before writing or reviewing any React/TypeScript code in `frontend/src/`. It prevents Tailwind CSS v4 class-naming mistakes and documents every structural pattern in the codebase.

## Usage

```
/frontend          # load conventions before starting any frontend task
/frontend review   # check a component you just wrote against these rules
```

## Tech Stack

- React 18 + TypeScript + Vite
- Tailwind CSS v4 via `@tailwindcss/vite` — **no `tailwind.config.*` file**
- `@tanstack/react-query` for all server state
- `react-router-dom` v6 for routing
- Theme tokens defined in `frontend/src/index.css` inside `@theme {}`
- Path alias `@/` maps to `frontend/src/`

---

## What You Must Do When Invoked

### Step 1 — Acknowledge

Print exactly one line before generating any code:

```
[frontend] Using project Tailwind v4 class conventions.
```

### Step 2 — Apply Tailwind v4 class rules

Tokens in `index.css @theme {}` become utility classes by their semantic name. Use the class form below. **Never** use CSS variable syntax in a `className`.

#### Token → class map

| Token | Backgrounds | Text | Borders / other |
|---|---|---|---|
| `--color-bg-base` | `bg-bg-base` | — | — |
| `--color-bg-surface` | `bg-bg-surface` | — | — |
| `--color-bg-elevated` | `bg-bg-elevated` | — | — |
| `--color-border` | — | — | `border-border`, `divide-border` |
| `--color-text-primary` | — | `text-text-primary` | — |
| `--color-text-muted` | — | `text-text-muted` | — |
| `--color-accent` | `bg-accent` | `text-accent` | `border-accent`, `ring-accent` |
| `--color-profit` | `bg-profit` | `text-profit` | `border-profit` |
| `--color-loss` | `bg-loss` | `text-loss` | `border-loss` |
| `--color-paper` | `bg-paper` | `text-paper` | `border-paper` |
| `--color-live` | `bg-live` | `text-live` | `border-live` |

#### Opacity modifiers — always `/N`, never `bg-opacity-*`

```
bg-accent/10  bg-accent/20  bg-profit/10  border-profit/30
bg-loss/10    border-loss/30   bg-paper/10   border-paper/30
```

#### Banned — NEVER write these

```
bg-[var(--color-accent)]        ← WRONG
text-[var(--color-profit)]      ← WRONG
border-[var(--color-border)]    ← WRONG
style={{ color: "var(--color-text-muted)" }}  ← WRONG
```

### Step 3 — Apply component conventions

#### cn() utility — always use it for className composition

`cn()` is available at `@/lib/utils` (backed by `clsx` + `tailwind-merge`). Use it for all className strings — never plain template literals.

```tsx
import { cn } from "@/lib/utils";

// Correct — conditional classes
className={cn(
  "rounded-lg px-3 py-2 text-sm transition",
  isActive
    ? "bg-accent/10 text-accent font-medium"
    : "text-text-muted hover:bg-bg-elevated hover:text-text-primary"
)}

// Correct — prop-driven extras
className={cn("rounded-xl border border-border bg-bg-surface p-5", className)}
```

#### Variant lookup table

When a component has more than two visual states, use a static `Record<Variant, string>` map combined with `cn()`:

```tsx
import { cn } from "@/lib/utils";

type Color = "profit" | "paper" | "loss";

const colorMap: Record<Color, string> = {
  profit: "text-profit bg-profit/10 border-profit/30",
  paper:  "text-paper  bg-paper/10  border-paper/30",
  loss:   "text-loss   bg-loss/10   border-loss/30",
};

className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-medium", colorMap[color])}
```

#### Card / surface container

```
rounded-xl border border-border bg-bg-surface p-5
```

For a card wrapping a table (no padding, overflow clipped):

```
rounded-xl border border-border bg-bg-surface overflow-hidden
```

#### Typography scale

| Use | Classes |
|---|---|
| Page section heading | `text-lg font-semibold text-text-primary` |
| Section sub-label | `text-sm text-text-muted` |
| Card inner label | `text-sm font-medium text-text-primary` |
| Large stat value | `text-2xl font-bold text-text-primary` |
| Table header cell | `text-xs font-medium uppercase tracking-wider text-text-muted` |
| Small metadata | `text-xs text-text-muted` |

#### Status badge pattern

```
bg-profit/10 text-profit border-profit/30  ← running / enabled
bg-loss/10   text-loss   border-loss/30    ← stopped / error
bg-paper/10  text-paper  border-paper/30   ← paused / paper mode
bg-live/10   text-live   border-live/30    ← live mode
```

Wrapper:

```
inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium
```

#### Active / selected state (tabs, nav)

```
bg-accent/10 text-accent font-medium                          ← active
text-text-muted hover:bg-bg-elevated hover:text-text-primary  ← inactive
```

#### Tables

```tsx
<table className="w-full text-sm">
  <thead>
    <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-text-muted">
      <th className="px-5 py-3">Col</th>
    </tr>
  </thead>
  <tbody className="divide-y divide-border">
    <tr className="transition hover:bg-bg-elevated">
      <td className="px-5 py-3.5 font-medium text-text-primary">Primary</td>
      <td className="px-5 py-3.5 text-text-muted">Secondary</td>
    </tr>
  </tbody>
</table>
```

#### Page layout

```tsx
<div className="space-y-6">
  <div>
    <h2 className="text-lg font-semibold text-text-primary">Title</h2>
    <p className="text-sm text-text-muted">Description</p>
  </div>
  {/* cards */}
</div>
```

#### Segment toggle (filter pill group)

```tsx
<div className="flex rounded-lg border border-border bg-bg-surface p-1 text-xs font-medium">
  {options.map((opt) => (
    <button
      key={opt}
      onClick={() => setSelected(opt)}
      className={cn(
        "rounded-md px-3 py-1.5 capitalize transition",
        selected === opt
          ? "bg-accent text-white"
          : "text-text-muted hover:text-text-primary"
      )}
    >
      {opt}
    </button>
  ))}
</div>
```

#### Form controls

```
rounded-lg border border-border bg-bg-surface px-3 py-1.5 text-xs text-text-primary
focus:outline-none focus:ring-1 focus:ring-accent
```

#### P&L coloring

```tsx
className={cn("font-medium", pnl >= 0 ? "text-profit" : "text-loss")}
```

#### Empty / loading state

```tsx
<div className="flex h-40 items-center justify-center text-sm text-text-muted">
  Loading…
</div>
```

### Step 4 — Data-fetching conventions

- **Server reads:** `useQuery` with key array + `queryFn` calling a function from `@/lib/api`
- **Mutations:** `useMutation`; call `queryClient.invalidateQueries()` in `onSettled`
- **Real-time:** consume the WebSocket hook from `@/lib/ws`
- **Polling:** `refetchInterval` in query options
- Never call `fetch` directly in a component — add endpoints to `@/lib/api.ts`

### Step 5 — TypeScript conventions

- API response types live in `@/lib/api.ts` — import from there, don't redeclare inline
- Use `Record<Variant, string>` for variant maps (TypeScript enforces exhaustiveness)
- Use `??` for nullish fallback, `?.` for optional chaining
- Type variant unions explicitly: `type Variant = "running" | "stopped" | "paused"`

---

## Honesty Rules

- Never generate `bg-[var(--color-*)]` or `text-[var(--color-*)]` — wrong in this project
- Always use `cn()` from `@/lib/utils` — never raw template literals for className
- Never use `style={{ color: "var(--color-*)" }}` to work around a class — use the token table
- If a new color is needed and is not in the token table, say so and suggest adding it to `index.css @theme {}` rather than using an arbitrary value
