"use client";

import katex from "katex";
import { Fragment, useMemo } from "react";

interface Segment {
  kind: "text" | "inline" | "display";
  content: string;
}

function tokenizeMath(input: string): Segment[] {
  const segments: Segment[] = [];
  const regex = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null = regex.exec(input);

  while (match !== null) {
    if (match.index > lastIndex) {
      segments.push({
        kind: "text",
        content: input.slice(lastIndex, match.index),
      });
    }
    const raw = match[0];
    if (raw.startsWith("$$")) {
      segments.push({ kind: "display", content: raw.slice(2, -2).trim() });
    } else {
      segments.push({ kind: "inline", content: raw.slice(1, -1).trim() });
    }
    lastIndex = regex.lastIndex;
    match = regex.exec(input);
  }
  if (lastIndex < input.length) {
    segments.push({ kind: "text", content: input.slice(lastIndex) });
  }
  return segments;
}

/**
 * Safely renders prose + $...$ / $$...$$ math via KaTeX (`trust: false`).
 * Non-math text is rendered as escaped React text nodes, preventing HTML/XSS injection.
 */
export function MathText({
  text,
  className = "",
}: {
  text: string;
  className?: string;
}) {
  const segments = useMemo(() => tokenizeMath(text), [text]);

  return (
    <span className={className}>
      {segments.map((seg, idx) => {
        if (seg.kind === "text") {
          return <Fragment key={idx}>{seg.content}</Fragment>;
        }
        const html = katex.renderToString(seg.content, {
          displayMode: seg.kind === "display",
          throwOnError: false,
          strict: false,
          trust: false,
        });
        return (
          <span
            key={idx}
            className={seg.kind === "display" ? "my-2 block overflow-x-auto" : "inline-block align-baseline"}
            dangerouslySetInnerHTML={{ __html: html }}
          />
        );
      })}
    </span>
  );
}
