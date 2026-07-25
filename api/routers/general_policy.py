"""
This module provides General Policy related API endpoints
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
from src.utils.models import CreateGeneralPolicyListEntryForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.database import PostgresDep, create_general_policy_entry, edit_general_policy_entry, get_general_policy_entries, delete_general_policy_entry, get_general_policy_entry_by_id, check_domain_organization_mapping, export_general_policy_entries


# Router
router = APIRouter()


# Create a new General Policy List Entry
@router.post("/create/{organization_id}", response_class=JSONResponse, tags=["General Policy Management"], description="Create a new General Policy List entry at Domain level")
async def create_new_general_policy_entry(data: CreateGeneralPolicyListEntryForm, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new General Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:general:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain,
        organization_id=organization_id
    )

    # Create a new entry in the database
    await create_general_policy_entry(
        db_session=PgDB,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain,
        block_all_incoming_emails=data.block_all_incoming_emails,
        block_all_outgoing_emails=data.block_all_outgoing_emails,
        block_all_incoming_domains=data.block_all_incoming_domains,
        block_all_outgoing_domains=data.block_all_outgoing_domains,
        incoming_exception_domains=data.incoming_exception_domains,
        incoming_exception_emails=data.incoming_exception_emails,
        outgoing_exception_domains=data.outgoing_exception_domains,
        outgoing_exception_emails=data.outgoing_exception_emails,
        outgoing_size_limit_mb=data.outgoing_size_limit_mb,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "General Policy List entry created successfully"}
    )


# Edit an existing General Policy List Entry
@router.put("/edit/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["General Policy Management"], description="Edit an existing General Policy List entry at Domain level")
async def edit_general_policy(
    policy_id: str,
    organization_id: str,
    data: CreateGeneralPolicyListEntryForm,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Edit an existing General Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:general:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    await check_domain_organization_mapping(
        db_session=PgDB,
        domain_name=data.domain,
        organization_id=organization_id
    )

    # Edit the existing entry in the database
    await edit_general_policy_entry(
        db_session=PgDB,
        policy_id=policy_id,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain,
        block_all_incoming_emails=data.block_all_incoming_emails,
        block_all_outgoing_emails=data.block_all_outgoing_emails,
        block_all_incoming_domains=data.block_all_incoming_domains,
        block_all_outgoing_domains=data.block_all_outgoing_domains,
        incoming_exception_domains=data.incoming_exception_domains,
        incoming_exception_emails=data.incoming_exception_emails,
        outgoing_exception_domains=data.outgoing_exception_domains,
        outgoing_exception_emails=data.outgoing_exception_emails,
        outgoing_size_limit_mb=data.outgoing_size_limit_mb,
        is_active=data.is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "General Policy List entry updated successfully"}
    )


# Get all General Policy List Entries
@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["General Policy Management"], description="Get all General Policy List entries at Domain level")
async def get_general_policy_list(organization_id: str, domain_name: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Get all General Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:general:view"],
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
    policies = await get_general_policy_entries(db_session=PgDB, domain_name=domain_name, page=page, page_size=page_size, search_query=query)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Export General Policy List Entries
@router.get("/export/{organization_id}", response_class=JSONResponse, tags=["General Policy Management"], description="Export all General Policy List entries at Domain level")
async def export_general_policy_list(organization_id: str, domain_name: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Export all General Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:general:view"],
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
    policies = await export_general_policy_entries(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Delete a General Policy List Entry
@router.delete("/delete/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["General Policy Management"], description="Delete a General Policy List entry at Domain level")
async def delete_general_policy(policy_id: str, domain_name: str, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a General Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:general:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the entry from the database
    await delete_general_policy_entry(db_session=PgDB, policy_id=policy_id, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "General Policy List entry deleted successfully"}
    )


# Get a General Policy List Entry by ID
@router.get("/get/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["General Policy Management"], description="Get a General Policy List entry by ID at Domain level")
async def get_general_policy_by_id(
    policy_id: str,
    organization_id: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Get a General Policy List entry by its ID for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:general:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the entry from the database
    entry = await get_general_policy_entry_by_id(db_session=PgDB, policy_id=policy_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entry
    )
