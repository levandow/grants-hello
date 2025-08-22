from fastapi import FastAPI

app = FastAPI(title="Hello Grants API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Hello from your local Dockerized API"}
