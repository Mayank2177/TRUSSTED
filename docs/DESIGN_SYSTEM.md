# DESIGN_SYSTEM.md

Applies to the optional dashboard (PRD FR-9, priority P2). Build the core library and benchmark first. The dashboard exists to make runs, decisions, receipts, and benchmark results **legible and honest**, not to look like a finished product.

## 1. Principles

1. **Evidence over polish.** Show numbers, sample sizes, and confidence intervals together. Never show a percentage without `n`.
2. **Show failures.** Failed scenarios (e.g. S6) are displayed with the same prominence as successes.
3. **Not colour alone.** Status always has a label and icon in addition to colour.
4. **Readable by default.** Calm, dense-but-airy layout; monospace for hashes and IDs.
5. **Light and dark.** Both themes supported from day one via tokens.

## 2. Design tokens

All values come from CSS variables. No hard-coded colours or pixel values in components.

### Colour (light / dark)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#FFFFFF` | `#0F1115` | page background |
| `--surface` | `#F6F7F9` | `#171A21` | cards, panels |
| `--surface-raised` | `#FFFFFF` | `#1E222B` | popovers, modals |
| `--border` | `#D9DDE3` | `#2C323D` | dividers |
| `--text` | `#14171C` | `#E8EAEE` | primary text |
| `--text-muted` | `#555E6B` | `#9AA3B2` | secondary text |
| `--accent` | `#2457D6` | `#6C94FF` | links, primary actions |
| `--allow` | `#1B7F4B` | `#4CC38A` | ALLOW |
| `--step-up` | `#9A6700` | `#E3B341` | STEP_UP |
| `--block` | `#B42318` | `#FF7B72` | BLOCK |
| `--info` | `#3A6EA5` | `#7FB0E6` | informational |

Contrast: body text >= 4.5:1, large text/UI >= 3:1 against its background. Verify with an automated check in CI.

### Typography

| Token | Value |
|---|---|
| `--font-sans` | `Inter, system-ui, -apple-system, "Segoe UI", sans-serif` |
| `--font-mono` | `"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace` |
| Scale | 12 / 14 / 16 / 20 / 24 / 32 px (`--text-xs` ... `--text-2xl`) |
| Line height | 1.5 body, 1.25 headings |
| Weights | 400, 500, 600 |

Use mono for: hashes, run IDs, JSON, token fields. Truncate hashes as `a1b2c3...d4e5f6` with a copy button.

### Spacing, radius, elevation

- Spacing scale (4px base): 4, 8, 12, 16, 24, 32, 48 (`--space-1` ... `--space-7`).
- Radius: 4 (inputs), 8 (cards), 999 (pills).
- Elevation: border-first; one shadow level for popovers only.

## 3. Components

| Component | Notes |
|---|---|
| **StatusBadge** | Variants `ALLOW`, `STEP_UP`, `BLOCK`. Icon + text label + colour (check / hand / x). |
| **MetricCard** | Value + `n` + 95% CI, e.g. `ASR 12.5% (n=40, CI 5.5-26.1%)`. Required fields; component refuses to render without `n`. |
| **ComparisonBar** | Baseline vs Trussted per scenario, with CI whiskers; labelled axis starting at 0. |
| **ScenarioTable** | Columns: scenario, type, baseline ASR, Trussted ASR, false-block, result. Failed rows flagged "Not mitigated". |
| **DecisionTimeline** | Vertical stages: Extract -> Cross-check -> Rank -> Perturb -> Decide -> Credential. Each node expandable. |
| **ConflictDiff** | Side-by-side `extracted` vs `reference` with the mismatching field highlighted (underline + icon). |
| **HashChainView** | Events as linked rows; broken link shown as an error state. |
| **VerifyPanel** | Upload receipt + public key -> shows pass/fail with the first failing event. |
| **LimitationsBanner** | Persistent, links to the limitations list. Cannot be dismissed on report pages. |
| **CodeBlock** | Mono, copy button, wraps long lines. |

## 4. Layout & navigation

- Left nav: **Runs**, **Benchmark**, **Receipts**, **Limitations**.
- Content max width 1200px; tables scroll horizontally inside their own container.
- Responsive breakpoints: 640 / 1024. Mobile shows stacked cards instead of wide tables.

### Screens

1. **Benchmark report**: summary metrics, ComparisonBar per scenario, ScenarioTable, LimitationsBanner.
2. **Run detail**: StatusBadge, DecisionTimeline, ConflictDiff, links to receipt.
3. **Receipt viewer**: HashChainView + VerifyPanel.
4. **Limitations**: plain list sourced from `ARCHITECTURE.md` section 9.

## 5. Content & tone

- Plain, factual labels. Avoid "secure", "protected", "guaranteed", "AI-powered".
- Say "Not mitigated" or "Failed" when true.
- Reason codes shown with human-readable text, e.g. `FACT_CONFLICT_HIGH` -> "Price or spec on the page disagrees with the reference source."
- Dates in ISO or locale-aware with timezone; money with currency code.

## 6. Accessibility

- Keyboard reachable; visible focus ring (`2px var(--accent)`).
- Semantic HTML; tables use `<th scope>`; charts have text alternatives (a data table toggle).
- Respect `prefers-reduced-motion` and `prefers-color-scheme`.
- No information conveyed by colour alone.
- Target WCAG 2.2 AA. Run axe in CI against key screens.

## 7. Implementation notes

- React + Vite + TypeScript; CSS variables for tokens; a small headless component library is fine, but keep styling in tokens.
- Charts: a single library (e.g. Recharts), themed from tokens.
- Storybook optional; if used, each component has light and dark stories.
