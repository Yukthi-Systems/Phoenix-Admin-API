"""
This module provides Domain Based Distribution Policy related API endpoints
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
from src.utils.models import CreateDistributionPolicyForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.database import (
    get_distribution_policy_entry_by_id,
    check_domain_organization_mapping,
    export_distribution_policy_entries,
    delete_distribution_policy_entry,
    create_distribution_policy_entry,
    get_distribution_policy_entries,
    edit_distribution_policy_entry,
    PostgresDep
)

# Router
router = APIRouter()


# Create a MailBox Distribution Policy
@router.post("/create/{organization_id}", response_class=JSONResponse, tags=["Distribution Policy Management"], description="Create a new Mail Box Distribution Policy at Domain level")
async def create_mailbox_distribution_policy(organization_id: str, data: CreateDistributionPolicyForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new Mail Box Distribution Policy
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:distribution:create", "policy:distribution:view"],
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

    # Create a new distribution policy entry in the database
    await create_distribution_policy_entry(
        db_session=PgDB,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain_name,
        is_active=data.is_active,
        rule_type=data.rule_type.value,
        specific_emails=data.specific_emails,
        internal_members=data.internal_members,
        external_members=data.external_members
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Domain Based Distribution Policy created successfully"}
    )


# Edit an existing Distribution Policy
@router.put("/edit/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Distribution Policy Management"], description="Edit an existing Distribution Policy List entry at Domain level")
async def edit_distribution_policy(
    policy_id: str,
    organization_id: str,
    data: CreateDistributionPolicyForm,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Edit an existing Distribution Policy entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:distribution:edit", "policy:distribution:view"],
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
    await edit_distribution_policy_entry(
        db_session=PgDB,
        policy_id=policy_id,
        policy_name=data.policy_name,
        policy_description=data.policy_description,
        domain_name=data.domain_name,
        is_active=data.is_active,
        rule_type=data.rule_type.value,
        specific_emails=data.specific_emails,
        internal_members=data.internal_members,
        external_members=data.external_members
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Distribution Policy entry updated successfully"}
    )


# Get all Distribution Policy List Entries
@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["Distribution Policy Management"], description="Get all Distribution Policy List entries at Domain level")
async def get_distribution_policy_list(organization_id: str, domain_name: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Get all Distribution Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:distribution:view"],
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
    policies = await get_distribution_policy_entries(db_session=PgDB, domain_name=domain_name, page=page, page_size=page_size, search_query=query)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )



# Export Distribution Policy List Entries
@router.get("/export/{organization_id}", response_class=JSONResponse, tags=["Distribution Policy Management"], description="Export all Distribution Policy List entries at Domain level")
async def export_distribution_policy_list(organization_id: str, domain_name: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, page_size: int = 10) -> JSONResponse:
    """
    Export all Distribution Policy List entries for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:distribution:view"],
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
    policies = await export_distribution_policy_entries(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=policies
    )


# Delete a Distribution Policy List Entry
@router.delete("/delete/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Distribution Policy Management"], description="Delete a Distribution Policy List entry at Domain level")
async def delete_distribution_policy(policy_id: str, domain_name: str, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a Distribution Policy List entry for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:distribution:delete", "policy:distribution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the entry from the database
    await delete_distribution_policy_entry(db_session=PgDB, policy_id=policy_id, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Distribution Policy List entry deleted successfully"}
    )


# Get a Distribution Policy List Entry by ID
@router.get("/get/{organization_id}/{policy_id}", response_class=JSONResponse, tags=["Distribution Policy Management"], description="Get a Distribution Policy List entry by ID at Domain level")
async def get_distribution_policy_by_id(
    policy_id: str,
    organization_id: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Get a Distribution Policy List entry by its ID for a domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["policy:distribution:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the entry from the database
    entry = await get_distribution_policy_entry_by_id(db_session=PgDB, policy_id=policy_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=entry
    )
