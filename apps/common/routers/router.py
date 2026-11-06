"""Main router that combines all endpoint modules.

This module imports and combines all router modules into a single router
for the common app. Each endpoint group is organized in its own module:
- root: Root and version endpoints
- health: Health check endpoints
- metrics: Prometheus metrics endpoint
- debug: Debug-only endpoints
- documentation: Sphinx documentation endpoints
"""

from fastapi import APIRouter

from . import debug, documentation, health, metrics, root

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(root.router)
router.include_router(health.router)
router.include_router(metrics.router)
router.include_router(debug.router)
router.include_router(documentation.router)
