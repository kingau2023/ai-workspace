from fastapi import FastAPI

from database import check_db_connection

app = FastAPI(
    title="AI Workspace API",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db/health")
def db_health_check():
    result = check_db_connection()
    return {"status": "ok", "database": "connected", "result": result}
