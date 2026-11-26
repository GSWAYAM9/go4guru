# Interactive Whiteboard Specification (`docs/WHITEBOARD_SPECIFICATION.md`)

**Core Requirement (Section 20):** The whiteboard must be a real, interactive, persistent, replayable canvas controlled via strict structured schemas — **never** executing arbitrary AI-generated JavaScript/HTML code.

---

## 1. Canvas Technology Evaluation

| Option | Strengths | Risks / Licensing Considerations | Verdict |
| :--- | :--- | :--- | :--- |
| **`tldraw` (SDK v2/v3+)** | Best-in-class React/TS UX, smooth pan/zoom/handwriting/arrows/layering, built-in JSON store snapshots & record diffs ideal for replay and collaborative/AI sync. | **Commercial License Constraint:** Removing the `tldraw` watermark in commercial SaaS production requires a paid tldraw commercial license (otherwise proprietary watermarked license applies). | **Strongest UX candidate** if commercial license budget approved. |
| **`Excalidraw` (`@excalidraw/excalidraw`)** | **MIT License (zero royalties)**, crisp educational diagram look, scene JSON elements, React component, zoom/pan/undo/redo/export PNG & SVG. | Slightly fewer built-in rich shape primitives (tables/KaTeX embeds require clean custom overlay/SVG element wrappers). | **Best zero-royalty MIT option** if avoiding commercial canvas licensing fees. |
| **Custom Konva / Fabric.js** | Full low-level control. | High engineering cost to build handwriting smoothing, undo/redo stacks, selection handles, and accessibility. | Not recommended over tldraw/Excalidraw. |

**Phase 0 Decision Flag:** Evaluate `tldraw` commercial license cost vs `Excalidraw` (MIT) before Phase 4 kickoff; design our `WhiteboardAction` schema in `packages/whiteboard-schema` cleanly **canvas-engine-agnostic** so an adapter maps canonical actions to whichever library is selected!

---

## 2. Canonical Structured Whiteboard Action Schema

All AI whiteboard commands conform to a strict discriminated union validated by Pydantic (backend) and Zod (frontend):

| Action (`op`) | Required Fields | Visual Semantics |
| :--- | :--- | :--- |
| `WRITE_TEXT` | `id`, `x`, `y`, `text`, `font_size`, `color`, `max_width` | Plain/heading text block (HTML-escaped, no script injection) |
| `INSERT_FORMULA` | `id`, `x`, `y`, `latex`, `font_size`, `color` | Sanitized KaTeX-rendered math block or SVG formula node |
| `DRAW_LINE` | `id`, `x1`, `y1`, `x2`, `y2`, `stroke`, `style` (`solid\|dashed\|dotted`) | Straight segment / axis / ray |
| `DRAW_ARROW` | `id`, `x1`, `y1`, `x2`, `y2`, `label?`, `stroke` | Vector, ray, process flow, free-body force arrow |
| `DRAW_SHAPE` | `id`, `shape` (`rect\|circle\|ellipse\|triangle\|polygon`), `bounds`, `fill?`, `stroke`, `label?` | Geometric figures, boxes, Venn sets, containers |
| `DRAW_GRAPH` | `id`, `bounds`, `x_range`, `y_range`, `series[]` (sampled coordinate points or safe AST math plot), `labels` | Deterministic 2D Cartesian plots (linear/quadratic/trig/kinematics) |
| `DRAW_DIAGRAM` | `id`, `template` (`free_body\|circuit\|ray_optics\|chem_bond\|number_line\|timeline\|mind_map\|table`), `params` | Domain-specific parameterized vector templates rendered safely by client components |
| `INSERT_IMAGE` | `id`, `asset_id` (signed internal/rights-approved URL only), `x`, `y`, `w`, `h`, `alt` | Verified educational diagram/map asset (no arbitrary external URLs) |
| `HIGHLIGHT` | `target_id` or `bounds`, `color`, `duration_ms?` | Pulse/callout box drawing student attention during narration |
| `ERASE` | `target_ids[]` or `layer` | Removes specified objects cleanly |
| `MOVE` | `target_id`, `dx`, `dy` | Translates object cleanly |
| `TRANSFORM` | `target_id`, `scale_x`, `scale_y`, `rotate_deg` | Scales/rotates existing shape |

**Security Invariants:**
- Never pass `eval()`, `new Function()`, raw `<script>`, `javascript:` URLs, or unsanitized inline `<svg>` strings from AI outputs to the DOM.
- `INSERT_IMAGE` only accepts registered `whiteboard_assets` / `content_items` IDs vetted by Content Rights.

---

## 3. Persistence, Export & Replay Architecture

- **Event Log (`whiteboard_events`):** Append-only ordered events (`sequence_no`) tagged by `classroom_session_id`, `segment_seq`, and `actor` (`ai` or `student`), storing student handwriting strokes alongside AI actions.
- **Snapshots (`whiteboard_snapshots`):** Periodic full scene checkpoints written at every segment boundary and every N student strokes so restoring a 45-minute lesson never replays 5,000 raw stroke events from zero.
- **Export:** Client/server exports clean PNG, SVG, or PDF study notes combining whiteboard snapshots + lesson narration notes.
- **Accessibility:** Every AI `canvas_action` carries optional `aria_summary` so a live screen-reader panel narrates visual board updates alongside audio captions.
