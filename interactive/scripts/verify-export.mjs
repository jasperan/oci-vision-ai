import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const root = process.cwd();
const indexPath = path.join(root, "out", "index.html");

if (!existsSync(indexPath)) {
  console.error(`Missing static export: ${indexPath}`);
  process.exit(1);
}

const html = readFileSync(indexPath, "utf8");
const requiredSnippets = [
  "Interactive Explorer",
  "Image Classification",
  "Object Detection",
  "Text / OCR",
  "Face Detection",
  "Document AI",
  "Metrics",
  "Architecture",
  "Workflow Packs",
  "Vision",
];

for (const snippet of requiredSnippets) {
  if (!html.includes(snippet)) {
    console.error(`Static export is missing expected content: ${snippet}`);
    process.exit(1);
  }
}

console.log(`Static export verified: ${indexPath}`);
