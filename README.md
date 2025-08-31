# Coloring Book Design Generator

A simple and clean LangChain application that generates innovative coloring book designs based on user input.

## Features

- 🎨 Generate creative coloring book designs
- 🖌️ Get detailed design descriptions and patterns
- 🌈 Receive color palette suggestions
- 📊 Difficulty level recommendations
- ✨ Unique design features and aspects

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Spirikou/Coloring_book_assistant.git
   cd Coloring_book_assistant
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   # or
   pip install -r requirements.txt
   ```

3. **Set up your OpenAI API key:**
   - Copy `env.example` to `.env`
   - Add your OpenAI API key:
     ```
     OPENAI_API_KEY=your_actual_api_key_here
     ```
   - Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)

3. **Run the application:**
   ```bash
   python main.py
   ```

## Usage

1. Run the script
2. Enter a description of the coloring book design you want
3. Get a complete design specification including:
   - Creative title
   - Design elements and patterns
   - Color palette suggestions
   - Difficulty level
   - Special features

## Example Input

- "a space adventure with planets and rockets"
- "underwater world with coral reefs and sea creatures"
- "enchanted garden with fairies and flowers"
- "steampunk city with gears and machinery"

## Requirements

- Python 3.12+
- OpenAI API key
- Internet connection

## Dependencies

- langchain-openai
- python-dotenv
- langchain
- langgraph
