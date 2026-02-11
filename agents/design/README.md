# Design Agent

The design agent generates coloring book design packages with built-in quality assurance.

## What it does

The agent runs in two phases: **Executor** (generates content) and **Evaluator** (reviews quality). If the evaluator finds issues, feedback is sent back to the executor for up to 5 attempts per component.

## Components

1. **Theme expansion** – Takes your basic idea and researches an artistic style (e.g., Johanna Basford, Kerby Rosanes). Produces an expanded theme, artistic style, and signature artist.
2. **Title and description** – Creates a marketable title (max 60 chars) and professional description (~200 words).
3. **MidJourney prompts** – Generates 50 prompts for coloring page images, formatted for MidJourney.
4. **SEO keywords** – Extracts 10 high-traffic keywords for discoverability.

## How users interact

In the Design Generation tab, users describe their coloring book idea (e.g., "forest animals coloring book for adults with intricate patterns"). The agent runs all components in sequence. Progress is shown in real time. Users can download the full report as JSON.

## Quality criteria

The evaluator checks for: no AI-sounding words, proper prompt format, relevant keywords, and natural-sounding copy. Content that fails is refined automatically.
