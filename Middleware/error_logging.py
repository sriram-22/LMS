import logging

logger = logging.getLogger('error_logger')

class ErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Process the request
            return self.get_response(request)
        except Exception as e:
            # Log unhandled exceptions
            logger.error(
                f"Unhandled exception for {request.method} {request.path}: {str(e)}",
                exc_info=True,
                extra={
                    'user': request.user if request.user.is_authenticated else 'Anonymous',
                    'path': request.path,
                    'method': request.method,
                }
            )
            # Re-raise the exception to maintain default behavior
            raise