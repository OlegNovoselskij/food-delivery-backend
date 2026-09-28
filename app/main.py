from fastapi import FastAPI

app = FastAPI(title="Food Delivery API")

@app.get("/health")
def health_check():
    return {"status": "ok"}