import asyncio
import json
import re
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_framework import AgentRunEvent, WorkflowBuilder, WorkflowOutputEvent, Executor, handler
from agent_framework import AIFunction, WorkflowContext
from agent_framework.openai import OpenAIChatClient

from fastmcp import Client as FastMCPClient
import os
from dotenv import load_dotenv

load_dotenv()

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
4. Return the selected database name and its schema

When you receive a user question:
- Call list_databases to see available databases
- Call get_schema for each database
- Match keywords from the question with table/column names in schemas
- Select the best matching database
- Return ONLY a JSON object in this format:
{
  "selected_db": "database_name",
  "schema": "CREATE TABLE statements...",
  "reasoning": "Why this database was selected"
}

IMPORTANT: Always return a valid JSON object. Do not include any markdown, code fences, or explanations outside the JSON.
"""

Prompt_nlp_sql = """
You are an **NLP-to-SQL generation** agent. Your job is to convert a natural-language question into a correct, read-only SQL query (SQLite dialect).

Rules:
- Always output a JSON response with the query
- Do NOT wrap the SQL in markdown or code fences
- Do NOT include explanations or commentary
- Use SELECT only
- Use LIMIT 50 if no limit is specified
- Use table and column names exactly as in the schema snippet provided

Input:
- A user question
- A schema snippet (CREATE TABLE statements)
- Previous selected_db from Database Selector

Output Format MUST be JSON:
{"selected_db": "database_name", "query": "SELECT ... LIMIT 50"}

IMPORTANT: Return ONLY valid JSON, no markdown or extra text.
"""

SQL_EXECUTOR_PROMPT = """
You are a SQL Execution Agent. Your job is to:
1. Receive a SQL query and database name
2. Execute the query using the run_sql tool
3. Format and present the results

When executing:
- Call run_sql with the database name and SQL query
- If there's an error, explain it clearly
- If successful, format the results in a readable way
- Return a JSON object with: 
  - database_used: the database name
  - sql_executed: the SQL query
  - num_rows: number of rows returned
  - results: the query results
  - status: "success" or "error"

Output MUST be valid JSON only, no markdown or extra text.
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
You are a **SQL Validation** agent. Validate the SQL query to ensure it is safe and read-only.

Rules:
- Only SELECT queries are allowed.
- Disallow commands: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, REPLACE, EXEC, GRANT, REVOKE, CALL.
- Disallow multi-statement SQL (i.e., no semicolons that separate statements).
- Enforce that the SQL references only tables/columns that appear in the schema snippet.
- Optionally enforce a LIMIT ≤ 1000.

Input:
- A candidate SQL query (string).
- Schema snippet (for verifying table/column names).

Output MUST be valid JSON:
- If safe: `{ "status": "approved", "selected_db": "database_name", "approved_sql": "<the SQL>" }`
- If unsafe: `{ "status": "rejected", "reason": "<why it was rejected>" }`

IMPORTANT: Return ONLY valid JSON, no markdown or extra text.
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
client_open = OpenAIChatClient(
    model_id="gemini-2.5-flash",
    api_key=os.environ.get("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# ============== Global Variables ==============
workflow = None
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

    final_agent = client_open.create_agent(
        name="final-Agent",
        instructions="""
        You are the final agent in the workflow. Your role is to process the output from the previous agent and present it as a clear and concise final result for the user.

        Guidelines:
        1. If the previous agent's output contains results, summarize the key information in a user-friendly format.
        2. If no results are found, explicitly state that no matching records were retrieved.
        3. Ensure the output is well-structured, easy to understand, and free of unnecessary details.

        Example:
        Input:
        {
        "database_used": "orders",
        "sql_executed": "SELECT count(T1.`Order ID`) FROM order_table AS T1 INNER JOIN orders_table AS T2 ON T1.`Customer Name` = T2.`Customer Name` WHERE T2.`Customer Gender` = 'Female' LIMIT 50",
        "num_rows": 1,
        "results": [
            {
            "count(T1.`Order ID`)": 27
            }
        ],
        "status": "success"
        }

        Output:
        "The total number of orders placed by female customers is 27."

        If no results are found:
        "No matching records were found based on the query."
        """,
        tools=[],
    )

    builder = WorkflowBuilder()
    builder.add_agent(db_selector_agent)
    builder.add_agent(sql_generator_agent)
    builder.add_agent(validator_agent)
    builder.add_agent(sql_executor_agent)
    builder.set_start_executor(db_selector_agent)
    builder.add_edge(db_selector_agent, sql_generator_agent)
    builder.add_edge(sql_generator_agent, validator_agent)
    builder.add_edge(validator_agent, sql_executor_agent)
    builder.add_edge(sql_executor_agent, final_agent)
    
    return builder.build()

# ============== Global Workflow Instance ==============

workflow = None

async def initialize_workflow():
    global workflow
    workflow = await setup_workflow()
    print("✓ Workflow initialized")

# ============== API Endpoints ==============

@app.on_event("startup")
async def startup_event():
    await initialize_workflow()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a user query through the workflow"""
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized")

    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        response_text=""
        events = await workflow.run(request.question)
        for event in events:
            if isinstance(event, AgentRunEvent):
                # print(type(event.data.text))
                response_text=event.data
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
