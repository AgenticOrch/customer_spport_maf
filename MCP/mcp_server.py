from fastmcp import FastMCP
import sqlite3
import glob
import json
import os

DB_DIR = "/Users/rahul/Desktop/Gen AI/AgenticOrch/Content/customer_support_maf/Databases"

app = FastMCP("mcp-sql1")

def get_db_path(db_name):
    return f"{DB_DIR}/{db_name}.db"


@app.tool()
def list_databases():
    """
    Returns list of available Spider SQLite DBs.
    """
    dbs = [os.path.basename(x).replace(".db", "") for x in glob.glob(DB_DIR + "/*.db")]
    return {"databases": dbs}


@app.tool()
def get_schema(db_name: str):
    """
    Fetch CREATE TABLE schema statements.
    """
    path = get_db_path(db_name)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schema = [row[0] for row in cursor.fetchall()]

    conn.close()
    return {"schema": schema}


@app.tool()
def run_sql(db_name: str, query: str):
    """
    Execute SQL on selected Spider DB.
    """
    path = get_db_path(db_name)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        result = [dict(zip(columns, r)) for r in rows]
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

    return {"result": result}


if __name__ == "__main__":
    app.run(transport="http", host="0.0.0.0", port=8001)