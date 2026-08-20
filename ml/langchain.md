## LangChain LangGraph

<https://habr.com/ru/articles/956940/>

<https://habr.com/ru/companies/amvera/articles/933460/>

<https://habr.com/ru/search/?q=langGraph&target_type=posts&order=relevance>

 

## By raw GitHub stars

LangChain itself remains the most starred framework overall, with extensive tooling for chains, agents, and retrieval. 

Other high-star names in that same ranking include AutoGen, MetaGPT, LlamaIndex, and CrewAI. 

Separately, Microsoft AutoGen tops one survey at over 60,000 stars, though notably its development pace has slowed.

## By actual production adoption (probably the more meaningful metric for you)

This is where LangGraph pulls ahead of raw-star leaders: LangGraph leads in enterprise adoption with 34.5 million monthly downloads, even though Dify leads in raw GitHub stars at 144k. 

Around 400 companies now use LangGraph Platform in production, including Cisco, Uber, LinkedIn, BlackRock, and JPMorgan. That gap between "stars" and "downloads/production use" is a real signal — stars skew toward what's trending on social media, downloads skew toward what teams actually ship with.

## Where the Claude Agent SDK fits

Claude Agent SDK isn't really competing on the same "framework popularity" axis as LangChain/LangGraph/CrewAI — it's a vendor SDK tied to Claude specifically, not a model-agnostic orchestration layer, and one analysis flags that vendor-SDK star counts are a poor adoption metric compared to model-agnostic frameworks, since npm/PyPI download counts capture vendor SDK usage far better than stars do. 

Its comparison set is really "Claude-committed teams choosing SDK vs. LangGraph vs. going lower-level with the base API," not a broad multi-framework popularity contest.

## The category split (this is the more useful lens than a single ranking)

By 2026 the space has fragmented into distinct lanes rather than one leaderboard:
- general-purpose orchestration (LangChain/LangGraph, AutoGen),
- coding agents,
- browser/voice automation,
- and visual workflow builders

are now separate categories with different leaders. P
ython remains dominant overall,   
while TypeScript has captured the visual-workflow and IDE-extension corners — n8n, Flowise, Cline, Vercel AI SDK, Mastra.   
Notably, the **Vercel** AI SDK isn't a traditional agent framework like LangGraph or **CrewAI** but is the most-downloaded TypeScript AI toolkit by a wide margin, at roughly 2.8 million weekly npm downloads.   
And TypeScript-native entrants like **Mastra** have crossed roughly 21,000 GitHub stars with enterprise adopters including Marsh McLennan and SoftBank.

LangChain/LangGraph - the explicit state machine, model-agnostic flexibility, and the human-in-the-loop gates  

**CrewAI** and **AutoGen** are the other Python-native names worth knowing exist, but they solve a different problem (role-based multi-agent crews) than what your dashboard pipeline needs.


