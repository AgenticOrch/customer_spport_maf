import asyncio
import json
import re
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_framework import AgentRunEvent, WorkflowBuilder, WorkflowOutputEvent, Executor, handler
from agent_framework import AIFunction, WorkflowContext, HandoffBuilder
from agent_framework.openai import OpenAIChatClient

from fastmcp import Client as FastMCPClient
import os
from dotenv import load_dotenv

load_dotenv()

# ============== Environment Validation =============
def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = ["GOOGLE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please set these in your .env file or environment."
        )
    
    # Warn if API key looks suspicious (too short or contains common test keys)
    api_key = os.getenv("GOOGLE_API_KEY")
    print(f"Using GOOGLE_API_KEY: {api_key[:4]}...{api_key[-4:]}")
    if len(api_key) < 20:
        raise ValueError("GOOGLE_API_KEY appears to be invalid (too short)")

validate_environment()

# ============== Pydantic Models =============
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    status: str
    response: str

# ============== Prompts ==============
DB_SELECTOR_PROMPT = """
You are a Database Selection Agent. Your job is to:
1. List all available databases using the list_databases tool
2. Get the schema for each database using the get_schema tool
3. Analyze the user's question and select the most relevant database
4. Hand off to the SQL Generator with the selected database and schema

Steps:
- Call list_databases to see available databases
- Call get_schema for each database
- Match keywords from the question with table/column names in schemas
- Select the best matching database
- Provide the selected database name and full schema in your response
- Call handoff_to_SQL_Generator with the database name, schema, and original user question

Example response format before handoff:
"I've analyzed the available databases and selected 'orders'. 

Schema for 'orders' database:
CREATE TABLE order_table ('Order ID' TEXT, 'Customer Name' TEXT, 'Food Item' TEXT, 'Category' TEXT, 'Quantity' TEXT, 'Price' TEXT, 'Payment Method' TEXT, 'Order Time' TEXT);
CREATE TABLE orders_table ('Ticket ID' TEXT, 'Customer Name' TEXT, 'Customer Email' TEXT, ...);

Handing off to SQL Generator to create the query."

Then call: handoff_to_SQL_Generator
"""

Prompt_nlp_sql = """
You are an SQL Generator agent. Your job is to convert a natural-language question into a correct, read-only SQL query (SQLite dialect).

Rules:
- Use SELECT only (read-only queries)
- Use LIMIT 50 if no limit is specified
- Use table and column names EXACTLY as they appear in the schema provided by the Database Selector
- Do not assume table or column names; use only what's in the schema
- Generate clean, valid SQL based on the user's question and the provided schema
- If you receive error feedback from Validator or Executor, fix the specific issues mentioned

The Database Selector will provide the database name and schema in its output. Use that information to create the query.

If this is a RETRY (you're receiving error feedback):
1. Analyze the error message
2. Fix the specific issue (wrong table name, missing column, syntax error, etc.)
3. Generate a corrected query

After generating the SQL query:
1. Present the query clearly
2. Call handoff_to_Validator-Agent to validate the query

Example (First attempt):
"Based on your question about female customer orders and the schema provided, I've generated this query:
SELECT COUNT(*) FROM order_table WHERE `Customer Gender` = 'Female'

Now validating the query..."

Example (Retry after error):
"I've corrected the query based on the error feedback. The issue was using single quotes for column names. New query:
SELECT COUNT(*) FROM order_table WHERE `Customer Gender` = 'Female'

Validating the corrected query..."

Then call: handoff_to_Validator-Agent
"""

SQL_EXECUTOR_PROMPT = """
You are a SQL Execution Agent. Your job is to execute validated SQL queries and provide the final formatted response.

Steps:
1. Call the run_sql tool with the database name and SQL query
2. Check the results

If execution SUCCEEDS:
- Extract the data from the results
- Format it into a natural, user-friendly response
- Provide the final answer (DO NOT call any handoff - this is the terminal agent)

If execution FAILS (table doesn't exist, column not found, syntax errors):
- Explain the specific error
- Call handoff_to_SQL_Generator to regenerate the query with the error context

Example (SUCCESS - Terminal Response):
"The total number of orders is 2896."

Example (SUCCESS with multiple rows):
"Found 3 customers:
- John (Order ID: 123)
- Jane (Order ID: 456)
- Bob (Order ID: 789)"

Example (EXECUTION ERROR - Retry):
"Query execution failed: no such table 'orders'. The database has tables 'order_table' and 'orders_table'. Requesting query regeneration..."
Then call: handoff_to_SQL_Generator
"""

Response_Prompt = """
You are a response generator. Your ONLY job is to format query results EXACTLY as they are returned.

CRITICAL RULES - DO NOT BREAK THESE:
1. ONLY format data that was actually returned by the query
2. DO NOT invent, guess, or hallucinate any information
3. DO NOT add columns, names, or values that weren't returned
4. DO NOT make assumptions about missing data
5. If a column doesn't appear in results, do NOT mention it
6. If results are empty, say "No records found matching your criteria"

Input Format:
- status: "success" or "error"
- num_rows: how many records were returned
- results: array of actual database records
- sql_executed: the query that was run

Output Requirements:
- If status is "error": Report the error ONLY
- If num_rows is 0: Say "No records found"
- If results exist: Create a table showing the returned data with actual values from the results
- Include a summary line: "Found X records matching your query"
- Show only the columns and data that were actually returned

DO NOT:
- Invent departments, managers, or any information not in results
- Add formatting that implies data exists when it doesn't
- Make up names or locations
- Hallucinate additional details

Return ONLY the formatted results, no JSON or markdown code fences.
"""

Prompt_validator = """
You are a SQL Validation agent. Validate the SQL query to ensure it is safe and read-only.

Rules:
- Only SELECT queries are allowed
- Disallow: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, REPLACE, EXEC, GRANT, REVOKE, CALL
- Disallow multi-statement SQL (no semicolons separating statements)
- Enforce LIMIT ≤ 1000
- Check for basic syntax issues (missing FROM clause, invalid operators)

If the query is VALID:
1. Note validation passed
2. Call handoff_to_SQL_Executor

If the query is INVALID (dangerous operations, multi-statements, syntax errors):
1. Explain the specific issue
2. Call handoff_to_SQL_Generator to regenerate the query

Example (VALID):
"✓ Query is valid and safe. Proceeding to execution..."
Then call: handoff_to_SQL_Executor

Example (INVALID):
"✗ Query validation failed: Contains INSERT statement which is not allowed. Only SELECT queries are permitted. Requesting query regeneration..."
Then call: handoff_to_SQL_Generator
"""

Prompt_nlp_sql_retry = """
You are an SQL Generator Retry agent. You regenerate SQL queries after validation or execution failures.

Your job:
1. Review the error/feedback from the previous attempt
2. Review the schema and user's original question
3. Generate a corrected SQL query that addresses the issues
4. Hand off to Validator for re-validation

Rules:
- Use SELECT only (read-only)
- Use LIMIT 50 if no limit specified
- Fix the specific issues mentioned in the error
- Use only tables/columns that exist in the schema

After generating the corrected query:
"I've corrected the query based on the feedback. New query:
[SQL query here]
Validating..."

Then call: handoff_to_Validator-Agent
"""

# ============== Constants ==============
MAX_LIMIT = 1000
DEFAULT_USER_LIMIT = 50

# ============== FastAPI App ==============
app = FastAPI(title="Customer Support MAF Backend")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Initialize AI Client ==============
try:
    client_open = OpenAIChatClient(
        model_id="gemini-2.5-flash",
        api_key=os.environ.get("GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
except Exception as e:
    raise RuntimeError(
        f"Failed to initialize AI client: {str(e)}\n"
        f"Please verify your GOOGLE_API_KEY is valid and not compromised.\n"
        f"If the key was leaked, generate a new one from Google Cloud Console."
    )

# ============== Global Variables ==============
mcp = None

# ============== Helper Functions ==============
def enforce_limit(sql: str, max_limit: int = MAX_LIMIT) -> str:
    """Ensure the SQL has a LIMIT; if present, cap it."""
    m = re.search(r"(?i)\blimit\s+(\d+)", sql)
    if m:
        existing = int(m.group(1))
        if existing > max_limit:
            sql = re.sub(r"(?i)\blimit\s+\d+", f"LIMIT {max_limit}", sql)
    else:
        sql = sql.rstrip(";") + f" LIMIT {DEFAULT_USER_LIMIT}"
    return sql

# ============== Context Manager ==============
class ContextManager:
    """Manages context for customer interactions."""
    def __init__(self):
        self.context_store = {}

    def save_context(self, session_id: str, context: Dict[str, Any]):
        self.context_store[session_id] = context

    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.context_store.get(session_id, {})

# Initialize Context Manager
context_manager = ContextManager()

# ============== Routing Agent ==============
ROUTING_PROMPT = """
You are a Triage Agent for customer support. Your job is to analyze the user's query and route it to the appropriate specialist agent using handoff tools.

Available handoff tools:
- handoff_to_Database_Selector: For queries about orders, tickets, products, or any data lookup
- handoff_to_Fraud_Detection_Agent: For queries about fraud, suspicious activity, or security concerns

Rules:
1. If the query is about orders, tickets, products, customers, or any database lookup → Call handoff_to_Database_Selector
2. If the query mentions fraud, scam, suspicious activity → Call handoff_to_Fraud_Detection_Agent
3. For all other queries, provide a helpful response directly

IMPORTANT: You MUST call the appropriate handoff tool. Do not just describe the handoff in text.

Examples:
- "Show me orders from last month" → Call handoff_to_Database_Selector
- "How many tickets are open?" → Call handoff_to_Database_Selector
- "I think there's fraud on my account" → Call handoff_to_Fraud_Detection_Agent
- "What's your refund policy?" → Answer directly
"""

# ============== Fraud Detection Agent ==============
FRAUD_DETECTION_PROMPT = """
You are a Fraud Detection Agent. Your job is to analyze the user's query for potential fraud and provide the final response.

Analyze the query:
- If fraud or scam is mentioned, or suspicious activity, detect as fraud.
- Otherwise, no fraud.

Provide the final response (DO NOT call any handoff - this is a terminal agent):
- If fraud: "Fraud detected: [brief details]. Escalating to Live Support."
- If no fraud: "No fraud detected in your query."
"""

async def fraud_detection_func(query: str) -> Dict[str, Any]:
    """Analyze the query for potential fraud."""
    if "fraud" in query.lower() or "scam" in query.lower():
        return {"fraud_detected": True, "details": "Potential fraud detected in the query."}
    return {"fraud_detected": False, "details": "No fraud detected."}

fraud_detection_tool = AIFunction(
    name="fraud_detection_agent",
    description="Analyze queries for potential fraud",
    func=fraud_detection_func
)

# ============== Setup Workflow ==============
async def setup_workflow():
    """Initialize the workflow with all agents"""
    global mcp
    mcp = FastMCPClient("http://localhost:8001/mcp/")

    async def list_dbs_func():
        async with mcp:
            result = await mcp.call_tool("list_databases", {})
            if result.data:
                return result.data
            elif result.content and result.content[0].text:
                return json.loads(result.content[0].text)
            return {"databases": []}

    async def get_schema_func(db_name: str) -> Dict[str, Any]:
        async with mcp:
            result = await mcp.call_tool("get_schema", {"db_name": db_name})
            if result.data:
                return result.data
            elif result.content and result.content[0].text:
                return json.loads(result.content[0].text)
            return {"schema": []}

    async def run_sql_func(db_name: str, query: str) -> Dict[str, Any]:
        async with mcp:
            result = await mcp.call_tool("run_sql", {"db_name": db_name, "query": query})
            if result.data:
                return result.data
            elif result.content and result.content[0].text:
                return json.loads(result.content[0].text)
            return {"result": [], "error": None}

    # Create AIFunction tools
    list_dbs_tool = AIFunction(
        name="list_databases",
        description="List available SQLite DBs",
        func=list_dbs_func
    )

    get_schema_tool = AIFunction(
        name="get_schema",
        description="Get schema (CREATE TABLE) for a DB",
        func=get_schema_func
    )

    run_sql_tool = AIFunction(
        name="run_sql",
        description="Run SQL query on DB",
        func=run_sql_func
    )

    # Create agents
    # Routing agent - don't provide custom tools, let HandoffBuilder add them
    routing_agent = client_open.create_agent(
        name="Routing Agent",
        instructions=ROUTING_PROMPT,
        tools=[],  # HandoffBuilder will add handoff tools automatically
    )

    fraud_detection_agent = client_open.create_agent(
        name="Fraud Detection Agent",
        instructions=FRAUD_DETECTION_PROMPT,
        tools=[],
    )

    db_selector_agent = client_open.create_agent(
        name="Database Selector",
        instructions=DB_SELECTOR_PROMPT,
        tools=[list_dbs_tool, get_schema_tool],
    )

    sql_generator_agent = client_open.create_agent(
        name="SQL Generator",
        instructions=Prompt_nlp_sql,
        tools=[],
    )

    sql_generator_retry_agent = client_open.create_agent(
        name="SQL Generator Retry",
        instructions=Prompt_nlp_sql_retry,
        tools=[],
    )

    validator_agent = client_open.create_agent(
        name="Validator-Agent",
        instructions=Prompt_validator,
        tools=[],
    )

    sql_executor_agent = client_open.create_agent(
        name="SQL Executor",
        instructions=SQL_EXECUTOR_PROMPT,
        tools=[run_sql_tool],
    )

    # Build handoff workflow following Microsoft Agent Framework pattern
    # Use HandoffBuilder for orchestration with coordinator and specialists
    # Terminal agents: sql_executor_agent and fraud_detection_agent (provide final responses)
    workflow = (
        HandoffBuilder(
            name="customer_support_workflow",
            participants=[
                routing_agent,
                fraud_detection_agent,
                db_selector_agent,
                sql_generator_agent,
                validator_agent,
                sql_executor_agent
            ],
            description="Customer support workflow with routing, fraud detection, and database query capabilities"
        )
        .set_coordinator(routing_agent)
        # Routing agent can handoff to fraud detection or database query path
        .add_handoff(routing_agent, [fraud_detection_agent, db_selector_agent])
        # Database query path with retry logic
        .add_handoff(db_selector_agent, sql_generator_agent)
        .add_handoff(sql_generator_agent, validator_agent)
        # Validator can either proceed to executor OR retry with generator
        .add_handoff(validator_agent, [sql_executor_agent, sql_generator_agent])
        # Executor is terminal (formats final response) OR retries with generator on error
        .add_handoff(sql_executor_agent, sql_generator_agent)
        # Fraud detection agent is terminal (provides final response directly)
        .build()
    )

    return workflow

# ============== API Endpoints ==============

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a user query through the workflow"""
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        # Create a fresh workflow for each request to avoid state issues
        current_workflow = await setup_workflow()
        response_text = ""
        events = await current_workflow.run(request.question)
        for event in events:
            if isinstance(event, AgentRunEvent):
                response_text = event.data
                print(f"{event.executor_id}: {event.data}")

        print(f"{'=' * 60}\nWorkflow Outputs: {events.get_outputs()}")
        # Summarize the final run state (e.g., COMPLETED)
        print("Final state:", events.get_final_state())
        
        return QueryResponse(
            status="success",
            response=response_text.text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/")
async def root():
    return {
        "name": "Customer Support MAF Backend",
        "version": "1.0.0"
    }

# ============== Main ==============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
