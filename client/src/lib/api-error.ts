/**
 * Custom error class for API errors
 * Preserves the structured error response from the API
 */

export interface ApiErrorResponse {
	error: string;
	message: string;
	details?: Record<string, unknown>;
}

export class ApiError extends Error {
	public readonly errorCode: string;
	public readonly details?: Record<string, unknown>;
	public readonly statusCode?: number;

	constructor(errorResponse: ApiErrorResponse | string, statusCode?: number) {
		// If it's a string, use it as the message
		if (typeof errorResponse === "string") {
			super(errorResponse);
			this.errorCode = "UnknownError";
			// Don't set optional properties - leave them undefined
		} else {
			// Use the message field from the API response
			super(errorResponse.message);
			this.errorCode = errorResponse.error;
			if (errorResponse.details !== undefined) {
				this.details = errorResponse.details;
			}
		}

		if (statusCode !== undefined) {
			this.statusCode = statusCode;
		}
		this.name = "ApiError";
	}

	/**
	 * Get a user-friendly error message
	 */
	getUserMessage(): string {
		return this.message;
	}

	/**
	 * Get the full error details for debugging
	 */
	getDebugInfo(): string {
		const parts = [`${this.errorCode}: ${this.message}`];

		if (this.details) {
			parts.push(`Details: ${JSON.stringify(this.details, null, 2)}`);
		}

		if (this.statusCode) {
			parts.push(`Status: ${this.statusCode}`);
		}

		return parts.join("\n");
	}
}

/**
 * Helper to parse error responses from openapi-fetch
 */
export function parseApiError(error: unknown, statusCode?: number): ApiError {
	// If it's already an ApiError, return it
	if (error instanceof ApiError) {
		return error;
	}

	// If it's a structured error response with error/message fields
	if (
		error &&
		typeof error === "object" &&
		"error" in error &&
		"message" in error
	) {
		return new ApiError(error as ApiErrorResponse, statusCode);
	}

	// If it's a regular Error object
	if (error instanceof Error) {
		return new ApiError(error.message, statusCode);
	}

	// Fallback for unknown error types
	return new ApiError(String(error), statusCode);
}
