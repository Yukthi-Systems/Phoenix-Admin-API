"""
This module provides Domain Disclaimer related API endpoints
Note: Disclaimer's are associated with Organization level, and attached to domains under that organization
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
from src.utils.models import CreateDisclaimerForm
from src.database import (
    get_all_paginated_disclaimers_by_organization,
    get_disclaimer_details_by_id,
    create_new_disclaimer_entry,
    export_disclaimers_by_org,
    update_disclaimer_details,
    delete_disclaimer_by_id,
    PostgresDep
)

# Router
router = APIRouter()


# Create a Domain Disclaimer
@router.post("/create", response_class=JSONResponse, tags=["Disclaimer Management"], description="Create a new Domain Disclaimer")
async def create_domain_disclaimer(data: CreateDisclaimerForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Domain Disclaimer
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["disclaimer:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new disclaimer entry in the database
    await create_new_disclaimer_entry(
        db_session=PgDB,
        organization_id=data.associated_organization_id,
        disclaimer_name=data.disclaimer_name,
        info=data.details,
        html_content=data.html_content,
        text_content=data.text_content
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Domain Disclaimer created successfully"}
    )


@router.get("/list/{organization_id}/{page}/{limit}", response_class=JSONResponse, tags=["Disclaimer Management"], summary="Get list of all Domain Disclaimers under an Organization")
async def list_domain_disclaimers(organization_id: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, limit: int = 10) -> JSONResponse:
    """
    Get a list of all Domain Disclaimers under an Organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["disclaimer:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of disclaimers for the organization
    data = await get_all_paginated_disclaimers_by_organization(
        db_session=PgDB,
        organization_id=organization_id,
        search_query=query,
        page=page,
        limit=limit
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "List of Domain Disclaimers retrieved successfully",
            "data": data
        }
    )


@router.get("/export/{organization_id}/{page}/{limit}", response_class=JSONResponse, tags=["Disclaimer Management"], summary="Export list of all Domain Disclaimers under an Organization")
async def export_domain_disclaimers(organization_id: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, limit: int = 10) -> JSONResponse:
    """
    Export a list of all Domain Disclaimers under an Organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["disclaimer:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of disclaimers for the organization
    data = await export_disclaimers_by_org(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        limit=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Export of Domain Disclaimers retrieved successfully",
            "data": data
        }
    )


@router.get("/details/{organization_id}/{disclaimer_id}", response_class=JSONResponse, tags=["Disclaimer Management"], summary="Get details of a specific Domain Disclaimer")
async def get_domain_disclaimer_details(organization_id: str, disclaimer_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific Domain Disclaimer
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["disclaimer:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the disclaimer details
    data = await get_disclaimer_details_by_id(
        db_session=PgDB,
        organization_id=organization_id,
        disclaimer_id=disclaimer_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Domain Disclaimer details retrieved successfully",
            "data": data
        }
    )


@router.put("/edit/{disclaimer_id}", response_class=JSONResponse, tags=["Disclaimer Management"], summary="Edit a Domain Disclaimer")
async def edit_domain_disclaimer(disclaimer_id: str, data: CreateDisclaimerForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit a Domain Disclaimer
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["disclaimer:view", "disclaimer:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the disclaimer details
    await update_disclaimer_details(
        db_session=PgDB,
        organization_id=data.associated_organization_id,
        disclaimer_id=disclaimer_id,
        disclaimer_name=data.disclaimer_name,
        info=data.details,
        html_content=data.html_content,
        text_content=data.text_content
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain Disclaimer updated successfully"}
    )


@router.delete("/delete/{organization_id}/{disclaimer_id}", response_class=JSONResponse, tags=["Disclaimer Management"], summary="Delete a Domain Disclaimer")
async def delete_domain_disclaimer(organization_id: str, disclaimer_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a Domain Disclaimer
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["disclaimer:delete", "disclaimer:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the disclaimer
    await delete_disclaimer_by_id(
        db_session=PgDB,
        organization_id=organization_id,
        disclaimer_id=disclaimer_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain Disclaimer deleted successfully"}
    )
