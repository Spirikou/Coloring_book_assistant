# 🎨 Coloring Book Design Generator

An advanced AI-powered tool that generates complete coloring book design packages using a structured 3-step reasoning process.

## ✨ Features

- **Interactive Chat Interface**: Built with Streamlit for a user-friendly experience
- **3-Step Reasoning Process**:
  1. 📝 Generate marketable title and compelling description
  2. 🎨 Create 10 MidJourney prompts for coloring book pages
  3. 🔍 Extract high-traffic SEO keywords for marketing
- **Professional Output**: Well-formatted results with download capabilities
- **Session Management**: Maintains conversation history and generated content

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key

### Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project directory:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Run the Streamlit app**:
   ```bash
   streamlit run streamlit_app.py
   ```

5. **Open your browser** to the URL shown in the terminal (usually `http://localhost:8501`)

## 🎯 How to Use

1. **Describe your vision**: Enter a description of the coloring book you want to create
2. **Wait for processing**: The AI will work through the 3-step reasoning process
3. **Review results**: Check the generated title, description, MidJourney prompts, and SEO keywords
4. **Download report**: Save your complete design package as a JSON file

## 📁 Project Structure

```
CB_Assit_LangChain/
├── main.py              # Original command-line version
├── streamlit_app.py     # Streamlit chat interface
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── .env                # Environment variables (create this)
```

## 🛠️ Technical Details

- **Framework**: Streamlit for the web interface
- **AI Model**: OpenAI GPT-4o-mini via LangChain
- **Architecture**: Modular functions for each step of the reasoning process
- **Output Format**: JSON for easy integration with other tools

## 💡 Example Usage

**Input**: "A magical forest with hidden creatures and geometric patterns"

**Output**:
- **Title**: "Enchanted Forest Mysteries"
- **Description**: "A captivating collection of intricate forest scenes featuring hidden magical creatures and geometric mandala patterns, perfect for mindfulness and creative expression."
- **10 MidJourney Prompts**: Ready-to-use prompts for generating coloring book pages
- **10 SEO Keywords**: High-traffic terms for marketing and discoverability

## 🔧 Customization

You can modify the prompts in each function to:
- Change the artistic style focus
- Adjust the number of generated prompts/keywords
- Modify the output format
- Add additional reasoning steps

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the tool!