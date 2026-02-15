# 🎨 Coloring Book Workflow Assistant

An AI-powered web app that takes you from coloring book idea to published Pinterest pins. Run the Streamlit app for a guided multi-tab workflow.

## ✨ What it does

1. **Design Generation** – Describe your idea; the AI creates a theme, marketable title, description, 50 MidJourney prompts, and 10 SEO keywords.
2. **Image Generation** – Point the app to a folder of images (generated from the MidJourney prompts). Select which images to use.
3. **Canva Design** – The app creates a multi-page Canva layout from your images (browser automation).
4. **Pinterest Publishing** – Publish pins with metadata to Pinterest (browser automation).

Canva and Pinterest use the same images folder. Follow the tabs in order for the best experience.

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

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project directory:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Run the Streamlit app**:
   ```bash
   uv run streamlit run app.py
   ```

   Or run the CLI (design generation only):
   ```bash
   uv run python main.py "forest animals coloring book for adults"
   ```

**Optional:** Set `CB_OUTPUT_DIR` to customize where saved designs and Pinterest publish folders are stored (default: `./output`).

## Project Structure

```
Coloring_book_assistant/
├── app.py                # Main Streamlit app (multi-tab workflow)
├── main.py               # CLI entry point
├── config.py             # Centralized paths and settings
├── core/                 # Shared infrastructure (state, persistence)
├── features/
│   ├── design_generation/ # Design: agents, tools, workflow, UI
│   └── image_generation/ # Image: monitor, image_utils, UI
├── workflows/
│   ├── canva/            # Canva design workflow
│   └── pinterest/        # Pinterest publishing workflow
├── integrations/
│   ├── canva/            # Canva browser automation
│   └── pinterest/        # Pinterest browser automation
├── ui/tabs/              # Streamlit tabs (Guide, Canva, Pinterest)
├── saved_designs/        # Saved design JSON files
├── pinterest_publish/    # Pinterest publish folders
├── docs/                 # Project documentation
└── utils/                # Compatibility shims
```

## 🛠️ Technical Details

- **Framework**: LangGraph for design orchestration, Streamlit for UI
- **AI Model**: OpenAI GPT-4o-mini via LangChain
- **Browser**: Playwright connects to existing browser (Chrome/Brave/Edge) with `--remote-debugging-port=9222`

## 📄 License

This project is open source and available under the MIT License.
