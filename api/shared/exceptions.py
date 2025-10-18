"""
Custom Exceptions for Bifrost Integrations Platform

Define custom exception classes for more precise error handling
and consistent error responses across the application.
"""

class BifrostBaseException(Exception):
    """Base exception for all Bifrost-specific errors"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class FileUploadError(BifrostBaseException):
    """Raised when file upload validation or processing fails"""
    def __init__(self, message: str, file_name: str | None = None):
        error_code = "FILE_UPLOAD_ERROR"
        self.file_name = file_name
        super().__init__(message, error_code)


class FormContextError(BifrostBaseException):
    """Raised when form context generation or validation fails"""
    def __init__(self, message: str, form_id: str | None = None):
        error_code = "FORM_CONTEXT_ERROR"
        self.form_id = form_id
        super().__init__(message, error_code)


class WorkflowKeyError(BifrostBaseException):
    """Raised for workflow API key related errors"""
    def __init__(self, message: str, workflow_id: str | None = None):
        error_code = "WORKFLOW_KEY_ERROR"
        self.workflow_id = workflow_id
        super().__init__(message, error_code)


class VisibilityExpressionError(BifrostBaseException):
    """Raised when visibility expression parsing or evaluation fails"""
    def __init__(self, message: str, expression: str | None = None):
        error_code = "VISIBILITY_EXPRESSION_ERROR"
        self.expression = expression
        super().__init__(message, error_code)


class AuthorizationError(BifrostBaseException):
    """Raised when authorization checks fail"""
    def __init__(self, message: str, resource_type: str | None = None):
        error_code = "AUTHORIZATION_ERROR"
        self.resource_type = resource_type
        super().__init__(message, error_code)


class AsyncExecutionError(BifrostBaseException):
    """Raised for async workflow execution errors"""
    def __init__(self, message: str, execution_id: str | None = None):
        error_code = "ASYNC_EXECUTION_ERROR"
        self.execution_id = execution_id
        super().__init__(message, error_code)


class CronScheduleError(BifrostBaseException):
    """Raised for CRON schedule configuration errors"""
    def __init__(self, message: str, schedule_id: str | None = None):
        error_code = "CRON_SCHEDULE_ERROR"
        self.schedule_id = schedule_id
        super().__init__(message, error_code)


class BrandingError(BifrostBaseException):
    """Raised for branding configuration errors"""
    def __init__(self, message: str, org_id: str | None = None):
        error_code = "BRANDING_ERROR"
        self.org_id = org_id
        super().__init__(message, error_code)


def error_to_dict(error: BifrostBaseException) -> dict:
    """
    Convert an exception to a dictionary for API error responses

    Args:
        error: BifrostBaseException instance

    Returns:
        Dictionary representation of the error
    """
    error_dict = {
        "error": error.error_code,
        "message": error.message
    }

    # Add optional metadata
    for attr in ['file_name', 'form_id', 'workflow_id', 'expression', 'resource_type', 'execution_id', 'schedule_id', 'org_id']:
        value = getattr(error, attr, None)
        if value is not None:
            error_dict[attr] = value

    return error_dict