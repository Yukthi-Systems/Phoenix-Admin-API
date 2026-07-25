"""
This module provides Domain Caution Message related API endpoints
Note: Caution Messages are associated with Organization level, and attached to domains under that organization
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
from src.utils.models import CreateCautionMessageForm
from src.database import (
    export_cautions_under_organization,
    list_cautions_under_organization,
    create_new_caution_entry,
    update_caution_details,
    get_caution_details,
    delete_caution,
    PostgresDep
)

# Router
router = APIRouter()


@router.post("/create", response_class=JSONResponse, tags=["Caution Management"], description="Create a new caution message for the organization")
async def create_caution_message(data: CreateCautionMessageForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new caution message for the organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["caution:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new caution entry in the database
    await create_new_caution_entry(
        db_session=PgDB,
        organization_id=data.associated_organization_id,
        caution_name=data.caution_message_name,
        info=data.info,
        html_content=data.html_content,
        text_content=data.text_content
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Caution message created successfully", "caution_name": data.caution_message_name}
    )


@router.get("/details/{organization_id}/{caution_id}", response_class=JSONResponse, tags=["Caution Management"], description="Get details of a specific caution message")
async def get_caution_details_endpoint(organization_id: str, caution_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific caution message
    """
    # Basic permission checks
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["caution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the caution details from the database
    caution_details = await get_caution_details(db_session=PgDB, organization_id=organization_id, caution_id=caution_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=caution_details
    )


@router.put("/update/{organization_id}/{caution_id}", response_class=JSONResponse, tags=["Caution Management"], description="Update an existing caution message")
async def update_caution_message_endpoint(
    organization_id: str,
    caution_id: str,
    data: CreateCautionMessageForm,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Update an existing caution message
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["caution:edit", "caution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the caution details in the database
    await update_caution_details(
        db_session=PgDB,
        organization_id=organization_id,
        caution_id=caution_id,
        caution_name=data.caution_message_name,
        info=data.info,
        html_content=data.html_content,
        text_content=data.text_content
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Caution message updated successfully", "caution_name": data.caution_message_name}
    )


@router.delete("/delete/{organization_id}/{caution_id}", response_class=JSONResponse, tags=["Caution Management"], description="Delete a caution message")
async def delete_caution_message_endpoint(
    organization_id: str,
    caution_id: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Delete a caution message
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["caution:delete", "caution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the caution from the database
    await delete_caution(db_session=PgDB, organization_id=organization_id, caution_id=caution_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Caution message deleted successfully"}
    )


@router.get("/list/{organization_id}/{page}/{page_size}", response_class=JSONResponse, tags=["Caution Management"], description="List all caution messages for an organization")
async def list_caution_messages_endpoint(organization_id: str, page: int, page_size: int, query: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all caution messages for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["caution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of cautions from the database
    cautions = await list_cautions_under_organization(
        db_session=PgDB,
        organization_id=organization_id,
        search_query=query,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Caution messages listed successfully", "data": cautions}
    )


@router.get("/export/{organization_id}/{page}/{page_size}", response_class=JSONResponse, tags=["Caution Management"], description="Export all caution messages for an organization")
async def export_caution_messages_endpoint(organization_id: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Export all caution messages for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["caution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of cautions from the database
    cautions = await export_cautions_under_organization(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Caution messages exported successfully", "data": cautions}
    )
