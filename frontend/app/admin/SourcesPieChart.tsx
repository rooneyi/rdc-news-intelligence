"use client";

import { useMemo } from "react";

export type BreakdownRow = { source: string; count: number; in_catalog?: boolean };

const MAX_SLICES = 10;
const CX = 100;
const CY = 100;
const R_OUT = 72;
const R_IN = 44;

/**
 * Anneau du donut : portion entre aStart et aEnd (angles décroissants = sens antihoraire).
 */
function donutWedgePath(aStart: number, aEnd: number): string {
  const xo1 = CX + R_OUT * Math.cos(aStart);
  const yo1 = CY + R_OUT * Math.sin(aStart);
  const xo2 = CX + R_OUT * Math.cos(aEnd);
  const yo2 = CY + R_OUT * Math.sin(aEnd);
  const xi1 = CX + R_IN * Math.cos(aEnd);
  const yi1 = CY + R_IN * Math.sin(aEnd);
  const xi2 = CX + R_IN * Math.cos(aStart);
  const yi2 = CY + R_IN * Math.sin(aStart);

  const delta = aEnd - aStart;
  const span = Math.abs(delta) % (Math.PI * 2);
  const large = span > Math.PI ? 1 : 0;
  const sweepOut = delta < 0 ? 0 : 1;
  const sweepIn = delta < 0 ? 1 : 0;

  return [
    `M ${xo1} ${yo1}`,
    `A ${R_OUT} ${R_OUT} 0 ${large} ${sweepOut} ${xo2} ${yo2}`,
    `L ${xi1} ${yi1}`,
    `A ${R_IN} ${R_IN} 0 ${large} ${sweepIn} ${xi2} ${yi2}`,
    "Z",
  ].join(" ");
}

function hsl(i: number, orphan: boolean): string {
  if (orphan) return "oklch(0.55 0.02 260)";
  const h = (i * 47 + 210) % 360;
  return `oklch(0.72 0.14 ${h})`;
}

type Slice = { label: string; count: number; fraction: number; orphan: boolean };

function buildSlices(rows: BreakdownRow[]): Slice[] {
  const positive = rows.filter((r) => r.count > 0);
  const total = positive.reduce((s, r) => s + r.count, 0);
  if (total <= 0) return [];

  const sorted = [...positive].sort((a, b) => b.count - a.count);
  const head = sorted.slice(0, MAX_SLICES - 1);
  const tail = sorted.slice(MAX_SLICES - 1);
  const merged: typeof sorted = [...head];
  if (tail.length > 0) {
    const sum = tail.reduce((s, r) => s + r.count, 0);
    merged.push({
      source: `Autres (${tail.length})`,
      count: sum,
      in_catalog: tail.every((t) => t.in_catalog !== false),
    });
  }

  return merged.map((r) => ({
    label: r.source,
    count: r.count,
    fraction: r.count / total,
    orphan: r.in_catalog === false,
  }));
}

type Props = {
  breakdown: BreakdownRow[];
  loading?: boolean;
};

export function SourcesPieChart({ breakdown, loading }: Props) {
  const slices = useMemo(() => buildSlices(breakdown), [breakdown]);

  const segments = useMemo(() => {
    if (slices.length === 0) return [];
    let angle = -Math.PI / 2;
    return slices.map((sl, i) => {
      const sweep = sl.fraction * Math.PI * 2;
      const nextAngle = angle - sweep;
      const path = donutWedgePath(angle, nextAngle);
      const seg = { path, color: hsl(i, sl.orphan), label: sl.label, count: sl.count, idx: i };
      angle = nextAngle;
      return seg;
    });
  }, [slices]);

  const staggerMs = 55;

  if (loading) {
    return (
      <div className="flex min-h-[220px] items-center justify-center rounded-xl border border-slate-600/30 bg-slate-900/40">
        <div className="h-40 w-40 animate-pulse rounded-full bg-slate-700/50" />
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-600/40 bg-slate-900/30 p-6 text-center text-sm text-slate-500">
        <p>Aucune donnée à afficher</p>
        <p className="text-xs text-slate-600">Il faut au moins un article avec une source en base.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:justify-center sm:gap-8">
      <div className="relative shrink-0">
        <svg
          viewBox="0 0 200 200"
          className="rdc-pie-chart h-44 w-44 sm:h-52 sm:w-52"
          aria-hidden
        >
          <title>Répartition des articles par source</title>
          {segments.map((seg) => (
            <path
              key={`${seg.label}-${seg.idx}`}
              d={seg.path}
              fill={seg.color}
              stroke="rgba(15,23,42,0.85)"
              strokeWidth={1}
              className="rdc-pie-slice origin-center"
              style={{
                animationDelay: `${seg.idx * staggerMs}ms`,
              }}
            />
          ))}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Articles</p>
            <p className="text-xl font-semibold tabular-nums text-slate-100">
              {slices.reduce((s, x) => s + x.count, 0)}
            </p>
          </div>
        </div>
      </div>

      <ul className="max-h-52 min-w-0 flex-1 space-y-1.5 overflow-y-auto text-xs text-slate-300">
        {segments.map((seg, i) => (
          <li key={`${seg.label}-${i}`} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-sm border border-slate-600/50"
              style={{ backgroundColor: seg.color }}
            />
            <span className="min-w-0 flex-1 truncate" title={seg.label}>
              {seg.label}
            </span>
            <span className="shrink-0 tabular-nums text-slate-400">{seg.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
