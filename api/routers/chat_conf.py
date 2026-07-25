"""
This module provides Chat Service related configurations at Organization level
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


from src.utils.models import ChatServiceConfigUpdateForm, All_Exceptions
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.main import CurrentUser, validate_permissions
from src.database import (
    list_all_chat_users_under_domain,
    get_chat_config_for_organization,
    create_or_update_chat_config,
    get_organization_details,
    toggle_chat_user_status,
    get_domain_details,
    update_chat_quota,
    delete_chat_user,
    create_chat_user,
    PostgresDep
)

# Router
router = APIRouter()


# Update Chat Service related configurations
@router.post("/config/update", response_class=JSONResponse, tags=["Chat Service"], description="Update Chat Service related configurations at Organization level")
async def update_chat_service_config(data: ChatServiceConfigUpdateForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update Chat Service related configurations at Organization level
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["chat:edit", "chat:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=data.organization_id)
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization, please enable it before updating the configuration",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # If exists, then update, else create a new one (Logic for create is also handled in the same function)
    await create_or_update_chat_config(
        db_session=PgDB,
        organization_id=data.organization_id,
        enable_file_sharing=data.enable_file_sharing,
        file_size_limit_mb=data.file_size_limit_mb,
        enable_group_chat=data.enable_group_chat,
        enable_direct_chat=data.enable_direct_chat
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Chat Service configuration updated successfully"}
    )


# Update Chat Service Quota
@router.put("/config/quota/update/{organization_id}", response_class=JSONResponse, tags=["Chat Service"], description="Update Chat Service Quota at Organization level")
async def update_chat_service_quota(organization_id: str, new_quota: float, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update Chat Service Quota at Organization level
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:view", "chat:edit", "chat:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=organization_id)
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization, please enable it before updating the configuration",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # If exists, then update the quota
    await update_chat_quota(
        db_session=PgDB,
        organization_id=organization_id,
        new_quota=new_quota
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Chat Service quota updated successfully"}
    )


# View the Chat Service configuration for an organization
@router.get("/config/{organization_id}", response_class=JSONResponse, tags=["Chat Service"], description="View the Chat Service configuration for an organization")
async def view_chat_service_config(organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    View the Chat Service configuration for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["chat:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=organization_id)
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization",
            status_code=status.HTTP_403_FORBIDDEN
        )

    chat_config = await get_chat_config_for_organization(db_session=PgDB, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Chat Service configuration retrieved successfully",
            "data": chat_config
        }
    )


# List all chat users for a domain
@router.get("/users/{domain_name}", response_class=JSONResponse, tags=["Chat Service"], description="List all chat users for a domain")
async def list_chat_users_for_domain(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all chat users for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["chat:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization, please enable it to view the chat users",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to list all chat users for the given domain
    chat_users = await list_all_chat_users_under_domain(db_session=PgDB, domain_name=domain_name, page=page, page_size=size)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Chat users for the domain retrieved successfully",
            "data": chat_users
        }
    )


# Disable a chat user for a domain
@router.put("/user/{domain_name}/disable/{user_email}", response_class=JSONResponse, tags=["Chat Service"], description="Disable a chat user for a domain")
async def disable_chat_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Disable a chat user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["chat:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization, please enable it to disable the chat user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to disable the chat user for the given domain
    await toggle_chat_user_status(db_session=PgDB, domain_name=domain_name, email=user_email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Chat user {user_email} for the domain {domain_name} disabled successfully"
        }
    )


# Delete a chat user for a domain
@router.delete("/user/{domain_name}/delete/{user_email}", response_class=JSONResponse, tags=["Chat Service"], description="Delete a chat user for a domain")
async def delete_chat_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a chat user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["chat:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization, please enable it to delete the chat user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to delete the chat user for the given domain
    await delete_chat_user(db_session=PgDB, domain_name=domain_name, email=user_email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Chat user {user_email} for the domain {domain_name} deleted successfully"
        }
    )


# Create a chat user for a domain
@router.post("/user/{domain_name}/create", response_class=JSONResponse, tags=["Chat Service"], description="Create a chat user for a domain")
async def create_chat_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a chat user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["chat:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["chat_service_enabled"]:
        raise All_Exceptions(
            message="Chat Service is not enabled for this organization, please enable it to create the chat user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to create the chat user for the given domain
    await create_chat_user(db_session=PgDB, domain_name=domain_name, email=user_email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Chat user {user_email} for the domain {domain_name} created successfully"
        }
    )
