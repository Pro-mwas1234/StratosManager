"""Domain error types. HTTP/CLI/MCP map these to their own envelopes."""


class StratosError(Exception):
    code = "internal_error"
    http_status = 500

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(StratosError):
    code = "validation_error"
    http_status = 422


class AuthError(StratosError):
    code = "unauthenticated"
    http_status = 401


class ForbiddenError(StratosError):
    code = "forbidden"
    http_status = 403


class NotFoundError(StratosError):
    code = "not_found"
    http_status = 404


class ConflictError(StratosError):
    code = "conflict"
    http_status = 409


class PaymentRequiredError(StratosError):
    """Raised by the entitlement layer when a plan limit/feature blocks an action."""
    code = "payment_required"
    http_status = 402
