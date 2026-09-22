from math import isfinite
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.schemas.planner import BudgetCalculationRequest, BudgetCalculationResponse
from app.services.budget_service import calculate_budget


def _json_safe(value: Any) -> Any:
    # Validation errors echo the offending input, but a non-finite float
    # (Infinity decoded from 1e400, NaN literals) is not JSON-serializable
    # and would turn the 422 envelope itself into a 500. Replace it with
    # its short name. The payload itself is never logged here.
    if isinstance(value, float) and not isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class PlannerRoute(APIRoute):
    def get_route_handler(self):  # type: ignore[no-untyped-def]
        handler = super().get_route_handler()

        async def json_safe_validation_handler(request: Request):  # type: ignore[no-untyped-def]
            try:
                return await handler(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": _json_safe(jsonable_encoder(exc.errors()))},
                )

        return json_safe_validation_handler


router = APIRouter(tags=["planner"], route_class=PlannerRoute)


@router.post(
    "/planner/budget",
    response_model=BudgetCalculationResponse,
    summary="Monthly and move-in budget for a Tallinn relocation",
    description=(
        "Employment or manual net income with explicit spending, savings and "
        "an editable housing share. Returns both budget limits, the final "
        "housing allowance, seasonal apartment totals and signed remainders, "
        "move-in cash and machine-readable warnings. Estimates only, not "
        "financial advice; no persistence."
    ),
)
def calculate_planner_budget(
    request: BudgetCalculationRequest,
    response: Response,
) -> BudgetCalculationResponse:
    response.headers["Cache-Control"] = "no-store"
    return calculate_budget(request)
