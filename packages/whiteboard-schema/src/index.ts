/**
 * Canonical schema contract & deterministic validator for Schema-Driven Whiteboard Actions
 * (docs/WHITEBOARD_SPECIFICATION.md & ADR-010).
 */

export const WHITEBOARD_OPCODES = [
  "WRITE_TEXT",
  "INSERT_FORMULA",
  "DRAW_LINE",
  "DRAW_ARROW",
  "DRAW_SHAPE",
  "DRAW_GRAPH",
  "DRAW_DIAGRAM",
  "INSERT_IMAGE",
  "HIGHLIGHT",
  "ERASE",
  "MOVE",
  "TRANSFORM",
] as const;

export type WhiteboardOpcode = (typeof WHITEBOARD_OPCODES)[number];

export interface WhiteboardAction {
  id: string;
  opcode: WhiteboardOpcode;
  sequence: number;
  at_ms: number;
  aria_summary: string;
  payload: Record<string, unknown>;
}

export interface WhiteboardSceneElement {
  id: string;
  opcode: Exclude<
    WhiteboardOpcode,
    "ERASE" | "MOVE" | "TRANSFORM" | "HIGHLIGHT"
  >;
  payload: Record<string, unknown>;
  aria_summary: string;
  highlighted?: boolean;
  highlight_color?: string;
  dx?: number;
  dy?: number;
  scale_x?: number;
  scale_y?: number;
  rotate_deg?: number;
}

const UNSAFE_PATTERN = /<\s*script|javascript:|onerror=|onload=/i;

export function containsUnsafeMarkup(value: unknown): boolean {
  if (typeof value === "string") {
    return UNSAFE_PATTERN.test(value);
  }
  if (Array.isArray(value)) {
    return value.some(containsUnsafeMarkup);
  }
  if (value !== null && typeof value === "object") {
    return Object.values(value).some(containsUnsafeMarkup);
  }
  return false;
}

export function isValidWhiteboardAction(
  candidate: unknown
): candidate is WhiteboardAction {
  if (candidate === null || typeof candidate !== "object") return false;
  const obj = candidate as Record<string, unknown>;
  if (typeof obj.id !== "string" || obj.id.trim().length === 0) return false;
  if (
    typeof obj.opcode !== "string" ||
    !(WHITEBOARD_OPCODES as readonly string[]).includes(obj.opcode)
  ) {
    return false;
  }
  if (typeof obj.sequence !== "number" || obj.sequence < 0) return false;
  if (typeof obj.at_ms !== "number" || obj.at_ms < 0) return false;
  if (typeof obj.aria_summary !== "string") return false;
  if (obj.payload === null || typeof obj.payload !== "object") return false;
  return !containsUnsafeMarkup(obj.payload) && !containsUnsafeMarkup(obj.aria_summary);
}

/**
 * Pure deterministic reducer applying ordered WhiteboardActions into scene objects
 * for synchronized playback, reload restore, and undo/redo replay.
 */
export function reduceWhiteboardActions(
  actions: WhiteboardAction[],
  maxAtMs?: number
): WhiteboardSceneElement[] {
  const byId = new Map<string, WhiteboardSceneElement>();
  const ordered = [...actions].sort((a, b) => a.sequence - b.sequence);

  for (const act of ordered) {
    if (!isValidWhiteboardAction(act)) continue;
    if (maxAtMs !== undefined && act.at_ms > maxAtMs) continue;

    if (act.opcode === "ERASE") {
      const targets = Array.isArray(act.payload.target_ids)
        ? (act.payload.target_ids as string[])
        : typeof act.payload.target_id === "string"
          ? [act.payload.target_id]
          : [];
      for (const tid of targets) {
        byId.delete(tid);
      }
      if (act.payload.clear_all === true) {
        byId.clear();
      }
      continue;
    }

    if (act.opcode === "MOVE") {
      const tid = String(act.payload.target_id ?? "");
      const existing = byId.get(tid);
      if (existing) {
        existing.dx = (existing.dx ?? 0) + Number(act.payload.dx ?? 0);
        existing.dy = (existing.dy ?? 0) + Number(act.payload.dy ?? 0);
      }
      continue;
    }

    if (act.opcode === "TRANSFORM") {
      const tid = String(act.payload.target_id ?? "");
      const existing = byId.get(tid);
      if (existing) {
        existing.scale_x = Number(act.payload.scale_x ?? existing.scale_x ?? 1);
        existing.scale_y = Number(act.payload.scale_y ?? existing.scale_y ?? 1);
        existing.rotate_deg = Number(
          act.payload.rotate_deg ?? existing.rotate_deg ?? 0
        );
      }
      continue;
    }

    if (act.opcode === "HIGHLIGHT") {
      const tid = String(act.payload.target_id ?? "");
      const existing = byId.get(tid);
      if (existing) {
        existing.highlighted = true;
        existing.highlight_color = String(act.payload.color ?? "#f59e0b");
      }
      continue;
    }

    byId.set(act.id, {
      id: act.id,
      opcode: act.opcode,
      payload: act.payload,
      aria_summary: act.aria_summary,
    });
  }

  return Array.from(byId.values());
}
