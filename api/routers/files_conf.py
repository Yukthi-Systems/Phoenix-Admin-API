"""
This module provides File Service related configurations at Organization level
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


from src.utils.models import FileServiceConfigUpdateForm, All_Exceptions, FilesUserCreateForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.main import CurrentUser, validate_permissions
from src.database import (
    get_file_settings_for_organization,
    list_all_files_users_under_domain,
    update_create_files_settings,
    get_organization_details,
    toggle_file_user_status,
    update_file_user_quota,
    get_domain_details,
    create_file_user,
    delete_file_user,
    PostgresDep
)


# Router
router = APIRouter()


# Update File Service related configurations
@router.post("/config/update", response_class=JSONResponse, tags=["File Service"], description="Update File Service related configurations at Organization level")
async def update_file_service_config(data: FileServiceConfigUpdateForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update File Service related configurations at Organization level
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:edit", "file:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=data.organization_id)
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization, please enable it before updating the configuration",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # If exists, then update, else create a new one (Logic for create is also handled in the same function)
    await update_create_files_settings(
        db_session=PgDB,
        organization_id=data.organization_id,
        enable_file_sharing=data.enable_file_sharing,
        enable_file_versioning=data.enable_file_versioning
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "File Service configuration updated successfully"}
    )


# View the File Service configuration for an organization
@router.get("/config/{organization_id}", response_class=JSONResponse, tags=["File Service"], description="View the File Service configuration for an organization")
async def view_file_service_config(organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    View the File Service configuration for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=organization_id)
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization",
            status_code=status.HTTP_403_FORBIDDEN
        )

    file_config = await get_file_settings_for_organization(db_session=PgDB, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "File Service configuration retrieved successfully",
            "data": file_config
        }
    )


# List all Files users for a domain
@router.get("/users/{domain_name}", response_class=JSONResponse, tags=["File Service"], description="List all file users for a domain")
async def list_file_users_for_domain(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all file users for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization, please enable it to view the file users",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to list all file users for the given domain
    file_users = await list_all_files_users_under_domain(db_session=PgDB, domain_name=domain_name, page=page, page_size=size)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "File users for the domain retrieved successfully",
            "data": file_users
        }
    )


# Disable a Files user for a domain
@router.put("/user/{domain_name}/disable/{user_email}", response_class=JSONResponse, tags=["File Service"], description="Disable a file user for a domain")
async def disable_file_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Disable a file user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization, please enable it to disable the file user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to disable the file user for the given domain
    await toggle_file_user_status(db_session=PgDB, domain_name=domain_name, email=user_email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"File user {user_email} for the domain {domain_name} disabled successfully"
        }
    )


# Delete a Files user for a domain
@router.delete("/user/{domain_name}/delete/{user_email}", response_class=JSONResponse, tags=["File Service"], description="Delete a Files user for a domain")
async def delete_file_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a file user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization, please enable it to delete the file user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to delete the file user for the given domain
    await delete_file_user(db_session=PgDB, domain_name=domain_name, email=user_email, organization_id=domain_info["managed_by"])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"File user {user_email} for the domain {domain_name} deleted successfully"
        }
    )


# Create a Files user for a domain
@router.post("/user/create", response_class=JSONResponse, tags=["File Service"], description="Create a Files user for a domain")
async def create_files_user_for_domain(data: FilesUserCreateForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a Files user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=data.domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization, please enable it to create the file user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to create the file user for the given domain
    await create_file_user(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=domain_info["managed_by"],
        email=data.email_identity,
        quota_allocated=data.quota_allocated,
        is_enabled=data.enable_user
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Files user {data.email_identity} for the domain {data.domain_name} created successfully"
        }
    )


# Update a Files user for a domain
@router.put("/user/{domain_name}/quota/{user_email}", response_class=JSONResponse, tags=["File Service"], description="Update a Files user's quota for a domain")
async def update_files_user_quota_for_domain(domain_name: str, user_email: str, new_quota: float, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update a Files user's quota for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["file:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["file_service_enabled"]:
        raise All_Exceptions(
            message="File Service is not enabled for this organization, please enable it to update the file user's quota",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to update the file user's quota for the given domain
    await update_file_user_quota(
        db_session=PgDB,
        domain_name=domain_name,
        organization_id=domain_info["managed_by"],
        email=user_email,
        new_quota_allocated=new_quota
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Files user {user_email} for the domain {domain_name} quota updated successfully"
        }
    )
