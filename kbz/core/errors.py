"""Domain error types. HTTP/CLI/MCP map these to their own envelopes."""


class KBZError(Exception):
    code = "internal_error"
    http_status = 500

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(KBZError):
    code = "validation_error"
    http_status = 422


class AuthError(KBZError):
    code = "unauthenticated"
    http_status = 401


class ForbiddenError(KBZError):
    code = "forbidden"
    http_status = 403


class NotFoundError(KBZError):
    code = "not_found"
    http_status = 404


class ConflictError(KBZError):
    code = "conflict"
    http_status = 409


class PaymentRequiredError(KBZError):
    """Raised by the entitlement layer when a plan limit/feature blocks an action."""
    code = "payment_required"
    http_status = 402
