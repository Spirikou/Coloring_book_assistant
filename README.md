# 🎨 Coloring Book Design Generator

An AI-powered multi-agent system that generates complete coloring book design packages with built-in quality assurance using LangGraph.

## ✨ Features

- **Multi-Agent Architecture**: Executor agent generates content, Evaluator agent ensures quality
- **Iterative Refinement**: Automatic feedback loop improves output quality (up to 3 iterations)
- **Web Search Integration**: Research trending coloring book themes and market insights
- **Human-in-the-Loop**: Agent can ask clarifying questions when needed
- **Quality Criteria**: Enforces best practices (no AI-sounding words, proper formatting)
- **Complete Design Package**:
  - Marketable title (max 60 characters)
  - Professional description (~200 words)
  - 50 MidJourney prompts for coloring pages
  - 10 SEO-optimized keywords

## 🏗️ Architecture

```
User Input --> Executor Agent (generates content)
                     |
                     +--> Tool: generate_title_description
                     +--> Tool: generate_midjourney_prompts  
                     +--> Tool: extract_seo_keywords
                     +--> Tool: web_search (for trends)
                     +--> Tool: ask_user (clarifications)
                     |
                     v
              Evaluator Agent (reviews quality)
                     |
                     +--> Checks title/description against best practices
                     +--> Validates MidJourney prompt format and diversity
                     +--> Assesses SEO keyword relevance
                     |
                     v
              [Pass] --> Save Report --> Done
              [Fail] --> Feedback to Executor --> Retry (max 3 iterations)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- OpenAI API key
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Spirikou/Coloring_book_assistant.git
   cd Coloring_book_assistant
   ```

2. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project directory:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Run the application**:
   ```bash
   uv run python main.py
   ```

   Or with a theme directly:
   ```bash
   uv run python main.py "forest animals coloring book for adults"
   ```

## 📁 Project Structure

```
Coloring_book_assistant/
├── main.py              # Entry point - runs the multi-agent graph
├── graph.py             # LangGraph workflow definition
├── tools/
│   ├── __init__.py
│   ├── content_tools.py # Title, description, prompts, keywords generation
│   ├── search_tools.py  # DuckDuckGo web search for trends
│   └── user_tools.py    # User interaction and report saving
├── agents/
│   ├── __init__.py
│   ├── executor.py      # Executor agent with tool-calling
│   └── evaluator.py     # Evaluator agent with quality criteria
├── pyproject.toml       # Dependencies (managed by uv)
├── uv.lock              # Lock file
└── .env                 # Environment variables (create this)
```

## 🛠️ Technical Details

- **Framework**: LangGraph for multi-agent orchestration
- **AI Model**: OpenAI GPT-4o-mini via LangChain
- **Package Manager**: uv for fast, reliable dependency management
- **Web Search**: DuckDuckGo for trend research (no API key required)

### Agents

| Agent | Role | Temperature |
|-------|------|-------------|
| Executor | Generates content using tools | 0.7 (creative) |
| Evaluator | Reviews quality, provides feedback | 0.3 (consistent) |

### Tools

| Tool | Description |
|------|-------------|
| `generate_title_description` | Creates marketable title and description |
| `generate_midjourney_prompts` | Generates 50 diverse MidJourney prompts |
| `extract_seo_keywords` | Extracts 10 high-traffic SEO keywords |
| `web_search` | Search web for any query |
| `search_coloring_book_trends` | Get current trending themes |
| `ask_user` | Request clarification from user |
| `save_report` | Save results to JSON file |

## 🔍 Quality Criteria

The Evaluator agent checks for:

- **Title**: Max 60 chars, contains keywords, sounds natural
- **Description**: ~200 words, no banned AI words, includes required sections
- **MidJourney Prompts**: 
  - Exactly 50 prompts
  - Comma-separated keywords only (no sentences)
  - Includes `coloring book page` and `clean and simple line art`
  - Ends with `--v 5 --q 2 --no color --ar 1:1`
- **SEO Keywords**: 10 relevant, high-traffic terms

### Banned AI Words
The system automatically flags and rejects content containing overused AI-sounding words like: *whimsical, enchanting, captivating, mesmerizing, breathtaking, stunning, magical, delightful*, etc.

## 💡 Example

**Input**: 
```
forest animals coloring book for adults with intricate patterns
```

**Output**:
- **Title**: "Wild Forest Animals Adult Coloring Book"
- **Description**: Professional listing description with benefits section
- **50 MidJourney Prompts**: Ready-to-use prompts like:
  ```
  owl, mandala, forest, detailed feathers, coloring book page, clean and simple line art --v 5 --q 2 --no color --ar 1:1
  ```
- **10 SEO Keywords**: "adult coloring book", "forest animals", "stress relief coloring", etc.
- **Quality Score**: 85/100

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the tool!
