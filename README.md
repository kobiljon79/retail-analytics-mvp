# Retail Analytics MVP

Ask natural-language questions about sales, inventory, stock, shrinkage,
and products — get clear business answers powered by PostgreSQL + LLM
(Claude or OpenAI).

## Example Questions

- "What were sales yesterday?"
- "Which products are out of stock?"
- "Which branch had the highest shrinkage?"
- "Which products are overstocked?"

## How It Works

1. You ask a question in plain English via the `/ask` endpoint
2. The LLM converts your question into a SQL query
3. The query runs against PostgreSQL
4. The LLM turns the raw results into a clear, business-friendly answer

## Setup Instructions

### 1. Install PostgreSQL

If you don't have PostgreSQL installed, download it from
https://www.postgresql.org/download/ or use Docker:

```bash
docker run --name retail-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
```

### 2. Create the database and load sample data

```bash
createdb retail_analytics
psql -d retail_analytics -f schema.sql
```

(If using Docker, first `docker exec -it retail-db psql -U postgres -c "CREATE DATABASE retail_analytics;"`
then `docker exec -i retail-db psql -U postgres -d retail_analytics < schema.sql`)

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
- Set your PostgreSQL connection details
- Set `LLM_PROVIDER` to `anthropic` or `openai`
- Add your API key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)

### 5. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### 6. Test it

Open `http://localhost:8000/docs` for interactive API documentation,
or test with curl:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Which products are out of stock?"}'
```

Example response:

```json
{
  "question": "Which products are out of stock?",
  "sql_query": "SELECT p.product_name, b.branch_name FROM inventory i JOIN products p ON i.product_id = p.product_id JOIN branches b ON i.branch_id = b.branch_id WHERE i.stock_quantity = 0;",
  "raw_results": [
    {"product_name": "Pepsi 1.5L", "branch_name": "Downtown Store"},
    {"product_name": "Bananas (kg)", "branch_name": "Westside Mall"}
  ],
  "answer": "Two products are currently out of stock: Pepsi 1.5L at the Downtown Store and Bananas at Westside Mall. These should be restocked as soon as possible."
}
```

## Database Schema

- **products**: product catalog with prices and reorder levels
- **branches**: store locations
- **inventory**: current stock levels per product per branch
- **sales**: daily sales records
- **shrinkage**: lost/damaged/stolen inventory records

Sample data is included in `schema.sql` covering 3 branches, 10 products,
and realistic sales/inventory/shrinkage scenarios so all example
questions return meaningful results immediately.

## Safety

The `/ask` endpoint only allows `SELECT` queries. Any generated SQL
containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`,
or `CREATE` is rejected automatically.

## Extending This MVP

- Add more KPI-specific endpoints (e.g. `/kpi/top-sellers`)
- Add authentication for production use
- Cache common questions to reduce LLM API calls
- Add a simple frontend (Streamlit or React) on top of the `/ask` endpoint
- Add more tables (suppliers, purchase orders, customers)

## Troubleshooting

- **"database connection failed"**: check `.env` values match your
  PostgreSQL setup
- **"Failed to generate SQL"**: check your API key is correct and has
  available credits
- **Empty results**: the LLM-generated SQL may not match your exact
  data — check the `sql_query` field in the response to debug
