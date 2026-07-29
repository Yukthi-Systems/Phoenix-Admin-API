"""
This module provides Mail-Box related API endpoints
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


from src.main import CurrentUser, validate_permissions, assign_new_mailbox_server, delete_email_on_server
from src.utils.models import CreateMailBoxForm, UpdateMailBoxInfoForm
from src.utils.base.libraries import JSONResponse, APIRouter, status
from src.database import (
    update_mailbox_activation_status,
    delete_mailbox_and_update_quota,
    get_all_mailboxes_under_domain,
    fetch_full_id_info_by_admin,
    bulk_export_mailboxes,
    update_mailbox_quota,
    list_only_mailboxes,
    update_mailbox_info,
    get_mailbox_details,
    create_new_mailbox,
    get_domain_details,
    get_identity_info,
    PostgresDep
)


# Router
router = APIRouter()


# Create a new MailBox
@router.post("/create", response_class=JSONResponse, tags=["MailBox Management"], summary="Create a new MailBox")
async def domain_mailbox(data: CreateMailBoxForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new MailBox
    """
    # Get Identity details and domain details
    email_id = data.email_identity.strip().lower()
    identity_info = await get_identity_info(db_session=PgDB, email=email_id)
    domain_info = await get_domain_details(db_session=PgDB, domain_name=identity_info["domain_name"])

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:create", "identity:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Create a new MailBox
    await create_new_mailbox(
        db_session=PgDB,
        email_identity=data.email_identity,
        allocated_quota=data.allocate_quota,
        general_policy_id=data.general_policy_id,
        forwarding_policy_id=data.forwarding_policy_id,
        distribution_policy_id=data.distribution_policy_id,
        domain_name=identity_info["domain_name"],
        org_id=domain_info["managed_by"]
    )

    # After Creation send the details to the RabbitMQ to actually create the MailBox in the mail server
    assign_new_mailbox_server(email_id=email_id)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "MailBox created successfully", "email": email_id}
    )


# Get MailBox details
@router.get("/details/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["MailBox Management"], summary="Get MailBox details")
async def mailbox_details(domain_name: str, email_prefix: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get MailBox details
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)
    identity_info = await get_identity_info(db_session=PgDB, email=f"{email_prefix}@{domain_name}".strip().lower())

    # Identity should be enabled
    if not identity_info["is_enabled"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Identity is not enabled"}
        )

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get MailBox details
    mailbox_details = await get_mailbox_details(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}".strip().lower()
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBox details fetched successfully",
            "mailbox_details": mailbox_details
        }
    )


# Get all available MailBoxes under a domain
@router.get("/list/{domain_name}", response_class=JSONResponse, tags=["MailBox Management"], summary="Get all MailBoxes under a domain")
async def list_mailboxes(domain_name: str, user: CurrentUser, PgDB: PostgresDep, query: str = '', page: int = 1, limit: int = 10) -> JSONResponse:
    """
    Get all MailBoxes under a domain
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get all MailBoxes under the domain
    mailboxes = await get_all_mailboxes_under_domain(
        db_session=PgDB,
        domain_name=domain_name,
        email_search=query.strip().lower(),
        page=page,
        size=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBoxes fetched successfully",
            **mailboxes
        }
    )


# Edit MailBox details
@router.patch("/edit/info/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["MailBox Management"], summary="Edit MailBox details")
async def edit_update_mailbox_info(domain_name: str, email_prefix: str, data: UpdateMailBoxInfoForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit MailBox details
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)
    identity_info = await get_identity_info(db_session=PgDB, email=f"{email_prefix}@{domain_name}".strip().lower())

    # Identity should be enabled
    if not identity_info["is_enabled"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Identity is not enabled"}
        )

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Update MailBox details
    await update_mailbox_info(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}",
        general_policy_id=data.general_policy_id,
        forwarding_policy_id=data.forwarding_policy_id,
        distribution_policy_id=data.distribution_policy_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox updated successfully", "email": f"{email_prefix}@{domain_name}"}
    )


# Activate/Deactivate MailBox
@router.put("/edit/activation/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["MailBox Management"], summary="Activate/Deactivate MailBox")
async def activate_deactivate_mailbox(domain_name: str, email_prefix: str, is_enabled: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Activate or Deactivate a MailBox
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)
    identity_info = await get_identity_info(db_session=PgDB, email=f"{email_prefix}@{domain_name}".strip().lower())

    # Identity should be enabled
    if not identity_info["is_enabled"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Identity is not enabled"}
        )

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Update MailBox activation status
    await update_mailbox_activation_status(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}",
        is_enabled=is_enabled
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox activation status updated successfully", "email": f"{email_prefix}@{domain_name}"}
    )


# Update Quota
@router.patch("/edit/quota/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["MailBox Management"], summary="Update MailBox quota")
async def update_mailbox_quota_value(domain_name: str, email_prefix: str, new_quota_allocated: float, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update MailBox quota
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)
    identity_info = await get_identity_info(db_session=PgDB, email=f"{email_prefix}@{domain_name}".strip().lower())

    # Identity should be enabled
    if not identity_info["is_enabled"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Identity is not enabled"}
        )

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Update MailBox quota
    await update_mailbox_quota(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}",
        domain_name=domain_name,
        org_id=user.organization_id,
        new_quota=new_quota_allocated
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox quota updated successfully", "email": f"{email_prefix}@{domain_name}"}
    )


# Delete MailBox
@router.delete("/delete/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["MailBox Management"], summary="Delete a MailBox")
async def delete_mailbox(domain_name: str, email_prefix: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a MailBox
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Delete MailBox
    server_id = await delete_mailbox_and_update_quota(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}",
        org_id=user.organization_id
    )

    # Delete the email from the server
    delete_email_on_server(email_prefix=email_prefix, domain_name=domain_name, server_id=server_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox deleted successfully", "email": f"{email_prefix}@{domain_name}"}
    )


# Bulk Export MailBoxes
@router.get("/export/{domain_name}", response_class=JSONResponse, tags=["MailBox Management"], summary="Export all MailBoxes under a domain")
async def export_mailboxes(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Export all MailBoxes under a domain
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Bulk export MailBoxes
    mailboxes_data = await bulk_export_mailboxes(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        size=size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBoxes exported successfully",
            "data": mailboxes_data
        }
    )


# Simple search endpoint for MailBoxes as dropdown
@router.get("/search/{domain_name}", response_class=JSONResponse, tags=["MailBox Management"], summary="Search MailBoxes under a domain")
async def search_mailboxes(domain_name: str, query: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Search MailBoxes under a domain for dropdowns
    """
    # Get Domain details
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    # Domain should be active
    if not domain_info["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain is not active"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["mailbox:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Get all MailBoxes under the domain matching the search query
    mailboxes = await list_only_mailboxes(
        db_session=PgDB,
        domain_name=domain_name,
        query=query.strip().lower(),
        page=page,
        size=size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBoxes fetched successfully, use for dropdowns or to validate existence",
            "data": mailboxes
        }
    )


# Admin based Full Details fetch, given a email ID
@router.get("/admin/details/{email_id}", response_class=JSONResponse, tags=["MailBox Management"], summary="Admin fetch MailBox details")
async def admin_mailbox_details(email_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Admin fetch MailBox details
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:admin:view", "mailbox:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Get Full details
    full_info = await fetch_full_id_info_by_admin(db_session=PgDB, email=email_id.strip().lower())

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBox details fetched successfully",
            "data": full_info
        }
    )
