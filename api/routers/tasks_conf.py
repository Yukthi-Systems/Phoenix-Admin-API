"""
This module provides Tasks Service related configurations at Organization level
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


from src.utils.models import All_Exceptions, TaskCalServiceConfigUpdateForm, TaskCalUserCreateForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.main import CurrentUser, validate_permissions
from src.database import (
    update_create_tasks_service_settings,
    get_tasks_settings_for_organization,
    list_all_tasks_users_under_domain,
    get_organization_details,
    toggle_tasks_user_status,
    get_domain_details,
    delete_tasks_user,
    create_tasks_user,
    PostgresDep
)


# Router
router = APIRouter()


# Update Tasks Service related configurations
@router.post("/config/update", response_class=JSONResponse, tags=["Tasks (Calendar) Service"], description="Update Tasks Service related configurations at Organization level")
async def update_tasks_service_config(data: TaskCalServiceConfigUpdateForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update Tasks Service related configurations at Organization level
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["tasks_calendar:edit", "tasks_calendar:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=data.organization_id)
    if not organization_details["tasks_service_enabled"]:
        raise All_Exceptions(
            message="Tasks Service is not enabled for this organization, please enable it before updating the configuration",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # If exists, then update, else create a new one (Logic for create is also handled in the same function)
    await update_create_tasks_service_settings(
        db_session=PgDB,
        organization_id=data.organization_id,
        is_external_sharing_enabled=data.is_external_sharing_enabled
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Tasks Service configuration updated successfully"}
    )


# View the Tasks Service configuration for an organization
@router.get("/config/{organization_id}", response_class=JSONResponse, tags=["Tasks (Calendar) Service"], description="View the Tasks Service configuration for an organization")
async def view_tasks_service_config(organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    View the Tasks Service configuration for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["tasks_calendar:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=organization_id)
    if not organization_details["tasks_service_enabled"]:
        raise All_Exceptions(
            message="Tasks Service is not enabled for this organization",
            status_code=status.HTTP_403_FORBIDDEN
        )

    tasks_config = await get_tasks_settings_for_organization(db_session=PgDB, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Tasks Service configuration retrieved successfully",
            "data": tasks_config
        }
    )


# List all Tasks Service users for a domain
@router.get("/users/{domain_name}", response_class=JSONResponse, tags=["Tasks (Calendar) Service"], description="List all Tasks Service users for a domain")
async def list_tasks_users_for_domain(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all Tasks Service users for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["tasks_calendar:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["tasks_service_enabled"]:
        raise All_Exceptions(
            message="Tasks Service is not enabled for this organization, please enable it to view the tasks users",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to list all tasks users for the given domain
    tasks_users = await list_all_tasks_users_under_domain(db_session=PgDB, domain_name=domain_name, page=page, page_size=size)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Tasks users for the domain retrieved successfully",
            "data": tasks_users
        }
    )


# Disable a Tasks user for a domain
@router.put("/user/{domain_name}/disable/{user_email}", response_class=JSONResponse, tags=["Tasks (Calendar) Service"], description="Disable a tasks user for a domain")
async def disable_tasks_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Disable a tasks user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["tasks_calendar:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["tasks_service_enabled"]:
        raise All_Exceptions(
            message="Tasks Service is not enabled for this organization, please enable it to disable the tasks user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to disable the tasks user for the given domain
    await toggle_tasks_user_status(db_session=PgDB, domain_name=domain_name, email=user_email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Tasks user {user_email} for the domain {domain_name} disabled successfully"
        }
    )


# Delete a Tasks user for a domain
@router.delete("/user/{domain_name}/delete/{user_email}", response_class=JSONResponse, tags=["Tasks (Calendar) Service"], description="Delete a Tasks user for a domain")
async def delete_tasks_user_for_domain(domain_name: str, user_email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a tasks user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["tasks_calendar:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["tasks_service_enabled"]:
        raise All_Exceptions(
            message="Tasks Service is not enabled for this organization, please enable it to delete the tasks user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to delete the tasks user for the given domain
    await delete_tasks_user(db_session=PgDB, domain_name=domain_name, email=user_email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Tasks user {user_email} for the domain {domain_name} deleted successfully"
        }
    )


# Create a Tasks user for a domain
@router.post("/user/create", response_class=JSONResponse, tags=["Tasks (Calendar) Service"], description="Create a Tasks user for a domain")
async def create_tasks_user_for_domain(data: TaskCalUserCreateForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a Tasks user for a domain
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=data.domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["tasks_calendar:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get requested organization details
    organization_details = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])
    if not organization_details["tasks_service_enabled"]:
        raise All_Exceptions(
            message="Tasks Service is not enabled for this organization, please enable it to create the tasks user",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Logic to create the tasks user for the given domain
    await create_tasks_user(
        db_session=PgDB,
        domain_name=data.domain_name,
        email=data.email_identity,
        is_enabled=data.enable_user
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"Tasks user {data.email_identity} for the domain {data.domain_name} created successfully"
        }
    )
