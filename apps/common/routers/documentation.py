"""Sphinx documentation endpoints."""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse

from config.logging import get_logger
from config.settings import settings

router = APIRouter()
logger = get_logger(__name__)

# Path to Sphinx documentation build directory
# Note: Sphinx builds HTML files directly in docs/build/, not docs/build/html/
DOCS_BUILD_DIR = Path(__file__).parent.parent.parent.parent / "docs" / "build"


def _rewrite_documentation_paths(html_content: str) -> str:
    """Rewrite relative paths in HTML to absolute paths starting with /documentation/.

    This function rewrites relative paths in href, src, and action attributes to absolute
    paths starting with /documentation/. This ensures all links work correctly when
    served from the /documentation endpoint.

    Examples:
    - href="page.html" -> href="/documentation/page.html"
    - href="./page.html" -> href="/documentation/page.html"
    - src="_static/file.css" -> src="/documentation/_static/file.css"
    - href="#anchor" -> href="#anchor" (anchor links are preserved)
    - href="http://..." -> href="http://..." (external links are preserved)

    Args:
        html_content: Original HTML content with relative paths

    Returns:
        HTML content with rewritten absolute paths
    """

    # Rewrite href attributes (but skip anchor-only links and external links)
    # Match href="relative/path" or href='relative/path' but not href="#anchor" or href="http://..."
    def rewrite_href(match: re.Match[str]) -> str:
        path = match.group(1)
        # Skip anchor-only links (they should stay as-is)
        if path.startswith("#"):
            return match.group(0)
        # Skip external links
        if path.startswith(("http://", "https://", "mailto:", "data:")):
            return match.group(0)
        # Rewrite relative paths
        normalized = path.lstrip("/")
        return f'href="/documentation/{normalized}"'

    html_content = re.sub(
        r'href=["\']([^"\']+)["\']',
        rewrite_href,
        html_content,
    )

    # Rewrite src attributes (for CSS, JS, images)
    def rewrite_src(match: re.Match[str]) -> str:
        path = match.group(1)
        # Skip external links and data URIs
        if path.startswith(("http://", "https://", "data:")):
            return match.group(0)
        # Rewrite relative paths
        normalized = path.lstrip("/")
        return f'src="/documentation/{normalized}"'

    html_content = re.sub(
        r'src=["\']([^"\']+)["\']',
        rewrite_src,
        html_content,
    )

    # Rewrite action attributes (for forms)
    def rewrite_action(match: re.Match[str]) -> str:
        path = match.group(1)
        # Skip external links
        if path.startswith(("http://", "https://")):
            return match.group(0)
        # Rewrite relative paths
        normalized = path.lstrip("/")
        return f'action="/documentation/{normalized}"'

    html_content = re.sub(
        r'action=["\']([^"\']+)["\']',
        rewrite_action,
        html_content,
    )

    return html_content


# Documentation endpoint (if enabled in settings)
# Note: Uses /documentation to avoid conflict with FastAPI's /docs (Swagger UI)
if settings.ENABLE_DOCUMENTATION:

    @router.get(
        "/documentation",
        summary="Documentation",
        description="Sphinx documentation index page",
    )
    async def docs_index() -> HTMLResponse:
        """Serve Sphinx documentation index page with rewritten paths for correct resolution."""
        index_file = DOCS_BUILD_DIR / "index.html"
        if not DOCS_BUILD_DIR.exists() or not index_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation not found. Please run 'python manage.py build-docs' to generate documentation.",
            )

        # Read the HTML file
        html_content = index_file.read_text(encoding="utf-8")

        # Rewrite relative paths to absolute paths starting with /documentation/
        html_content = _rewrite_documentation_paths(html_content)

        return HTMLResponse(content=html_content)

    @router.get(
        "/documentation/{file_path:path}",
        summary="Documentation files",
        description="Serve Sphinx documentation files (HTML, CSS, JS, images, etc.)",
    )
    async def docs_files(file_path: str) -> FileResponse:
        """Serve Sphinx documentation files.

        Handles all documentation files including:
        - HTML pages
        - Static assets (_static directory)
        - Source files (_sources directory)
        - Search index files

        Args:
            file_path: Path to the file relative to docs/build/

        Returns:
            FileResponse with the requested file

        Raises:
            HTTPException: If file is not found or outside allowed directory
        """
        # Check if docs directory exists
        if not DOCS_BUILD_DIR.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation not found. Please run 'python manage.py build-docs' to generate documentation.",
            )

        # Security: Prevent directory traversal
        requested_path = Path(file_path)
        if ".." in file_path or requested_path.is_absolute():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path",
            )

        # Resolve the full path
        full_path = (DOCS_BUILD_DIR / file_path).resolve()

        # Security: Ensure the file is within the docs build directory
        try:
            full_path.relative_to(DOCS_BUILD_DIR.resolve())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}",
            )

        # For HTML files, rewrite relative paths to absolute paths
        if full_path.suffix == ".html":
            html_content = full_path.read_text(encoding="utf-8")
            # Rewrite relative paths to absolute paths starting with /documentation/
            html_content = _rewrite_documentation_paths(html_content)
            return HTMLResponse(content=html_content)

        # Determine media type based on file extension for non-HTML files
        media_type = "text/html"
        if full_path.suffix == ".css":
            media_type = "text/css"
        elif full_path.suffix == ".js":
            media_type = "application/javascript"
        elif full_path.suffix == ".png":
            media_type = "image/png"
        elif full_path.suffix == ".jpg" or full_path.suffix == ".jpeg":
            media_type = "image/jpeg"
        elif full_path.suffix == ".svg":
            media_type = "image/svg+xml"
        elif full_path.suffix == ".json":
            media_type = "application/json"
        elif full_path.suffix == ".txt":
            media_type = "text/plain"

        return FileResponse(
            path=str(full_path),
            media_type=media_type,
        )
