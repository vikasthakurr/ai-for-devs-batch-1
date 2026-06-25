"""
Text-to-SQL: Conversational interface for querying e-commerce database.
Non-technical users ask questions in English → LLM generates SQL → executes → returns English answer.
"""
import sqlite3
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Text-to-SQL E-Commerce Assistant")

# Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DB_PATH = "ecommerce.db"


# --- Database Schema (for LLM context) ---
DB_SCHEMA = """
Tables in the e-commerce database:

1. customers (id, name, email, city, joined_date)
2. products (id, name, category, price, stock)
3. orders (id, customer_id, order_date, status, total_amount)
   - status can be: 'delivered', 'shipped', 'processing', 'cancelled'
   - Foreign key: customer_id → customers.id
4. order_items (id, order_id, product_id, quantity, price)
   - Foreign key: order_id → orders.id
   - Foreign key: product_id → products.id
"""


# --- Request/Response Models ---
class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    raw_result: list
    answer: str


# --- Core Functions ---
def generate_sql(question: str) -> str:
    """Use Gemini to convert natural language question to SQL query."""
    prompt = f"""You are a SQL expert. Given the following SQLite database schema,
convert the user's natural language question into a valid SQLite SELECT query.

{DB_SCHEMA}

Rules:
- Return ONLY the SQL query, no explanations or markdown.
- Use only SELECT statements (no INSERT, UPDATE, DELETE, DROP, etc.).
- Use proper JOINs when the question involves multiple tables.
- Use aggregation functions (COUNT, SUM, AVG, MAX, MIN) when appropriate.
- Limit results to 50 rows max unless the user specifies otherwise.
- For date filtering, dates are stored as 'YYYY-MM-DD' text.

User Question: {question}

SQL Query:"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    sql = response.text.strip()
    # Clean up any markdown formatting the model might add
    if sql.startswith("```sql"):
        sql = sql[6:]
    elif sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    return sql.strip()


def execute_sql(sql: str) -> list:
    """Execute SQL query against the database and return results."""
    # Safety check: only allow SELECT statements
    if not sql.strip().upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        # Convert Row objects to dicts
        result = [dict(row) for row in rows]
        return result
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")
    finally:
        conn.close()


def generate_answer(question: str, sql: str, result: list) -> str:
    """Use Gemini to convert raw query results into a human-readable English answer."""
    # Truncate result for the prompt if it's too large
    result_str = str(result[:20])  # Limit to first 20 rows for the prompt

    prompt = f"""You are a helpful data analyst. Given a user's question, the SQL query used, and the raw results, provide a clear, concise English answer. Use bullet points or tables when listing multiple items. Be specific with numbers.

Question: {question}

SQL Query: {sql}

Results: {result_str}

Provide a clear English answer:"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text.strip()


# --- API Endpoints ---
@app.post("/api/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    """
    Main endpoint: accepts natural language question, returns English answer.
    Flow: NLP → SQL → Execute → NLP Response
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Step 1: Convert question to SQL
    sql = generate_sql(question)

    # Step 2: Execute the SQL
    result = execute_sql(sql)

    # Step 3: Generate English answer
    answer = generate_answer(question, sql, result)

    return QueryResponse(
        question=question,
        generated_sql=sql,
        raw_result=result,
        answer=answer
    )


@app.get("/api/schema")
async def get_schema():
    """Return the database schema for reference."""
    return {"schema": DB_SCHEMA}


# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
