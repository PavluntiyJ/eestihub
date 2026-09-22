from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.schemas.addresses import AddressSearchResponse
from app.services.address_service import AddressProviderError, has_controls, search_addresses


router = APIRouter(tags=["addresses"])


@router.get(
    "/addresses/search",
    response_model=AddressSearchResponse,
    summary="Tallinn address candidates from In-AKS",
    description=(
        "Up to eight Tallinn address candidates for location context: "
        "opaque provider ID, full and short labels, WGS84 coordinates and "
        "match quality. No match is a 200 with an empty candidate list. "
        "Provider outages and local budget exhaustion are 503s with a "
        "machine-readable detail code. No persistence, no salary fields."
    ),
    responses={
        422: {"description": "Query is shorter than 3 or longer than 200 characters"},
        503: {"description": "Address provider unavailable or locally throttled"},
    },
)
def search_tallinn_addresses(
    request: Request, response: Response, q: str = Query(min_length=1, max_length=200)
) -> AddressSearchResponse:
    response.headers["Cache-Control"] = "no-store"
    # FastAPI collapses a repeated q into one value, so repetition is
    # rejected explicitly against the raw query params.
    if len(request.query_params.getlist("q")) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_query"},
        )
    query = q.strip()
    if not 3 <= len(query) <= 200 or has_controls(query):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_query"},
        )
    try:
        return search_addresses(query)
    except AddressProviderError as exc:
        headers = {"Cache-Control": "no-store"}
        if exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code},
            headers=headers,
        ) from exc
