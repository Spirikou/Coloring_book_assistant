# Design Generation Workflow

LangGraph workflow that generates a complete coloring book design package.

## Purpose

Takes a user's coloring book idea and produces a theme, title, description, 50 MidJourney prompts, and 10 SEO keywords. Each component is evaluated for quality and refined up to 5 times if needed.

## Components

1. **Theme expansion** – Expands the idea with artistic style and research
2. **Title and description** – Marketable copy for the coloring book
3. **MidJourney prompts** – 50 prompts for generating coloring page images
4. **SEO keywords** – 10 keywords for discoverability

## Flow

1. User enters idea in Design Generation tab
2. Executor agent runs theme expansion, then title/description, prompts, keywords
3. Evaluator checks each component; feedback loops back if needed
4. Final results are stored in workflow state and shown in the UI
5. User can download JSON report

## How users interact

Describe the coloring book in free text (e.g., "forest animals for adults with mandala patterns"). The agent runs automatically. Progress and scores are shown for each component.
