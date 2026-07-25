"""
This module provides Domain Based Forwarding Policy related API endpoints
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
from src.utils.models import CreateForwardingPolicyForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.database import (
    get_forwarding_policy_entry_by_id,
    check_domain_organization_mapping,
    export_forwarding_policy_entries,
    delete_forwarding_policy_entry,
    create_forwarding_policy_entry,
    get_forwarding_policy_entries,
    edit_forwarding_policy_entry,
    PostgresDep
)

# Router
router = APIRouter()


# Create a MailBox Forwarding Policy
@router.post("/create/{organization_id}", response_class=JSONResponse, tags=["Forwarding Policy Management"], description="Create a new Mail Box Forwarding Policy at Domain level")
async def create_mailbox_forwarding_policy(organization_id: str, data: CreateForwardingPolicyForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Mail Box Forwarding Policy
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:forwarding:create", "policy:forwarding:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=organization_id
    )

    # Create a new forwarding policy entry in the database
    await create_forwarding_policy_entry(
        db_session=PgDB,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain_name,
        forward_to_emails=data.forward_to_emails,
        from_emails=data.from_emails,
        subject_contains=data.subject_contains,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Domain Based Forwarding Policy created successfully"}
    )


# Edit an existing Forwarding Policy
@router.put("/edit/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Forwarding Policy Management"], description="Edit an existing Forwarding Policy List entry at Domain level")
async def edit_forwarding_policy(
    policy_id: str,
    organization_id: str,
    data: CreateForwardingPolicyForm,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Edit an existing Forwarding Policy entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:forwarding:edit", "policy:forwarding:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain_name,
        organization_id=organization_id
    )

    # Edit the existing entry in the database
    await edit_forwarding_policy_entry(
        db_session=PgDB,
        policy_id=policy_id,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain_name,
        subject_contains=data.subject_contains,
        from_emails=data.from_emails,
        forward_to_emails=data.forward_to_emails,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Forwarding Policy entry updated successfully"}
    )


# Get all Forwarding Policy List Entries
@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["Forwarding Policy Management"], description="Get all Forwarding Policy List entries at Domain level")
async def get_forwarding_policy_list(organization_id: str, domain_name: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Get all Forwarding Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:forwarding:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=domain_name,
        organization_id=organization_id
    )

    # Fetch all entries from the database
    policies = await get_forwarding_policy_entries(db_session=PgDB, domain_name=domain_name, page=page, page_size=page_size, search_query=query)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )



# Export Forwarding Policy List Entries
@router.get("/export/{organization_id}", response_class=JSONResponse, tags=["Forwarding Policy Management"], description="Export all Forwarding Policy List entries at Domain level")
async def export_forwarding_policy_list(organization_id: str, domain_name: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Export all Forwarding Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:forwarding:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=domain_name,
        organization_id=organization_id
    )

    # Fetch all entries from the database
    policies = await export_forwarding_policy_entries(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Delete a Forwarding Policy List Entry
@router.delete("/delete/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Forwarding Policy Management"], description="Delete a Forwarding Policy List entry at Domain level")
async def delete_forwarding_policy(policy_id: str, domain_name: str, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a Forwarding Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:forwarding:delete", "policy:forwarding:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the entry from the database
    await delete_forwarding_policy_entry(db_session=PgDB, policy_id=policy_id, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Forwarding Policy List entry deleted successfully"}
    )


# Get a Forwarding Policy List Entry by ID
@router.get("/get/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Forwarding Policy Management"], description="Get a Forwarding Policy List entry by ID at Domain level")
async def get_forwarding_policy_by_id(
    policy_id: str,
    organization_id: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Get a Forwarding Policy List entry by its ID for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:forwarding:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the entry from the database
    entry = await get_forwarding_policy_entry_by_id(db_session=PgDB, policy_id=policy_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entry
    )
