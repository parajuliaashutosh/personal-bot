"""
HTTP Status Codes Reference for APIResponse

This file documents the standard HTTP status codes used with APIResponse class.
"""

# Success Status Codes (2xx)
HTTP_200_OK = 200                    # Request succeeded
HTTP_201_CREATED = 201               # Resource created successfully
HTTP_202_ACCEPTED = 202              # Request accepted for processing
HTTP_204_NO_CONTENT = 204            # Success but no content to return

# Client Error Status Codes (4xx)
HTTP_400_BAD_REQUEST = 400           # Invalid request format or parameters
HTTP_401_UNAUTHORIZED = 401          # Missing or invalid authentication
HTTP_403_FORBIDDEN = 403             # Authenticated but not authorized
HTTP_404_NOT_FOUND = 404             # Resource not found
HTTP_409_CONFLICT = 409              # Request conflicts with current state
HTTP_422_UNPROCESSABLE_ENTITY = 422  # Validation error
HTTP_429_TOO_MANY_REQUESTS = 429     # Rate limit exceeded

# Server Error Status Codes (5xx)
HTTP_500_INTERNAL_SERVER_ERROR = 500  # Unexpected server error
HTTP_503_SERVICE_UNAVAILABLE = 503   # Service temporarily unavailable


# Usage Examples:
"""
# Success Response (200 OK)
return APIResponse.success_response(
    message="Data retrieved successfully",
    data={"items": [...]},
    status_code=HTTP_200_OK
)

# Created Resource (201 Created)
return APIResponse.success_response(
    message="Resource created successfully",
    data={"id": 123, "name": "New Item"},
    status_code=HTTP_201_CREATED
)

# Bad Request (400)
return APIResponse.error_response(
    message="Invalid input parameters",
    data={"errors": ["Field 'email' is required"]},
    status_code=HTTP_400_BAD_REQUEST
)

# Unauthorized (401)
return APIResponse.error_response(
    message="Invalid or missing API key",
    data=None,
    status_code=HTTP_401_UNAUTHORIZED
)

# Forbidden (403)
return APIResponse.error_response(
    message="You don't have permission to access this resource",
    data=None,
    status_code=HTTP_403_FORBIDDEN
)

# Not Found (404)
return APIResponse.error_response(
    message="Resource not found",
    data={"requested_id": 123},
    status_code=HTTP_404_NOT_FOUND
)

# Internal Server Error (500)
return APIResponse.error_response(
    message="An unexpected error occurred",
    data=None,
    status_code=HTTP_500_INTERNAL_SERVER_ERROR
)
"""
