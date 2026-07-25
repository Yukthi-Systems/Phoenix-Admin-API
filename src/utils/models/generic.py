"""
This module contains the basic models for the application
"""

"""
Copyright (C) 2026 Yukthi Systems Private Limited

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3
as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
version 3 along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""


from src.utils.base.libraries import BaseModel, Field, uuid


class All_Exceptions(Exception):
    """Class for handling wrong input exceptions"""
    def __init__(self , message: str , status_code: int):
        self.message = message
        self.status_code = status_code
        self.traceback_id = str(uuid.uuid4())


class UserSession(BaseModel):
    """
    User session model for API, used to store user session details in cahche
    """
    user_id: str = Field(..., title="User ID", description="Unique identifier for the user")
    display_name: str = Field(..., title="Display Name", description="Display name of the user")
    primary_phone: str = Field(..., title="Primary Phone", description="Primary phone number of the user")
    user_email: str = Field(..., title="User Email", description="Email address of the user")
    user_name: str = Field(..., title="User Name", description="User name of the user")
    organization_id: str = Field(..., title="Organization ID", description="Organization ID of the user")
    permissions: list[str] = Field(..., title="Permissions", description="List of permissions of the user")
    organization_name: str = Field(..., title="Organization Name", description="Name of the organization")
    parent_organization_id: str = Field(..., title="Parent Organization ID", description="Parent organization ID of the user")
    organization_hierarchy_path: list[str] = Field(..., title="Organization Hierarchy Path", description="Organization Hierarchy path of organizations the user has access to")
    csrf_token: str = Field(..., title="CSRF Token", description="CSRF token for the user session")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "user_name": "john_doe",
                "organization_id": "org_123",
                "permissions": ["read", "write"],
                "organization_name": "Example Organization",
                "parent_organization_id": "org_456",
                "organization_hierarchy_path": ["org_123", "org_456"],
                "csrf_token": "csrf_token_example"
            }
        }
