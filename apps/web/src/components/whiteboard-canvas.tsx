"use client";

import {
  type WhiteboardAction,
  type WhiteboardSceneElement,
  reduceWhiteboardActions,
} from "@go4guru/whiteboard-schema";
import katex from "katex";
import { useMemo, useRef, useState } from "react";

type ToolMode = "select" | "line" | "note";

interface WhiteboardCanvasProps {
  actions: WhiteboardAction[];
  maxAtMs?: number;
  canUndo: boolean;
  canRedo: boolean;
  busy?: boolean;
  onStudentAction?: (action: WhiteboardAction) => Promise<void> | void;
  onUndo?: () => Promise<void> | void;
  onRedo?: () => Promise<void> | void;
  onSaveSnapshot?: () => Promise<void> | void;
}

function renderLatexHtml(latex: string): string {
  return katex.renderToString(latex, {
    displayMode: false,
    throwOnError: false,
    strict: false,
    trust: false,
  });
}

function renderGraphElement(el: WhiteboardSceneElement) {
  const p = el.payload;
  const x = Number(p.x ?? 420);
  const y = Number(p.y ?? 80);
  const w = Number(p.w ?? 260);
  const h = Number(p.h ?? 180);
  const xMin = Number(p.x_min ?? -4);
  const xMax = Number(p.x_max ?? 4);
  const yMin = Number(p.y_min ?? 0);
  const yMax = Number(p.y_max ?? 10);
  const pts = Array.isArray(p.points) ? (p.points as [number, number][]) : [];

  const mapX = (vx: number) =>
    x + ((vx - xMin) / Math.max(0.0001, xMax - xMin)) * w;
  const mapY = (vy: number) =>
    y + h - ((vy - yMin) / Math.max(0.0001, yMax - yMin)) * h;

  const polylinePoints = pts.map(([vx, vy]) => `${mapX(vx)},${mapY(vy)}`).join(" ");
  const zeroX = mapX(Math.max(xMin, Math.min(xMax, 0)));
  const zeroY = mapY(Math.max(yMin, Math.min(yMax, 0)));

  return (
    <g key={el.id} data-testid={`wb-el-${el.id}`}>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
        fill="#f8fafc"
        stroke={el.highlighted ? (el.highlight_color ?? "#f59e0b") : "#cbd5e1"}
        strokeWidth={el.highlighted ? 3 : 1.5}
      />
      <line x1={x} y1={zeroY} x2={x + w} y2={zeroY} stroke="#94a3b8" strokeWidth={1.2} />
      <line x1={zeroX} y1={y} x2={zeroX} y2={y + h} stroke="#94a3b8" strokeWidth={1.2} />
      {polylinePoints && (
        <polyline
          fill="none"
          stroke="#2563eb"
          strokeWidth={2.5}
          points={polylinePoints}
        />
      )}
      {typeof p.title === "string" && (
        <text x={x + 10} y={y + 18} fontSize={12} fontWeight={600} fill="#1e293b">
          {p.title}
        </text>
      )}
      {typeof p.x_label === "string" && (
        <text x={x + w - 24} y={y + h - 6} fontSize={11} fill="#475569">
          {p.x_label}
        </text>
      )}
      {typeof p.y_label === "string" && (
        <text x={x + 6} y={y + 34} fontSize={11} fill="#475569">
          {p.y_label}
        </text>
      )}
    </g>
  );
}

function renderDiagramElement(el: WhiteboardSceneElement) {
  const p = el.payload;
  const x = Number(p.x ?? 380);
  const y = Number(p.y ?? 80);
  const nodes = Array.isArray(p.nodes)
    ? (p.nodes as string[])
    : ["Input", "Law", "Output"];
  const title = typeof p.title === "string" ? p.title : "System Diagram";
  return (
    <g key={el.id} data-testid={`wb-el-${el.id}`}>
      <rect
        x={x}
        y={y}
        width={330}
        height={130}
        rx={10}
        fill="#eef2ff"
        stroke={el.highlighted ? "#f59e0b" : "#6366f1"}
        strokeWidth={el.highlighted ? 3 : 1.5}
      />
      <text x={x + 14} y={y + 24} fontSize={13} fontWeight={700} fill="#312e81">
        {title}
      </text>
      {nodes.slice(0, 3).map((label, idx) => {
        const bx = x + 12 + idx * 106;
        const by = y + 48;
        return (
          <g key={`${el.id}-n-${idx}`}>
            <rect
              x={bx}
              y={by}
              width={92}
              height={46}
              rx={6}
              fill="#ffffff"
              stroke="#4f46e5"
              strokeWidth={1.2}
            />
            <text
              x={bx + 46}
              y={by + 27}
              fontSize={11}
              fontWeight={600}
              textAnchor="middle"
              fill="#1e1b4b"
            >
              {String(label).slice(0, 14)}
            </text>
            {idx < Math.min(2, nodes.length - 1) && (
              <line
                x1={bx + 92}
                y1={by + 23}
                x2={bx + 106}
                y2={by + 23}
                stroke="#4f46e5"
                strokeWidth={1.8}
                markerEnd="url(#wb-arrowhead)"
              />
            )}
          </g>
        );
      })}
    </g>
  );
}

/**
 * Deterministic SVG + KaTeX Whiteboard Renderer (`trust: false`, zero arbitrary code eval).
 */
export function WhiteboardCanvas({
  actions,
  maxAtMs,
  canUndo,
  canRedo,
  busy = false,
  onStudentAction,
  onUndo,
  onRedo,
  onSaveSnapshot,
}: WhiteboardCanvasProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [tool, setTool] = useState<ToolMode>("line");
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragEnd, setDragEnd] = useState<{ x: number; y: number } | null>(null);
  const [noteText, setNoteText] = useState("Check units here");

  const scene = useMemo(
    () => reduceWhiteboardActions(actions, maxAtMs),
    [actions, maxAtMs]
  );

  function toBoardCoords(e: React.PointerEvent<SVGSVGElement>): { x: number; y: number } {
    const svg = svgRef.current;
    if (!svg) return { x: 100, y: 100 };
    const rect = svg.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / Math.max(1, rect.width)) * 760);
    const y = Math.round(((e.clientY - rect.top) / Math.max(1, rect.height)) * 480);
    return { x: Math.max(0, Math.min(760, x)), y: Math.max(0, Math.min(480, y)) };
  }

  async function handlePointerDown(e: React.PointerEvent<SVGSVGElement>) {
    if (!onStudentAction || busy || tool === "select") return;
    const pt = toBoardCoords(e);
    if (tool === "note") {
      const action: WhiteboardAction = {
        id: `student_note_${Date.now()}`,
        opcode: "WRITE_TEXT",
        sequence: actions.length + 100,
        at_ms: maxAtMs ?? 0,
        aria_summary: `Student board note: ${noteText}`,
        payload: {
          x: pt.x,
          y: pt.y,
          text: noteText.trim() || "Student Note",
          font_size: 14,
          color: "#2563eb",
        },
      };
      await onStudentAction(action);
      return;
    }
    setDragStart(pt);
    setDragEnd(pt);
  }

  function handlePointerMove(e: React.PointerEvent<SVGSVGElement>) {
    if (!dragStart) return;
    setDragEnd(toBoardCoords(e));
  }

  async function handlePointerUp() {
    if (!dragStart || !dragEnd || !onStudentAction) {
      setDragStart(null);
      setDragEnd(null);
      return;
    }
    const dx = Math.abs(dragEnd.x - dragStart.x);
    const dy = Math.abs(dragEnd.y - dragStart.y);
    const x1 = dragStart.x;
    const y1 = dragStart.y;
    const x2 = dx + dy < 8 ? x1 + 90 : dragEnd.x;
    const y2 = dx + dy < 8 ? y1 + 35 : dragEnd.y;
    setDragStart(null);
    setDragEnd(null);

    const action: WhiteboardAction = {
      id: `student_line_${Date.now()}`,
      opcode: "DRAW_LINE",
      sequence: actions.length + 100,
      at_ms: maxAtMs ?? 0,
      aria_summary: `Student annotation line from (${x1},${y1}) to (${x2},${y2})`,
      payload: { x1, y1, x2, y2, color: "#2563eb", stroke_width: 2.5 },
    };
    await onStudentAction(action);
  }

  function handleExportSvg() {
    const svg = svgRef.current;
    if (!svg) return;
    const xml = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "classroom-whiteboard.svg";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Whiteboard Tools
          </span>
          {(["line", "note", "select"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setTool(mode)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                tool === mode
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              {mode === "line" ? "Draw Line" : mode === "note" ? "Place Note" : "Inspect"}
            </button>
          ))}
          {tool === "note" && (
            <input
              type="text"
              aria-label="Whiteboard note text"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              className="w-40 rounded-md border border-slate-300 px-2 py-1 text-xs"
              placeholder="Board note..."
            />
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!canUndo || busy}
            onClick={() => onUndo?.()}
            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Undo
          </button>
          <button
            type="button"
            disabled={!canRedo || busy}
            onClick={() => onRedo?.()}
            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Redo
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onSaveSnapshot?.()}
            className="rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-800 hover:bg-indigo-100 disabled:opacity-40"
          >
            Save Snapshot
          </button>
          <button
            type="button"
            onClick={handleExportSvg}
            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Export SVG
          </button>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
        <svg
          ref={svgRef}
          viewBox="0 0 760 480"
          role="img"
          aria-label="Synchronized Classroom Whiteboard"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          className="block h-auto w-full cursor-crosshair select-none bg-white"
        >
          <defs>
            <marker
              id="wb-arrowhead"
              markerWidth="8"
              markerHeight="8"
              refX="6"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L0,6 L7,3 z" fill="#4f46e5" />
            </marker>
            <pattern id="wb-grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <path
                d="M 24 0 L 0 0 0 24"
                fill="none"
                stroke="#f1f5f9"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect x={0} y={0} width={760} height={480} fill="url(#wb-grid)" />

          {scene.map((el) => {
            const p = el.payload;
            const transform = `translate(${el.dx ?? 0}, ${el.dy ?? 0}) rotate(${el.rotate_deg ?? 0}) scale(${el.scale_x ?? 1}, ${el.scale_y ?? 1})`;
            const highlightStroke = el.highlighted
              ? (el.highlight_color ?? "#f59e0b")
              : undefined;

            if (el.opcode === "WRITE_TEXT") {
              return (
                <text
                  key={el.id}
                  data-testid={`wb-el-${el.id}`}
                  transform={transform}
                  x={Number(p.x ?? 40)}
                  y={Number(p.y ?? 40)}
                  fontSize={Number(p.font_size ?? 16)}
                  fontWeight={600}
                  fill={String(p.color ?? "#0f172a")}
                >
                  {String(p.text ?? "")}
                </text>
              );
            }
            if (el.opcode === "INSERT_FORMULA") {
              const fx = Number(p.x ?? 40);
              const fy = Number(p.y ?? 200);
              const html = renderLatexHtml(String(p.latex ?? "y = x^2"));
              return (
                <g key={el.id} data-testid={`wb-el-${el.id}`} transform={transform}>
                  {el.highlighted && (
                    <rect
                      x={fx - 6}
                      y={fy - 8}
                      width={340}
                      height={48}
                      rx={8}
                      fill="#fef3c7"
                      stroke="#f59e0b"
                      strokeWidth={2}
                    />
                  )}
                  <foreignObject x={fx} y={fy} width={440} height={54}>
                    <div
                      className="text-sm font-medium text-slate-900"
                      dangerouslySetInnerHTML={{ __html: html }}
                    />
                  </foreignObject>
                </g>
              );
            }
            if (el.opcode === "DRAW_LINE" || el.opcode === "DRAW_ARROW") {
              return (
                <line
                  key={el.id}
                  data-testid={`wb-el-${el.id}`}
                  transform={transform}
                  x1={Number(p.x1 ?? 50)}
                  y1={Number(p.y1 ?? 50)}
                  x2={Number(p.x2 ?? 200)}
                  y2={Number(p.y2 ?? 50)}
                  stroke={highlightStroke ?? String(p.color ?? "#1d4ed8")}
                  strokeWidth={Number(p.stroke_width ?? 2.5)}
                  markerEnd={
                    el.opcode === "DRAW_ARROW" ? "url(#wb-arrowhead)" : undefined
                  }
                />
              );
            }
            if (el.opcode === "DRAW_SHAPE") {
              const shape = String(p.shape ?? "rect");
              if (shape === "circle") {
                return (
                  <circle
                    key={el.id}
                    data-testid={`wb-el-${el.id}`}
                    transform={transform}
                    cx={Number(p.x ?? 120)}
                    cy={Number(p.y ?? 120)}
                    r={Number(p.r ?? 36)}
                    fill={String(p.fill ?? "rgba(79,70,229,0.08)")}
                    stroke={highlightStroke ?? String(p.stroke ?? "#4f46e5")}
                    strokeWidth={2}
                  />
                );
              }
              return (
                <rect
                  key={el.id}
                  data-testid={`wb-el-${el.id}`}
                  transform={transform}
                  x={Number(p.x ?? 40)}
                  y={Number(p.y ?? 90)}
                  width={Number(p.w ?? 180)}
                  height={Number(p.h ?? 70)}
                  rx={8}
                  fill={String(p.fill ?? "rgba(14,165,233,0.08)")}
                  stroke={highlightStroke ?? String(p.stroke ?? "#0284c7")}
                  strokeWidth={2}
                />
              );
            }
            if (el.opcode === "DRAW_GRAPH") {
              return renderGraphElement(el);
            }
            if (el.opcode === "DRAW_DIAGRAM") {
              return renderDiagramElement(el);
            }
            return null;
          })}

          {dragStart && dragEnd && (
            <line
              x1={dragStart.x}
              y1={dragStart.y}
              x2={dragEnd.x}
              y2={dragEnd.y}
              stroke="#2563eb"
              strokeWidth={2}
              strokeDasharray="4 4"
            />
          )}
        </svg>
      </div>

      {/* Screen-reader accessible description of active whiteboard elements */}
      <details className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
        <summary className="cursor-pointer font-medium text-slate-700">
          Accessible Whiteboard Description ({scene.length} active objects)
        </summary>
        <ul aria-live="polite" className="mt-2 list-disc space-y-1 pl-4">
          {scene.map((item) => (
            <li key={item.id}>
              <span className="font-mono text-[11px] text-slate-500">
                [{item.opcode}]
              </span>{" "}
              {item.aria_summary}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
