"""
This module provides Domain Based Restriction Policy related API endpoints
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


from src.main import CurrentUser, validate_permissions
from src.utils.models import CreateRestrictionPolicyForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.database import (
    get_restriction_policy_entry_by_id,
    check_domain_organization_mapping,
    export_restriction_policy_entries,
    delete_restriction_policy_entry,
    create_restriction_policy_entry,
    get_restriction_policy_entries,
    edit_restriction_policy_entry,
    PostgresDep
)

# Router
router = APIRouter()


# Create a MailBox Restriction Policy
@router.post("/create/{organization_id}", response_class=JSONResponse, tags=["Restriction Policy Management"], description="Create a new Mail Box Restriction Policy at Domain level")
async def create_mailbox_restriction_policy(organization_id: str, data: CreateRestrictionPolicyForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Mail Box Restriction Policy
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:restriction:create", "policy:restriction:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new restriction policy entry in the database
    await create_restriction_policy_entry(
        db_session=PgDB,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        organization_id=organization_id,
        ip_restrictions=data.ip_restrictions,
        geo_restrictions=data.geo_restrictions,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Domain Based Restriction Policy created successfully"}
    )


# Edit an existing Restriction Policy
@router.put("/edit/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Restriction Policy Management"], description="Edit an existing Restriction Policy List entry at Domain level")
async def edit_restriction_policy(
    policy_id: str,
    organization_id: str,
    data: CreateRestrictionPolicyForm,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Edit an existing Restriction Policy entry for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:restriction:edit", "policy:restriction:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Edit the existing entry in the database
    await edit_restriction_policy_entry(
        db_session=PgDB,
        policy_id=policy_id,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        organization_id=organization_id,
        ip_restrictions=data.ip_restrictions,
        geo_restrictions=data.geo_restrictions,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Restriction Policy entry updated successfully"}
    )


# Get all Restriction Policy List Entries
@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["Restriction Policy Management"], description="Get all Restriction Policy List entries at Organization level")
async def get_restriction_policy_list(organization_id: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Get all Restriction Policy List entries for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:restriction:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all entries from the database
    policies = await get_restriction_policy_entries(db_session=PgDB, organization_id=organization_id, page=page, page_size=page_size, search_query=query)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )



# Export Restriction Policy List Entries
@router.get("/export/{organization_id}", response_class=JSONResponse, tags=["Restriction Policy Management"], description="Export all Restriction Policy List entries at Organization level")
async def export_restriction_policy_list(organization_id: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Export all Restriction Policy List entries for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:restriction:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all entries from the database
    policies = await export_restriction_policy_entries(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Delete a Restriction Policy List Entry
@router.delete("/delete/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Restriction Policy Management"], description="Delete a Restriction Policy List entry at Organization level")
async def delete_restriction_policy(policy_id: str, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a Restriction Policy List entry for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:restriction:delete", "policy:restriction:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the entry from the database
    await delete_restriction_policy_entry(db_session=PgDB, policy_id=policy_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Restriction Policy List entry deleted successfully"}
    )


# Get a Restriction Policy List Entry by ID
@router.get("/get/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Restriction Policy Management"], description="Get a Restriction Policy List entry by ID at Organization level")
async def get_restriction_policy_by_id(
    policy_id: str,
    organization_id: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Get a Restriction Policy List entry by its ID for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:restriction:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the entry from the database
    entry = await get_restriction_policy_entry_by_id(db_session=PgDB, policy_id=policy_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entry
    )
