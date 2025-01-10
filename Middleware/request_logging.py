import logging
import time

logger = logging.getLogger('request_logger')

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        logger.info(
            f"Incoming request: {request.method} {request.path} "
            f"User: {request.user if request.user.is_authenticated else 'Anonymous'} "
            f"Query Params: {request.GET.dict()}"
        )
        
        
        # Record the start time
        start_time = time.time()

        # Process the request
        response = self.get_response(request)

        # Log response details and execution time
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.path} "
            f"Execution Time: {time.time() - start_time:.2f}s"
        )
        return response