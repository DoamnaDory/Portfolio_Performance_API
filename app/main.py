from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.domain.services import PortfolioNotFoundError

app = FastAPI(
    title="Portfolio Performance API",
    description="Сервис расчета доходности портфеля",
    version="1.0.0"
)


@app.exception_handler(PortfolioNotFoundError)
async def portfolio_not_found_handler(request: Request,
                                      exc: PortfolioNotFoundError):
    print("Обработчик сработал для портфеля", exc.portfolio_id)
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )


app.include_router(router)
