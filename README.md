# ✈️ Asago – AI-Powered Flight Search Assistant

Asago is an intelligent flight search assistant that combines **agentic AI workflows**, **natural language processing**, and real-time flight data to deliver highly personalized travel options.

Built using:
- 🔁 [LangGraph](https://github.com/langchain-ai/langgraph) for agentic state machines
- 🤖 OpenAI's GPT for natural language understanding and result formatting
- 🌍 [Amadeus Flight Search API](https://developers.amadeus.com/) for real-time flight availability
- 🖥️ UI with Streamlit


## 🚀 Features

- **Conversational flight search**: Understands user input and preferences using GPT
- **Structured preference extraction**: Extracts travel preferences like class, airlines, flexibility, and more
- **Flight data integration**: Fetches real-time flight options via Amadeus APIs
- **Formatted results**: Converts raw flight data into friendly, readable flight itineraries
- **Agentic graph**: Uses LangGraph to coordinate the multi-step flight search workflow


## 🔧 Requirements

To run Asago, you'll need:

- ✅ Python 3.12+
- ✅ [Poetry](https://python-poetry.org/) (for dependency management)
- ✅ API Keys:
  - OpenAI (or compatible GPT provider)
  - Amadeus API key & secret


## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/asago.git
   cd asago
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set environment variables**
   Create a `.env` file or export manually:
   ```bash
   AMADEUS_API_KEY=your-amadeus-client-id
   AMADEUS_API_SECRET=your-amadeus-client-secret
   OPENAI_API_KEY=your-openai-api-key
   ```

4. **Run the app**
   ```bash
   poetry run streamlit run asago/app.py
   ```

## 🧠 How It Works
1. User Input → Natural language query (e.g., "I want to fly from NYC to Paris next month, business class.")
2. Parsing → GPT interprets intent and preferences
3. Flight Search → Amadeus API queried for best options
4. Formatting → GPT formats results into Markdown using rich visuals (✈️, 💰, 🕐)
5. Output → Friendly, professional flight summary shown to user

## 📋 TODO
* Fix bug: Improve extraction of flight preferences
* Clean up: Resolve remaining mypy typing issues


## 🤝 Acknowledgements
Asago was developed through Vibe Coding using Claude, and later refactored using GitHub Copilot.
