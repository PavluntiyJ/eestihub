from fastapi import APIRouter, Response

from app.schemas.planner import BudgetCalculationRequest, BudgetCalculationResponse
from app.services.budget_service import calculate_budget


router = APIRouter(tags=["planner"])


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
