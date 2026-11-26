---
trigger: model_decision
description: Rules for Next.js, React, TypeScript UI, shared design system, role-aware workspaces, KaTeX math rendering, state handling, and WCAG 2.1 AA accessibility in apps/web and packages/ui.
---

# Frontend Architecture Rules (`apps/web`, `packages/ui`)

1. **Type Safety & Shared Contracts:** Strict TypeScript (`strict: true`, zero `any` escapes in API boundaries). Generate or share request/response types from OpenAPI (`packages/contracts`) rather than hand-duplicating backend DTOs.
2. **Design System Discipline:** Build reusable, accessible primitives in `packages/ui` (typography, tokens, spacing, dialogs, toasts, tables, skeletons). Never copy-paste divergent button/form/card implementations across Student, Teacher, Mentor, Parent, or Admin workspaces.
3. **Mandatory UI States:** Every data-driven view MUST implement real **loading** (skeleton/spinner), **empty** (actionable guidance), **error** (recoverable retry + correlation ID), and **offline/slow-network** states where applicable. Never render hardcoded placeholder charts or fake stats as real data.
4. **Role-Aware Navigation & Security:** Enforce route guards cleanly while remembering UI hiding is UX only—backend enforces truth. Never store secrets or private API keys in `NEXT_PUBLIC_*`; never call LLM/ElevenLabs APIs directly from browser code.
5. **Math, Bilingual & Responsive Rendering:** Render mathematical notation safely with KaTeX (never `dangerouslySetInnerHTML` on unsanitized Markdown/AI output; sanitize HTML/SVG strictly). Support Desktop, Tablet, and Mobile viewports cleanly, including RTL readiness (`dir="rtl"`) for Urdu.
6. **Accessibility (WCAG 2.1 AA):** Semantic landmarks, keyboard-only operability (including exam question palette, timers with polite ARIA updates, and whiteboard toolbars), 4.5:1 text contrast, non-color-only mastery indicators, and required captions/transcripts on all voice/audio players.
