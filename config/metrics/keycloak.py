"""Keycloak-related Prometheus metrics."""

from prometheus_client import Counter, Histogram

# Keycloak Request Metrics
keycloak_requests_total = Counter(
    "keycloak_requests_total",
    "Total number of Keycloak API requests",
    ["endpoint", "status"],
)

keycloak_request_duration_seconds = Histogram(
    "keycloak_request_duration_seconds",
    "Keycloak API request duration in seconds",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

keycloak_errors_total = Counter(
    "keycloak_errors_total",
    "Total number of Keycloak API errors",
    ["endpoint", "error_type"],
)

# JWKS (JSON Web Key Set) Metrics
keycloak_jwks_fetches_total = Counter(
    "keycloak_jwks_fetches_total",
    "Total number of JWKS fetches from Keycloak",
    ["status"],
)

# Token Introspection Metrics
keycloak_token_introspections_total = Counter(
    "keycloak_token_introspections_total",
    "Total number of token introspections",
    ["status"],
)

# Token Validation Metrics
keycloak_token_validations_total = Counter(
    "keycloak_token_validations_total",
    "Total number of token validations",
    ["status"],
)

keycloak_token_validation_duration_seconds = Histogram(
    "keycloak_token_validation_duration_seconds",
    "Token validation duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

__all__ = [
    "keycloak_requests_total",
    "keycloak_request_duration_seconds",
    "keycloak_errors_total",
    "keycloak_jwks_fetches_total",
    "keycloak_token_introspections_total",
    "keycloak_token_validations_total",
    "keycloak_token_validation_duration_seconds",
]
