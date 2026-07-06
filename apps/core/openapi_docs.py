"""OpenAPI/Swagger docs router for developer-only access.

When OPENAPI_DOCS_ACCESS is "developer_only", this router serves /docs,
/redoc, and /openapi.json with authentication and workflow-access-swagger-doc role required.

Note: /docs and /redoc HTML pages load without auth (so users can see the UI),
but /openapi.json requires auth + role (so only authorized users can fetch the schema).
"""

from fastapi import APIRouter, Depends, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from apps.auth.dependencies.auth import get_current_user
from apps.auth.dependencies.rbac import require_roles
from apps.auth.schemas.user import UserInfo

router = APIRouter()

# Role required for accessing OpenAPI docs
REQUIRED_ROLE = "workflow-access-swagger-doc"


@router.get(
    "/openapi.json",
    include_in_schema=False,
    summary="OpenAPI schema (developer only)",
    description="OpenAPI JSON schema. Requires authentication and workflow-access-swagger-doc role.",
)
async def get_openapi_json(
    request: Request,
    _user: UserInfo = Depends(get_current_user),
    __: None = Depends(require_roles(REQUIRED_ROLE)),
) -> JSONResponse:
    """Return OpenAPI schema for developer-only docs.

    This endpoint requires authentication and the workflow-access-swagger-doc role.
    Swagger UI and ReDoc fetch this endpoint to display the API schema.

    Args:
        request: FastAPI request (used to access app.openapi).
        _user: Authenticated user (injected by dependency).
        __: Role check (workflow-access-swagger-doc) (injected by dependency).

    Returns:
        JSONResponse with OpenAPI schema.
    """
    return JSONResponse(content=request.app.openapi())


@router.get(
    "/docs",
    include_in_schema=False,
    summary="Swagger UI (developer only)",
    description="Swagger UI for API docs. HTML page loads without auth, but fetching /openapi.json requires workflow-access-swagger-doc role.",
)
async def get_swagger_ui(
    request: Request,
) -> HTMLResponse:
    """Return Swagger UI HTML for developer-only docs.

    The HTML page itself loads without authentication (so users can see the UI),
    but when Swagger UI tries to fetch /openapi.json, that endpoint requires
    authentication and the workflow-access-swagger-doc role.

    Args:
        request: FastAPI request (used for app title).

    Returns:
        HTMLResponse with Swagger UI.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{request.app.title} - Swagger UI",
    )


@router.get(
    "/redoc",
    include_in_schema=False,
    summary="ReDoc (developer only)",
    description="ReDoc for API docs. HTML page loads without auth, but fetching /openapi.json requires workflow-access-swagger-doc role.",
)
async def get_redoc(
    request: Request,
) -> HTMLResponse:
    """Return ReDoc HTML for developer-only docs.

    The HTML page itself loads without authentication (so users can see the UI),
    but when ReDoc tries to fetch /openapi.json, that endpoint requires
    authentication and the workflow-access-swagger-doc role.

    Args:
        request: FastAPI request (used for app title).

    Returns:
        HTMLResponse with ReDoc.
    """
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{request.app.title} - ReDoc",
    )
