from fastapi import FastAPI
from api.invoice import router as invoice_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AI Invoice Detective",
    description="Corporate IT Accounts Payable Fraud Detection — Rules + IsolationForest + Groq",
    version="1.0.0"
)

app.include_router(invoice_router)


@app.get("/")
def root():
    return {"status": "running", "project": "AI Invoice Detective", "docs": "/docs"}
