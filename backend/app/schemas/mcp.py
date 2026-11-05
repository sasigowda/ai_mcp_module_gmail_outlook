from pydantic import BaseModel, HttpUrl, Field
from typing import Any


class MCPServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    server_type: str = Field(..., min_length=1, max_length=50)
    base_url: str = Field(..., min_length=1)
    description: str | None = None


class MCPServerOut(BaseModel):
    id: str
    name: str
    server_type: str
    base_url: str
    description: str | None
    is_active: bool
    is_connected: bool
    health_status: str
    created_at: str

    class Config:
        from_attributes = True


class MCPServerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class MCPToolOut(BaseModel):
    id: str
    name: str
    description: str | None
    input_schema: Any | None
    is_enabled: bool

    class Config:
        from_attributes = True


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    server_id: str


class AuthStatusOut(BaseModel):
    connected: bool
    email: str | None
    name: str | None


class MCPHealthOut(BaseModel):
    server_id: str
    status: str
    health_status: str
