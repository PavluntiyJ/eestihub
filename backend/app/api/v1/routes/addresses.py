from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.schemas.addresses import AddressSearchResponse
from app.services.address_service import AddressProviderError, has_controls, search_addresses


NO_STORE = "no-store"


class AddressesRoute(APIRoute):
    def get_route_handler(self):  # type: ignore[no-untyped-def]
        handler = super().get_route_handler()

        async def no_store_validation_handler(request: Request):  # type: ignore[no-untyped-def]
            # Framework validation (missing q and friends) raises before the
            # handler runs, bypassing the injected Response headers — so the
            # no-store envelope for 422 is applied here, scoped to this route.
            # The echoed input is always a string, hence JSON-safe as encoded.
            try:
                return await handler(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": jsonable_encoder(exc.errors())},
                    headers={"Cache-Control": NO_STORE},
                )

        return no_store_validation_handler


router = APIRouter(tags=["addresses"], route_class=AddressesRoute)


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
    request: Request, response: Response, q: str = Query(min_length=1)
) -> AddressSearchResponse:
    response.headers["Cache-Control"] = NO_STORE
    # FastAPI collapses a repeated q into one value, so repetition is
    # rejected explicitly against the raw query params.
    if len(request.query_params.getlist("q")) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_query"},
            headers={"Cache-Control": NO_STORE},
        )
    # Length applies after trimming: padding must not turn a valid
    # 200-character query into a framework rejection.
    query = q.strip()
    if not 3 <= len(query) <= 200 or has_controls(query):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_query"},
            headers={"Cache-Control": NO_STORE},
        )
    try:
        return search_addresses(query)
    except AddressProviderError as exc:
        headers = {"Cache-Control": NO_STORE}
        if exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code},
            headers=headers,
        ) from exc
