import os
import decimal
import datetime
from typing import List, Tuple, Any

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

APP_TITLE = "Virtual Machines CMDB"

# Read config from environment (injected via Kubernetes)
DB_HOST = os.environ["DB_HOST"]  # from Secret
DB_USER = os.environ["DB_USER"]  # from Secret
DB_PASSWORD = os.environ["DB_PASSWORD"]  # from Secret
DB_NAME = os.environ.get("DB_NAME", "vmdb")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))

# Initialize connection pool
pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=DB_POOL_SIZE,
    dsn=f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}",
)

# Minimal Jinja environment
BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

app = FastAPI(title=APP_TITLE)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def fetch_vm_rows(limit: int) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM public.virtual_machines LIMIT %s", (limit,))
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            return cols, rows
    finally:
        pool.putconn(conn)


def jsonify_value(v: Any):
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return str(v)
    return v


@app.get("/api/virtual-machines", response_class=JSONResponse)
def api_virtual_machines(limit: int = Query(500, ge=1, le=10000)):
    cols, rows = fetch_vm_rows(limit)
    data = [{col: jsonify_value(val) for col, val in zip(cols, r)} for r in rows]
    return JSONResponse(data)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, limit: int = Query(100, ge=1, le=10000)):
    cols, rows = fetch_vm_rows(limit)
    template = jinja_env.get_template("index.html")
    html = template.render(
        title=APP_TITLE,
        columns=cols,
        rows=rows,
        limit=limit,
    )
    return HTMLResponse(html)


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    try:
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return PlainTextResponse("ok", status_code=200)
        finally:
            pool.putconn(conn)
    except Exception as e:
        return PlainTextResponse(f"error: {e}", status_code=500)
