# test_app.py - TESTE RÁPIDO
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "TESTE - API funcionando"}

@app.get("/health")
async def health():
    return {"status": "ok"}