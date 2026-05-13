from fastapi import FastAPI
from .api.v1 import items, vault

app = FastAPI(title="AeroPLM API", version="0.1.0")

app.include_router(items.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(vault.router, prefix="/api/v1/vault", tags=["Vault"])

@app.get("/")
async def root():
    return {"message": "Welcome to AeroPLM API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
