#!/usr/bin/env node
/**
 * Génère des fichiers .tldr (tldraw) depuis diagram.json
 * Usage: node gen-tldr.mjs --in ../diagrams/00-vue-generale.json --out ../00-vue-generale.tldr
 */
import fs from "node:fs";
import path from "node:path";

const NODE_W = 220;
const NODE_H = 90;
const COL_X_START = 80;
const COL_X_GAP = 480;
const NODE_Y_START = 220;
const NODE_Y_GAP = 200;
const GROUP_LABEL_Y = 160;

const SCHEMA = {
  schemaVersion: 2,
  sequences: {
    "com.tldraw.store": 5,
    "com.tldraw.asset": 1,
    "com.tldraw.camera": 1,
    "com.tldraw.document": 2,
    "com.tldraw.instance": 26,
    "com.tldraw.instance_page_state": 5,
    "com.tldraw.instance_presence": 6,
    "com.tldraw.page": 1,
    "com.tldraw.pointer": 1,
    "com.tldraw.shape": 4,
    "com.tldraw.asset.bookmark": 2,
    "com.tldraw.asset.image": 5,
    "com.tldraw.asset.video": 5,
    "com.tldraw.shape.arrow": 8,
    "com.tldraw.shape.bookmark": 2,
    "com.tldraw.shape.draw": 4,
    "com.tldraw.shape.embed": 4,
    "com.tldraw.shape.frame": 1,
    "com.tldraw.shape.geo": 11,
    "com.tldraw.shape.group": 0,
    "com.tldraw.shape.highlight": 3,
    "com.tldraw.shape.image": 5,
    "com.tldraw.shape.line": 5,
    "com.tldraw.shape.note": 10,
    "com.tldraw.shape.text": 4,
    "com.tldraw.shape.video": 4,
    "com.tldraw.binding": 0,
    "com.tldraw.binding.arrow": 1,
  },
};

function toRichText(text) {
  const lines = String(text).split("\n");
  return {
    type: "doc",
    content: lines.map((line) => {
      if (!line) return { type: "paragraph" };
      return {
        type: "paragraph",
        content: [{ type: "text", text: line }],
      };
    }),
  };
}

function buildIndexFactory() {
  const SAFE = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
  const BASE = SAFE.length;
  let counter = -1;
  return () => {
    counter += 1;
    const hi = Math.floor(counter / BASE);
    const lo = counter % BASE;
    return `a${SAFE[hi]}${SAFE[lo]}`;
  };
}

function center(point) {
  return { x: point.x + NODE_W / 2, y: point.y + NODE_H / 2 };
}

function buildTldr(diagram) {
  const nextIndex = buildIndexFactory();
  const records = [
    { typeName: "document", id: "document:document", gridSize: 10, name: "", meta: {} },
    { typeName: "page", id: "page:page", name: "Page 1", index: "a1", meta: {} },
    { typeName: "camera", id: "camera:page:page", x: 0, y: 0, z: 1, meta: {} },
    {
      typeName: "shape",
      id: "shape:title",
      type: "text",
      x: 80,
      y: 60,
      rotation: 0,
      isLocked: false,
      opacity: 1,
      parentId: "page:page",
      index: nextIndex(),
      meta: {},
      props: {
        richText: toRichText(diagram.title),
        size: "xl",
        font: "sans",
        textAlign: "start",
        color: "black",
        w: 900,
        scale: 1,
        autoSize: true,
      },
    },
  ];

  const groups = [];
  const groupToCol = new Map();
  for (const node of diagram.nodes) {
    const group = node.group || "Autre";
    if (!groupToCol.has(group)) {
      groupToCol.set(group, groups.length);
      groups.push(group);
    }
  }

  groups.forEach((group, i) => {
    records.push({
      typeName: "shape",
      id: `shape:grp_${i}`,
      type: "text",
      x: COL_X_START + i * COL_X_GAP,
      y: GROUP_LABEL_Y,
      rotation: 0,
      isLocked: false,
      opacity: 1,
      parentId: "page:page",
      index: nextIndex(),
      meta: {},
      props: {
        richText: toRichText(group),
        size: "l",
        font: "sans",
        textAlign: "start",
        color: "blue",
        w: 400,
        scale: 1,
        autoSize: true,
      },
    });
  });

  const nodePos = new Map();
  const colRowCount = new Map();

  for (const node of diagram.nodes) {
    const id = node.id;
    const label = node.label || id;
    const group = node.group || "Autre";
    const col = groupToCol.get(group) ?? 0;
    const row = colRowCount.get(col) ?? 0;
    colRowCount.set(col, row + 1);
    const x = COL_X_START + col * COL_X_GAP;
    const y = NODE_Y_START + row * NODE_Y_GAP;
    const shapeId = `shape:n_${id}`;
    const color = node.color || "black";

    records.push({
      typeName: "shape",
      id: shapeId,
      type: "geo",
      x,
      y,
      rotation: 0,
      isLocked: false,
      opacity: 1,
      parentId: "page:page",
      index: nextIndex(),
      meta: {},
      props: {
        geo: node.geo || "rectangle",
        dash: "draw",
        url: "",
        w: NODE_W,
        h: NODE_H,
        growY: 0,
        scale: 1,
        labelColor: "black",
        color,
        fill: node.fill || "semi",
        size: "m",
        font: "sans",
        align: "middle",
        verticalAlign: "middle",
        richText: toRichText(label),
      },
    });
    nodePos.set(id, { x, y, shapeId });
  }

  let edgeIndex = 0;
  for (const edge of diagram.edges || []) {
    const fromNode = nodePos.get(edge.from);
    const toNode = nodePos.get(edge.to);
    if (!fromNode || !toNode) continue;
    const start = center(fromNode);
    const end = center(toNode);
    records.push({
      typeName: "shape",
      id: `shape:e_${edgeIndex}`,
      type: "arrow",
      x: start.x,
      y: start.y,
      rotation: 0,
      isLocked: false,
      opacity: 1,
      parentId: "page:page",
      index: nextIndex(),
      meta: {},
      props: {
        kind: "arc",
        labelColor: "black",
        color: "black",
        fill: "none",
        dash: "draw",
        size: "m",
        arrowheadStart: "none",
        arrowheadEnd: "arrow",
        font: "sans",
        start: { x: 0, y: 0 },
        end: { x: end.x - start.x, y: end.y - start.y },
        bend: 0,
        richText: toRichText(edge.label || ""),
        labelPosition: 0.5,
        scale: 1,
        elbowMidPoint: 0.5,
      },
    });
    edgeIndex += 1;
  }

  return { tldrawFileFormatVersion: 1, schema: SCHEMA, records };
}

const inPath = process.argv.includes("--in")
  ? path.resolve(process.argv[process.argv.indexOf("--in") + 1])
  : null;
const outPath = process.argv.includes("--out")
  ? path.resolve(process.argv[process.argv.indexOf("--out") + 1])
  : null;

if (!inPath || !outPath) {
  console.error("Usage: node gen-tldr.mjs --in diagram.json --out output.tldr");
  process.exit(1);
}

const diagram = JSON.parse(fs.readFileSync(inPath, "utf8"));
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(buildTldr(diagram), null, 2));
console.log("Generated", outPath);
