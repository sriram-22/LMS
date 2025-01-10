




        
# class RequestLoggingMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
    
#     def __call__(self, request):
#         logger.info(f"Request Method: {request.method}")
#         logger.info(f"Request Path: {request.path}")
#         logger.info(f"Request Headers: {request.headers}")
#         try:
#             logger.info(f"Request Body: {request.body}")
#         except:
#             logger.info("Request Body: Non-JSON or too large to log safely.")

#         response = self.get_response(request)

#         logger.info(f"Response Status Code: {response.status_code}")
#         return response