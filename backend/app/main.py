from fastapi import FastAPI
from .api.v1 import items, vault, bom, workflow, fea, traceability, signatures, bom_diff, auth
from .db.session import engine
from .models.plm_models import Base

# Create tables on startup for this demo/scaffold
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AeroPLM API", version="0.1.0")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(items.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(vault.router, prefix="/api/v1/vault", tags=["Vault"])
app.include_router(bom.router, prefix="/api/v1/bom", tags=["BOM"])
app.include_router(bom_diff.router, prefix="/api/v1/bom-diff", tags=["BOM Diff"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["Workflow"])
app.include_router(fea.router, prefix="/api/v1/fea", tags=["FEA"])
app.include_router(traceability.router, prefix="/api/v1/traceability", tags=["Traceability"])
app.include_router(signatures.router, prefix="/api/v1/signatures", tags=["Signatures"])

@app.get("/")
async def root():
    return {"message": "Welcome to AeroPLM API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
