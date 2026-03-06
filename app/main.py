from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Portfolio Performance API",
    description="Сервис расчета доходности портфеля",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1", tags=["portfolio"])

@app.get("/")
async def main_check():
    return {"response": "Hello World"}