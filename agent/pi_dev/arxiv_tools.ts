/**
 * Pi extension adding a single `arxiv_search` tool.
 *
 * This is the mechanism Pi uses for EVERYTHING beyond its 4-tool core
 * (read/write/edit/bash): a typed TypeScript module registered as a
 * tool, loaded by the CLI at startup. There is no separate "subagent"
 * or "handoff" concept here -- one Pi session, one model, and however
 * many tools you bolt on. Compare this to how much scaffolding the
 * same capability needs in LangGraph (a node function) or the Claude
 * Agent SDK (an MCP server) -- Pi's answer is "the smallest possible
 * TypeScript function."
 *
 * Install as a Pi package, or drop into ~/.pi/agent/extensions/ per
 * Pi's extension-loading convention.
 */

import type { Extension, ToolDefinition } from "@earendil-works/pi-coding-agent";

const ARXIV_API = "https://export.arxiv.org/api/query";

const PHYSICS_CATEGORIES = [
  "quant-ph",
  "hep-th",
  "cond-mat.str-el",
  "cond-mat.mes-hall",
];

const LECTURE_KEYWORDS = [
  "lecture note",
  "lecture notes",
  "lectures on",
  "course note",
  "introductory lectures",
];

const PHYSICS_TOPIC_KEYWORDS: Record<string, string[]> = {
  "quantum mechanics": ["quantum mechanic", "quantum theory"],
  QFT: ["quantum field theor", "qft", "field theory"],
  "solid state physics": ["solid state", "condensed matter", "many-body", "strongly correlated"],
};

interface ArxivEntry {
  title: string;
  arxivId: string;
  published: string;
  summary: string;
}

async function fetchAtom(searchQuery: string, maxResults = 100): Promise<ArxivEntry[]> {
  const url = `${ARXIV_API}?search_query=${encodeURIComponent(searchQuery)}&start=0&max_results=${maxResults}&sortBy=submittedDate&sortOrder=descending`;
  const res = await fetch(url);
  const xml = await res.text();

  // Minimal Atom parsing without a heavy XML dependency -- Pi's
  // "bring only what you need" spirit extends to extensions too.
  const entries: ArxivEntry[] = [];
  const entryBlocks = xml.split("<entry>").slice(1);
  for (const block of entryBlocks) {
    const title = (block.match(/<title>([\s\S]*?)<\/title>/)?.[1] ?? "").replace(/\s+/g, " ").trim();
    const summary = (block.match(/<summary>([\s\S]*?)<\/summary>/)?.[1] ?? "").replace(/\s+/g, " ").trim();
    const published = block.match(/<published>([\s\S]*?)<\/published>/)?.[1] ?? "";
    const idUrl = block.match(/<id>([\s\S]*?)<\/id>/)?.[1] ?? "";
    const arxivId = idUrl.split("/").pop() ?? "";
    entries.push({ title, summary, published, arxivId });
  }
  return entries;
}

function withinWindow(publishedIso: string, days: number): boolean {
  const published = new Date(publishedIso).getTime();
  const now = Date.now();
  return now - published <= days * 24 * 60 * 60 * 1000;
}

function matchesAny(text: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  return keywords.some((k) => lower.includes(k.toLowerCase()));
}

async function arxivSearch(args: { category: "physics" | "math"; days: number }) {
  const { category, days } = args;
  const query =
    category === "physics"
      ? PHYSICS_CATEGORIES.map((c) => `cat:${c}`).join(" OR ")
      : "cat:math.*";

  const entries = await fetchAtom(query);
  const inWindow = entries.filter((e) => withinWindow(e.published, days));

  const articles = [];
  for (const e of inWindow) {
    const blob = `${e.title} ${e.summary}`;
    if (!matchesAny(blob, LECTURE_KEYWORDS)) continue;

    if (category === "physics") {
      const topicTags = Object.entries(PHYSICS_TOPIC_KEYWORDS)
        .filter(([, kws]) => matchesAny(blob, kws))
        .map(([topic]) => topic);
      if (topicTags.length === 0) continue;
      articles.push({ title: e.title, arxivId: e.arxivId, topicTags });
    } else {
      articles.push({ title: e.title, arxivId: e.arxivId, topicTags: [] });
    }
  }

  return { articles, count: articles.length };
}

const arxivSearchTool: ToolDefinition = {
  name: "arxiv_search",
  description:
    "Search arXiv for lecture-notes-style papers. category is 'physics' " +
    "(quant-ph/hep-th/cond-mat, tagged with quantum mechanics/QFT/solid " +
    "state physics) or 'math' (math.* umbrella). days is the recency " +
    "window. Returns { articles: [{title, arxivId, topicTags}], count }.",
  parameters: {
    type: "object",
    properties: {
      category: { type: "string", enum: ["physics", "math"] },
      days: { type: "number" },
    },
    required: ["category", "days"],
  },
  handler: async (args: { category: "physics" | "math"; days: number }) => arxivSearch(args),
};

const extension: Extension = {
  name: "arxiv-digest-tools",
  tools: [arxivSearchTool],
};

export default extension;
