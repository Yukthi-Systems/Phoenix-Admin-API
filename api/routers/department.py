"""
This module provides MailBox Department related API endpoints
Note: Departments are associated with Organization level, and attached to mailboxes under that organization
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


from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.main import CurrentUser, validate_permissions
from src.utils.models import CreateDepartmentForm
from src.database import (
    list_departments_under_organization,
    export_departments_under_org,
    create_new_department_entry,
    update_department_details,
    get_department_details,
    delete_department,
    PostgresDep
)

# Router
router = APIRouter()


# Create a new Department under an Organization
@router.post("/create", response_class=JSONResponse, tags=["Department Management"], description="Create a new Department")
async def create_department(data: CreateDepartmentForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Department under an Organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["department:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new department entry in the database
    await create_new_department_entry(
        db_session=PgDB,
        organization_id=data.associated_organization_id,
        department_name=data.department_name,
        details=data.department_details
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Department created successfully", "department_name": data.department_name}
    )


@router.get("/details/{organization_id}/{department_id}", response_class=JSONResponse, tags=["Department Management"], description="Get details of a specific Department")
async def get_full_department_details(organization_id: str, department_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific Department
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["department:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the department details from the database
    department_details = await get_department_details(
        db_session=PgDB,
        organization_id=organization_id,
        department_id=department_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Department details fetched successfully", "data": department_details}
    )


@router.get("/list/{organization_id}/{page}/{page_size}", response_class=JSONResponse, tags=["Department Management"], description="List all Departments under an Organization")
async def list_departments(organization_id: str, query: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all Departments under an Organization with pagination
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["department:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of departments from the database
    departments = await list_departments_under_organization(
        db_session=PgDB,
        organization_id=organization_id,
        search_query=query,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Departments listed successfully", "data": departments}
    )


@router.get("/export/{organization_id}/{page}/{page_size}", response_class=JSONResponse, tags=["Department Management"], description="Export all Departments under an Organization")
async def export_departments(organization_id: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Export all Departments under an Organization with pagination
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["department:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of departments from the database
    departments = await export_departments_under_org(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Departments exported successfully", "data": departments}
    )


@router.delete("/delete/{organization_id}/{department_id}", response_class=JSONResponse, tags=["Department Management"], description="Delete a Department")
async def delete_department_entry(organization_id: str, department_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a Department
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["department:delete", "department:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the department entry from the database
    await delete_department(
        db_session=PgDB,
        organization_id=organization_id,
        department_id=department_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Department deleted successfully"}
    )


@router.put("/update/{department_id}", response_class=JSONResponse, tags=["Department Management"], description="Update a Department")
async def update_department(department_id: str, data: CreateDepartmentForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update a Department
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["department:edit", "department:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the department details in the database
    await update_department_details(
        db_session=PgDB,
        organization_id=data.associated_organization_id,
        department_id=department_id,
        department_name=data.department_name,
        details=data.department_details
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Department updated successfully", "department_name": data.department_name}
    )
