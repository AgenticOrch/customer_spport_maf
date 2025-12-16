# Customer Support with Microsoft Agent Framework

A customer support system using Microsoft Agent Framework (MAF) with multi-agent orchestration for database queries and fraud detection.

## Features

- 🤖 **Multi-Agent Orchestration**: Routing, Database Selection, SQL Generation, Validation, Execution, and Fraud Detection
- 🔄 **Retry Logic**: Automatic query regeneration on validation or execution failures
- 🗄️ **MCP Server Integration**: Database operations via FastMCP
- 🎨 **Streamlit Frontend**: User-friendly web interface
- 🔒 **Security**: Read-only SQL queries with validation

## Setup

### Prerequisites

- Python 3.9+
- Google API Key (for Gemini)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd customer_support_maf_2
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
# or with uv:
uv sync
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Running the Application

1. Start the MCP Server:
```bash
cd MCP
uv run --prerelease=allow mcp_server.py
```

2. Start the Backend:
```bash
cd Backend
uv run --prerelease=allow backend.py
```

3. Start the Frontend:
```bash
cd Frontend
streamlit run app.py
```

4. Access the application at `http://localhost:8501`

## Architecture

```
User Query → Routing Agent → Database/Fraud Path
                ↓
         DB Selector → SQL Generator → Validator → SQL Executor (Terminal)
                           ↑              ↓
                           └──── Retry ───┘
```

## Security Notes

⚠️ **IMPORTANT**: Never commit `.env` file to git. The `.gitignore` file already excludes it.
- Use `.env.example` as a template
- Keep your API keys secure
- Rotate keys if accidentally exposed

## License

MIT
# cutomer_support_maf_2
