from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response schema for all endpoints.

    Attributes:
        success: Boolean indicating if the request was successful
        message: Human-readable message about the response
        data: Optional data payload of any type
    """
    success: bool = Field(...,
                          description="Indicates if the request was successful")
    message: str = Field(...,
                         description="Human-readable message about the response")
    data: Optional[T] = Field(None, description="Response data payload")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "message": "Operation completed successfully",
                    "data": {"result": "example"}
                },
                {
                    "success": False,
                    "message": "An error occurred",
                    "data": None
                }
            ]
        }

    @classmethod
    def success_response(cls, message: str = "Success", data: Optional[T] = None, status_code: int = 200) -> JSONResponse:
        """
        Create a success response with proper HTTP status code.

        Args:
            message: Success message
            data: Optional data to return
            status_code: HTTP status code (default: 200, use 201 for created resources)

        Returns:
            JSONResponse with success=True and appropriate status code
        """
        response = cls(success=True, message=message, data=data)
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump()
        )

    @classmethod
    def error_response(cls, message: str = "An error occurred", data: Optional[T] = None, status_code: int = 400) -> JSONResponse:
        """
        Create an error response with proper HTTP status code.

        Args:
            message: Error message
            data: Optional error details
            status_code: HTTP status code (400=Bad Request, 401=Unauthorized, 403=Forbidden, 404=Not Found, 500=Server Error)

        Returns:
            JSONResponse with success=False and appropriate status code
        """
        response = cls(success=False, message=message, data=data)
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump()
        )
