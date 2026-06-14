"""
Retail Analytics MVP — FastAPI Backend
----------------------------------------
Ask natural-language questions about sales, inventory, stock,
shrinkage, and products. The system converts the question into
SQL (via an LLM), runs it against PostgreSQL, and returns a
clear, natural-language answer.

Author: Kobiljon
"""

import os
import logging
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "retail_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

# Choose provider: "openai" or "anthropic"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Retail Analytics MVP")


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def run_sql(query: str):
    """Run a read-only SQL query and return rows as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


# ============================================================
# SCHEMA DESCRIPTION (used for Text-to-SQL prompting)
# ============================================================

SCHEMA_DESCRIPTION = """
Tables:

products(product_id, product_name, category, unit_price, reorder_level)
branches(branch_id, branch_name, city)
inventory(inventory_id, product_id, branch_id, stock_quantity, last_updated)
sales(sale_id, product_id, branch_id, quantity_sold, sale_date, total_amount)
shrinkage(shrinkage_id, product_id, branch_id, quantity_lost, reason, report_date)

Notes:
- "out of stock" means inventory.stock_quantity = 0
- "overstocked" means inventory.stock_quantity > reorder_level * 2
- "below reorder level" means inventory.stock_quantity < reorder_level
- "yesterday" means sale_date = CURRENT_DATE - INTERVAL '1 day'
- Join inventory/sales/shrinkage to products and branches using product_id and branch_id
"""


# ============================================================
# LLM: TEXT -> SQL
# ============================================================

def generate_sql_from_question(question: str) -> str:
    """
    Use an LLM to convert a natural-language question into a SQL query.
    Returns a single SELECT statement as plain text.
    """
    prompt = f"""You are a PostgreSQL expert. Given the following database schema:

{SCHEMA_DESCRIPTION}

Convert this question into a single valid PostgreSQL SELECT query.
Return ONLY the SQL query, no explanation, no markdown formatting.

Question: {question}
"""

    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    elif LLM_PROVIDER == "openai":
        return _call_openai(prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    return _clean_sql(text)


def _call_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content.strip()
    return _clean_sql(text)


def _clean_sql(text: str) -> str:
    """Strip markdown code fences if the model added them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


# ============================================================
# LLM: RESULT -> NATURAL LANGUAGE ANSWER
# ============================================================

def generate_answer_from_results(question: str, results: list) -> str:
    """Turn SQL query results into a clear natural-language answer."""
    prompt = f"""A user asked this business question: "{question}"

The database returned this result (as JSON):
{results}

Write a short, clear answer in plain business English. If the
result is empty, say so clearly. Do not mention SQL or databases.
"""

    if LLM_PROVIDER == "anthropic":
        return _answer_anthropic(prompt)
    else:
        return _answer_openai(prompt)


def _answer_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _answer_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ============================================================
# SAFETY: only allow SELECT queries
# ============================================================

def validate_select_only(sql: str):
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "create"]
    lowered = sql.lower()
    for word in forbidden:
        if word in lowered:
            raise HTTPException(
                status_code=400,
                detail=f"Generated query contains forbidden keyword: {word}",
            )
    if not lowered.strip().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")


# ============================================================
# API MODELS
# ============================================================

class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    question: str
    sql_query: str
    raw_results: list
    answer: str


# ============================================================
# ROUTES
# ============================================================

@app.get("/health")
def health_check():
    try:
        run_sql("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    """
    Main endpoint: ask a natural-language business question,
    get back the generated SQL, raw results, and a plain-English answer.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Generate SQL from the question
    try:
        sql_query = generate_sql_from_question(question)
    except Exception as e:
        logger.error(f"LLM SQL generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL: {e}")

    # 2. Safety check
    validate_select_only(sql_query)

    # 3. Run the query
    try:
        results = run_sql(sql_query)
    except Exception as e:
        logger.error(f"SQL execution failed: {e} | Query: {sql_query}")
        raise HTTPException(status_code=500, detail=f"SQL execution error: {e}")

    # 4. Generate natural-language answer
    try:
        answer = generate_answer_from_results(question, results)
    except Exception as e:
        logger.error(f"LLM answer generation failed: {e}")
        answer = f"Here are the raw results: {results}"

    return AnswerResponse(
        question=question,
        sql_query=sql_query,
        raw_results=results,
        answer=answer,
    )


@app.get("/")
def root():
    return {
        "message": "Retail Analytics MVP API",
        "endpoints": {
            "/health": "Check database connection",
            "/ask": "POST a business question, get an answer (JSON body: {\"question\": \"...\"})",
        },
        "example_questions": [
            "What were sales yesterday?",
            "Which products are out of stock?",
            "Which branch had the highest shrinkage?",
            "Which products are overstocked?",
        ],
    }
