from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="EestiHub API",
        # 0.2.0 — the contract additions of iteration 7: equalize_by and
        # constraints on calculate-taxes, database-aware health, housing
        # trends, and the e-Residency cost endpoint.
        version="0.2.0",
        description=(
            "Locale-neutral API behind EestiHub. Responses carry machine keys "
            "and numbers only; human-readable labels live in the frontend "
            "dictionaries. Money is computed with Decimal and rounded to cents "
            "(ROUND_HALF_UP).\n\n"
            "Tax rates are the 2026 EMTA figures and live in a single "
            "source-annotated module, `app/core/tax_rates.py`. Estimates only — "
            "not tax advice."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
