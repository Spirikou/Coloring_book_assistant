# 🎨 Coloring Book Workflow Assistant

An AI-powered web app that takes you from coloring book idea to published Pinterest pins. Run the Streamlit app for a guided multi-tab workflow.

## ✨ What it does

1. **Get Started** – Guide and workflow overview
2. **Design Generation** – Describe your idea; the AI creates a theme, marketable title, description, Midjourney prompts, and SEO keywords
3. **Image Generation** – Submit prompts to Midjourney (Publish → Upscale/Vary → Download), then select which images to use for Canva and Pinterest
4. **Canva Design** – Create a multi-page Canva layout from your selected images (browser automation)
5. **Pinterest Publishing** – Publish pins with metadata to Pinterest (browser automation)

Follow the tabs in order for the best experience.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- **OpenAI API key** (for Design Generation)
- **Midjourney account** (for Image Generation)
- **Brave browser** (for Midjourney, Canva, and Pinterest automation)

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

3. **Set up environment variables**  
   Create a `.env` file in the project directory:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Launch the app**:
   ```bash
   uv run streamlit run app.py
   ```

   The app opens in your browser at `http://localhost:8501`.

### CLI (Design Generation only)

Generate a design package from the command line:
```bash
uv run python main.py "forest animals coloring book for adults"
```

## 📋 Workflow Guide

### Step 1: Get Started
Read the guide and workflow overview in the first tab.

### Step 2: Design Generation
1. Enter a theme or idea (e.g. "ocean creatures coloring book for kids")
2. Click **Generate** to create a design package
3. The AI produces: title, description, Midjourney prompts, and SEO keywords
4. Save the design if you want to reuse it later

### Step 3: Image Generation
1. **Start Brave with remote debugging** (required for Midjourney automation):
   ```powershell
   & "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
   ```
   Or use **Launch Browser** in the app’s System & Prerequisites section.

2. **Log in to [Midjourney.com](https://www.midjourney.com)** in that browser window.

3. **Publish** – Prompts from Design Generation are pre-filled. Click **Publish** to submit them to Midjourney.

4. **Upscale/Vary** – After images appear, select actions (Upscale Subtle, Vary Strong, etc.) and click **Run**.

5. **Download** – Set the image count and click **Download** to save images to your output folder.

6. **Select Images** – Use the folder grid to choose which images to use for Canva and Pinterest. Click **Select All** or tick individual checkboxes.

### Step 4: Canva Design
1. Ensure you have selected images in the Image Generation tab
2. Open the Canva Design tab
3. Follow the prompts to create a multi-page layout (browser automation)

### Step 5: Pinterest Publishing
1. Ensure images are selected and Canva design is ready (if applicable)
2. Open the Pinterest Publishing tab
3. Follow the prompts to publish pins (browser automation)

## ⚙️ Configuration

- **Output folder** – Default: `./output/`. Set `CB_OUTPUT_DIR` to customize.
- **Generated images** – Default: `./output/generated_images/`. Change in the Image Generation tab or in `config.py`.
- **Midjourney** – Button coordinates and timing are in `config.py`. If you use a different screen resolution, run `uv run midjourney-agent setup` to record new coordinates.

## 📁 Project Structure

```
Coloring_book_assistant/
├── app.py                # Main Streamlit app (multi-tab workflow)
├── main.py               # CLI for design generation
├── config.py             # Centralized paths and Midjourney settings
├── core/                 # Shared infrastructure (state, persistence)
├── features/
│   ├── design_generation/ # Design: agents, tools, workflow, UI
│   └── image_generation/  # Image: Midjourney workflow, folder monitor, selection grid
├── workflows/
│   ├── canva/            # Canva design workflow
│   └── pinterest/       # Pinterest publishing workflow
├── integrations/
│   ├── canva/            # Canva browser automation
│   ├── pinterest/        # Pinterest browser automation
│   └── midjourney/       # Midjourney web automation (Playwright)
├── ui/tabs/              # Streamlit tabs (Guide, Canva, Pinterest)
├── output/               # Output root (configurable via CB_OUTPUT_DIR)
│   ├── saved_designs/    # Saved design JSON files
│   ├── generated_images/ # Midjourney-generated images
│   └── pinterest_publish/# Pinterest publish folders
├── docs/                 # Project documentation
└── utils/                # Compatibility shims
```

## 🛠️ Technical Details

- **Framework**: LangGraph for design orchestration, Streamlit for UI
- **AI Model**: OpenAI GPT-4o-mini via LangChain
- **Browser**: Playwright connects to Brave with `--remote-debugging-port=9222` for Midjourney, Canva, and Pinterest automation

## 📄 License

This project is open source and available under the MIT License.
