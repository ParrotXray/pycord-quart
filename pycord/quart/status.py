"""
pycord-quart Response Status Classes
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class ResponseData(BaseModel):
    """Response data structure"""

    authenticated: Optional[bool] = None
    user: Optional[Dict[str, Any]] = None
    guilds: Optional[List[Dict[str, Any]]] = None
    total_count: Optional[int] = None
    login_url: Optional[str] = None
    message: Optional[str] = None


class ResponseStatus(BaseModel):
    """Standard response structure"""

    code: int = 200
    success: bool
    message: Optional[str] = None
    data: Optional[ResponseData] = None
    error: Optional[str] = None

    @property
    def to_json(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return self.model_dump(exclude_none=True)
