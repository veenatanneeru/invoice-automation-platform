from fastapi import FastAPI

app = FastAPI(title="Invoice Automation Platform")

@app.get("/health")
def health():
    return {"status": "ok"}
