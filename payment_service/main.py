from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from payment_service.api.router import router
from payment_service.core.config import get_settings
from payment_service.core.db.session import get_engine
from payment_service.repositories.tariffs import TariffRepository


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    engine = get_engine()
    try:
        async with engine.begin() as connection:
            await TariffRepository.seed_default_tariffs(connection)
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "payment_service.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
    )
