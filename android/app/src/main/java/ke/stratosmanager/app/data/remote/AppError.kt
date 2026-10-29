package ke.stratosmanager.app.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Stable mirror of the backend error envelope (docs/API-CONTRACT.md §Error envelope).
 * The server codes are snake_case strings; keep this enum in lockstep with that table.
 */
@Serializable
data class ErrorBody(
    @SerialName("error") val error: ErrorPayload,
)

@Serializable
data class ErrorPayload(
    @SerialName("code") val code: String,
    @SerialName("message") val message: String = "",
    @SerialName("details") val details: Map<String, String> = emptyMap(),
)

/** Machine-readable error codes as emitted by the StratosManager API. */
enum class AppErrorCode(val wire: String) {
    UNAUTHENTICATED("unauthenticated"),
    FORBIDDEN("forbidden"),
    NOT_FOUND("not_found"),
    CONFLICT("conflict"),
    PAYMENT_REQUIRED("payment_required"),
    VALIDATION_ERROR("validation_error"),
    INTERNAL_ERROR("internal_error"),
    UNKNOWN("unknown"),
    ;

    companion object {
        fun from(wire: String?): AppErrorCode =
            entries.firstOrNull { it.wire == wire } ?: UNKNOWN
    }
}

/** Domain-level failure surfaced by repositories to ViewModels. */
class AppError(
    val code: AppErrorCode,
    override val message: String,
    val details: Map<String, String> = emptyMap(),
    val httpStatus: Int = 0,
) : Exception(message) {

    /** 402 → open UpgradeSheet with the meter info. */
    val isPlanLimit: Boolean get() = code == AppErrorCode.PAYMENT_REQUIRED
    val isFeatureLocked: Boolean get() = code == AppErrorCode.FORBIDDEN
    val isAuthExpired: Boolean get() = code == AppErrorCode.UNAUTHENTICATED

    /** e.g. "monthly limit reached for 'products' (200/200)" — used by UpgradeSheet. */
    fun limitInfo(): Triple<String, Int?, Int?>? {
        if (!isPlanLimit) return null
        val metric = details["metric"] ?: return null
        return Triple(metric, details["limit"]?.toIntOrNull(), details["used"]?.toIntOrNull())
    }

    companion object {
        fun fromPayload(p: ErrorPayload, httpStatus: Int) = AppError(
            code = AppErrorCode.from(p.code),
            message = p.message.ifBlank { p.code },
            details = p.details,
            httpStatus = httpStatus,
        )

        fun network(cause: Throwable) = AppError(
            AppErrorCode.UNKNOWN,
            "Can't reach StratosManager — working offline?",
            details = mapOf("cause" to cause.javaClass.simpleName),
        )
    }
}
