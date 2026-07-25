"""
This module provides Maintenance details API endpoints
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


from src.utils.base.libraries import (
    JSONResponse,
    APIRouter,
    status
)
from src.main import (
    validate_permissions,
    CurrentUser
)
from src.database import (
    delete_maintenance_entry,
    update_maintenance_entry,
    create_maintenance_entry,
    get_maintenance_data,
    PostgresDep
)

# Router
router = APIRouter()


# Status of all and maintenance of various dependencies alerting messages
@router.get("/status", response_class=JSONResponse, tags=["Maintenance"], summary="Get Status of All and Maintenance of Various Dependencies")
async def get_status_maintenance(is_active: bool, _: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get status and maintenance information for various dependencies
    No permission checks as this is general information
    """
    maintenance_data: list[dict] = await get_maintenance_data(db_session=PgDB, is_active=is_active)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Status and maintenance information fetched successfully",
            "data": maintenance_data
        }
    )


# Delete maintenance data by ID
@router.delete("/status/{maintenance_id}", response_class=JSONResponse, tags=["Maintenance"], summary="Delete Maintenance Data by ID")
async def delete_maintenance_data(maintenance_id: int, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete maintenance data by ID
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["maintenance:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=current_user.organization_id,
        user_id=None,
        db=PgDB
    )

    await delete_maintenance_entry(db_session=PgDB, maintenance_id=maintenance_id)

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content={"message": "Maintenance data deleted successfully"}
    )


# Edit maintenance data by ID
@router.put("/status/{maintenance_id}", response_class=JSONResponse, tags=["Maintenance"], summary="Update Maintenance Data by ID")
async def update_maintenance_data(maintenance_id: int, maintenance_info: dict, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update maintenance data by ID
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["maintenance:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=current_user.organization_id,
        user_id=None,
        db=PgDB
    )

    updated_maintenance = await update_maintenance_entry(
        db_session=PgDB,
        maintenance_id=maintenance_id,
        title=maintenance_info["title"],
        description=maintenance_info["description"],
        affected=maintenance_info["affected"],
        severity=maintenance_info["severity"],
        type=maintenance_info["type"],
        is_active=maintenance_info["is_active"],
        start_time=maintenance_info["start_time"],
        end_time=maintenance_info["end_time"]
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Maintenance data updated successfully",
            "data": updated_maintenance
        }
    )


# Add new maintenance data
@router.post("/status", response_class=JSONResponse, tags=["Maintenance"], summary="Add New Maintenance Data")
async def add_maintenance_data(maintenance_info: dict, current_user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Add new maintenance data
    """
    await validate_permissions(
        current_user_permissions=current_user.permissions,
        basic_permissions=["maintenance:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=current_user.organization_id,
        accessed_organization_id=current_user.organization_id,
        user_id=None,
        db=PgDB
    )

    new_maintenance = await create_maintenance_entry(
        db_session=PgDB,
        title=maintenance_info["title"],
        description=maintenance_info["description"],
        affected=maintenance_info["affected"],
        severity=maintenance_info["severity"],
        type=maintenance_info["type"],
        is_active=maintenance_info["is_active"],
        start_time=maintenance_info["start_time"],
        end_time=maintenance_info["end_time"]
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Maintenance data added successfully",
            "data": new_maintenance
        }
    )
