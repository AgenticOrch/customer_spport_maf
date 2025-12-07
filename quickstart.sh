#!/bin/bash
# Quick Start Script for Customer Support MAF System

set -e

PROJECT_DIR="/Users/rahul/Desktop/Gen\ AI/AgenticOrch/Content/customer_support_maf"
VENV_PATH="$PROJECT_DIR/.venv"

echo "🚀 Customer Support Multi-Agent Framework - Quick Start"
echo "========================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "${YELLOW}⚠️  Virtual environment not found. Please run: uv sync --prerelease=allow${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "${YELLOW}⚠️  .env file not found. Creating template...${NC}"
    cat > "$PROJECT_DIR/.env" << 'EOF'
# Google Gemini API Key (or use OpenAI)
GOOGLE_API_KEY=your-api-key-here

# Uncomment below to use OpenAI instead
# OPENAI_API_KEY=your-openai-key-here
EOF
    echo "${BLUE}📝 Please update .env with your API key${NC}"
    echo ""
fi

echo "${BLUE}Select which service(s) to start:${NC}"
echo ""
echo "1) MCP Server only (http://localhost:8001)"
echo "2) Backend API only (http://localhost:8000)"
echo "3) Streamlit Frontend only (http://localhost:8501)"
echo "4) Full Stack (All three - requires 3 terminals)"
echo "5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo "${GREEN}▶️  Starting MCP Server...${NC}"
        cd "$PROJECT_DIR"
        source $VENV_PATH/bin/activate
        python MCP/mcp_server.py
        ;;
    2)
        echo "${GREEN}▶️  Starting Backend API...${NC}"
        cd "$PROJECT_DIR"
        source $VENV_PATH/bin/activate
        python -m uvicorn backend:app --reload --host 0.0.0.0 --port 8000
        ;;
    3)
        echo "${GREEN}▶️  Starting Streamlit Frontend...${NC}"
        cd "$PROJECT_DIR"
        source $VENV_PATH/bin/activate
        streamlit run Frontend/app.py
        ;;
    4)
        echo "${GREEN}▶️  Starting Full Stack...${NC}"
        echo ""
        echo "${YELLOW}📌 Instructions for Full Stack:${NC}"
        echo "1. Open 3 terminals"
        echo ""
        echo "Terminal 1 - MCP Server:"
        echo "  cd $PROJECT_DIR"
        echo "  uv run MCP/mcp_server.py"
        echo ""
        echo "Terminal 2 - Backend API:"
        echo "  cd $PROJECT_DIR"
        echo "  uv run --prerelease=allow backend.py"
        echo ""
        echo "Terminal 3 - Frontend:"
        echo "  cd $PROJECT_DIR"
        echo "  uv run -m streamlit run Frontend/app.py"
        echo ""
        echo "${BLUE}Then access:${NC}"
        echo "  Frontend: http://localhost:8501"
        echo "  API: http://localhost:8000"
        echo "  API Docs: http://localhost:8000/docs"
        echo "  MCP Server: http://localhost:8001/mcp"
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "${YELLOW}Invalid choice${NC}"
        exit 1
        ;;
esac
