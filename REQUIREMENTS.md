# System Requirements & Installation

## Overview

The Customer Support Multi-Agent Framework requires multiple components working together:

```
User Browser
    ↓
Streamlit Frontend (Port 8501)
    ↓
FastAPI Backend (Port 8000)
    ↓
Agent Framework & AI Models
    ↓
MCP Server (Port 8001)
    ↓
SQLite Databases
```

## Prerequisites

### System Requirements

- **OS**: macOS (Intel/Apple Silicon), Linux, or Windows
- **Python**: 3.13+
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 2GB free space

### Network Requirements

- Ports available: 8000 (backend), 8001 (MCP), 8501 (frontend)
- Internet connection for AI API calls
- No firewall blocking localhost connections

## Python Environment

### Create Virtual Environment

```bash
# Using uv (recommended)
cd /Users/rahul/Desktop/Gen\ AI/AgenticOrch/Content/customer_support_maf
uv sync --prerelease=allow

# Or using venv
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Verify Installation

```bash
python --version  # Should be 3.13+
uv --version      # Should show uv version
```

## API Keys

### Google Gemini API (Default)

1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Create new API key
4. Add to `.env`:
   ```
   GOOGLE_API_KEY=your-key-here
   ```

### OpenAI API (Alternative)

1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Add to `.env`:
   ```
   OPENAI_API_KEY=your-key-here
   ```
4. Update `backend.py` to use OpenAI client

### Set Environment Variables

**Option 1: Using .env file**
```bash
# Create .env in project root
GOOGLE_API_KEY=sk-...
```

**Option 2: Export in shell**
```bash
export GOOGLE_API_KEY=sk-...
```

**Option 3: Verify it's set**
```bash
echo $GOOGLE_API_KEY  # Should show your key
```

## Database Setup

### Check Existing Databases

```bash
ls -la Databases/
# Should show: orders.db, tickets.db
```

### Create Databases (if needed)

```bash
# From project root
python scripts/create_db_csv.py
```

### Verify Database Integrity

```bash
# Open SQLite CLI
sqlite3 Databases/tickets.db

# Run commands
.tables          # List all tables
.schema          # Show schema
SELECT COUNT(*) FROM tickets_table;  # Check records
.quit
```

## Dependencies

### Core Dependencies

```
agent-framework==1.0.0b251114  # AI Agent Framework
fastapi                         # Web framework
uvicorn                         # ASGI server
streamlit                       # Frontend framework
fastmcp                         # Protocol client
pydantic                        # Data validation
python-dotenv                   # Environment config
httpx                          # HTTP client
aiohttp                        # Async HTTP
azure-identity                 # Azure auth (optional)
azure-ai-projects              # Azure integration (optional)
pandas                         # Data processing (optional)
uvloop                         # Event loop optimization
openai                         # OpenAI SDK
```

### Install Specific Versions

```bash
# With pre-releases allowed
uv pip install --prerelease=allow agent-framework==1.0.0b251114

# Or using requirements.txt
pip install -r requirements.txt
```

## Services Setup

### 1. MCP Server

**Requirements:**
- Python 3.13+
- SQLite databases in `Databases/` folder
- Port 8001 available

**Start:**
```bash
cd /Users/rahul/Desktop/Gen\ AI/AgenticOrch/Content/customer_support_maf
uv run MCP/mcp_server.py
```

**Verify:**
```bash
curl http://localhost:8001/mcp/
```

### 2. Backend API

**Requirements:**
- MCP server running
- Google API key configured
- Port 8000 available
- Python packages installed

**Start:**
```bash
cd /Users/rahul/Desktop/Gen\ AI/AgenticOrch/Content/customer_support_maf
uv run --prerelease=allow backend.py
```

**Verify:**
```bash
curl http://localhost:8000/health
```

**Access Docs:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Frontend

**Requirements:**
- Backend API running
- Port 8501 available
- Streamlit installed

**Start:**
```bash
cd /Users/rahul/Desktop/Gen\ AI/AgenticOrch/Content/customer_support_maf
uv run -m streamlit run Frontend/app.py
```

**Verify:**
- Opens browser automatically to http://localhost:8501

## Port Configuration

### Default Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 8501 | http://localhost:8501 |
| Backend | 8000 | http://localhost:8000 |
| MCP Server | 8001 | http://localhost:8001 |

### Change Port (if needed)

**Backend:**
```python
# In backend.py, change:
uvicorn.run(app, port=9000)
```

**Frontend:**
```bash
streamlit run Frontend/app.py --server.port 9501
```

**MCP Server:**
```python
# In MCP/mcp_server.py, change:
app.run(port=9001)
```

## SSL/HTTPS Setup (Production)

### Generate Self-Signed Certificate

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### Configure Backend for HTTPS

```python
# In backend.py
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    ssl_keyfile="key.pem",
    ssl_certfile="cert.pem",
)
```

## Performance Optimization

### Increase Worker Count

```bash
# Backend (4 workers)
uvicorn backend:app --workers 4 --host 0.0.0.0 --port 8000
```

### Enable Caching

Add Redis for query caching (optional):
```bash
pip install redis
```

### Database Indexing

```sql
-- Add indexes to tickets database
CREATE INDEX idx_customer_name ON tickets_table('Customer Name');
CREATE INDEX idx_status ON tickets_table('Ticket Status');
```

## Troubleshooting

### Import Errors

```bash
# Reinstall dependencies
uv pip install --force-reinstall --no-cache agent-framework

# Or
pip install --force-reinstall --no-cache-dir -r requirements.txt
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
```

### API Key Issues

```bash
# Verify key is set
echo $GOOGLE_API_KEY

# Test API key
curl -H "Authorization: Bearer $GOOGLE_API_KEY" https://generativelanguage.googleapis.com/v1beta/models
```

### Connection Errors

```bash
# Check services are running
curl http://localhost:8000/health
curl http://localhost:8001/mcp/
curl http://localhost:8501
```

### Memory Issues

```bash
# Monitor memory
top -l 1 | head -20

# Reduce model size or batch size
```

## Development Setup

### IDE Configuration

**VS Code:**
- Install Python extension
- Select .venv as interpreter
- Configure Python path to `${workspaceFolder}/.venv/bin/python`

**PyCharm:**
- Open project
- Go to Settings → Python Interpreter
- Select .venv environment

### Debugging

**Backend:**
```python
# Add breakpoints in backend.py
import pdb; pdb.set_trace()
```

**Frontend:**
```python
# Add debug output in Frontend/app.py
st.write("Debug:", variable)
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 backend:app
```

### Using Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Production)

```bash
export GOOGLE_API_KEY=prod-key
export LOG_LEVEL=INFO
export WORKERS=4
export TIMEOUT=60
```

## Security Checklist

- [ ] API keys stored in .env (not in code)
- [ ] Environment variables configured
- [ ] CORS properly configured
- [ ] HTTPS enabled in production
- [ ] Database backups in place
- [ ] Rate limiting configured
- [ ] Input validation enabled
- [ ] SQL injection prevention verified
- [ ] Firewall rules configured
- [ ] Monitoring/logging enabled

## Next Steps

1. ✅ Install Python 3.13+
2. ✅ Create virtual environment: `uv sync --prerelease=allow`
3. ✅ Configure API key in `.env`
4. ✅ Start MCP server: `uv run MCP/mcp_server.py`
5. ✅ Start backend: `uv run --prerelease=allow backend.py`
6. ✅ Start frontend: `uv run -m streamlit run Frontend/app.py`
7. ✅ Open http://localhost:8501

---

**Last Updated:** December 2, 2025
