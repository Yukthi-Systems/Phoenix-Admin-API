"""
This module provides MailBox Server related API endpoints
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
from src.utils.models import CreateServerForm
from src.utils.base.constants import SERVER_MANAGER_API_MAPS
from src.main import (
    perform_action_on_postfix_server,
    get_pflogsum_report_for_server,
    get_procs_list_for_server,
    get_mail_queue_for_server,
    has_required_permissions,
    parse_pflogsum_report,
    start_new_migration,
    CurrentUser
)
from src.database import (
    check_if_any_migration_in_progress_of_domain,
    check_migration_in_progress_for_mailbox,
    list_migrations_from_source_server_id,
    delete_server_and_related_data,
    quota_recalculation_and_update,
    update_server_active_status,
    do_manual_mailbox_migration,
    get_overall_migration_stats,
    create_new_migration_entry,
    update_mailbox_lock_status,
    get_mailboxes_under_server,
    list_migrations_from_email,
    update_domain_lock_status,
    get_email_server_mappings,
    get_mailbox_lock_status,
    create_new_server_entry,
    get_domain_lock_status,
    update_server_details,
    get_server_details,
    get_servers,
    PostgresDep
)

# Router
router = APIRouter()


# Create a new MailBox Server
@router.post("/create", response_class=JSONResponse, tags=["Server Management"], description="Create a new MailBox Server")
async def create_mailbox_server(data: CreateServerForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "server:create"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to create a new MailBox Server"}
        )

    # Create a new MailBox Server entry
    server_id = await create_new_server_entry(
        db_session=PgDB,
        host_name=data.host_name,
        smtp_port=data.smtp_port,
        server_info=data.server_info,
        is_active=data.is_active,
        is_monitoring=data.is_monitoring,
        is_mailbox_server=data.is_mailbox_server,
        is_accepting_new_mailboxes=data.is_accepting_new_mailboxes,
        quota_allocated=data.quota_allocated,
        quota_utilized=0,  # Initially set to 0
        storage_path=data.storage_path
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "MailBox Server created successfully", "server_id": server_id}
    )


# Get all MailBox Servers
@router.get("/list/{page}/{page_size}", response_class=JSONResponse, tags=["Server Management"], description="Get all MailBox Servers with pagination")
async def get_all_mailbox_servers(page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep, query: str = "") -> JSONResponse:
    """
    Get all MailBox Servers with pagination
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox Servers"}
        )

    # Retrieve all MailBox Servers
    servers = await get_servers(db_session=PgDB, query=query, page=page, page_size=page_size)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=servers
    )


# Get Single MailBox Server details
@router.get("/details/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="Get details of a MailBox Server")
async def get_mailbox_server_details(server_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox Server details"}
        )

    # Retrieve server details
    server_details = await get_server_details(db_session=PgDB, server_id=server_id)

    if not server_details:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "MailBox Server not found"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=server_details
    )


# Enable or disable MailBox Server
@router.patch("/switch/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="Edit details of a MailBox Server")
async def edit_mailbox_server(server_id: str, is_active: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit details of a MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "server:edit"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to activate/deactivate MailBox Servers"}
        )

    # Update server details
    await update_server_active_status(
        db_session=PgDB,
        server_id=server_id,
        is_active=is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox Server active status updated successfully", "server_id": server_id}
    )


# Edit MailBox Server details
@router.put("/edit/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="Edit details of a MailBox Server")
async def edit_mailbox_server(server_id: str, data: CreateServerForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit details of a MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "server:edit"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to edit MailBox Server details"}
        )

    # Update server details
    await update_server_details(
        db_session=PgDB,
        server_id=server_id,
        smtp_port=data.smtp_port,
        server_info=data.server_info,
        is_active=data.is_active,
        is_monitoring=data.is_monitoring,
        is_mailbox_server=data.is_mailbox_server,
        is_accepting_new_mailboxes=data.is_accepting_new_mailboxes,
        quota_allocated=data.quota_allocated,
        storage_path=data.storage_path
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox Server details updated successfully", "server_id": server_id}
    )


# Delete MailBox Server
@router.delete("/delete/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="Delete a MailBox Server")
async def delete_mailbox_server(server_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "server:delete"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to delete MailBox Servers"}
        )

    # Delete the server and its related data
    await delete_server_and_related_data(db_session=PgDB, server_id=server_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox Server deleted successfully along with its related data", "server_id": server_id}
    )


# List all MailBox under a server
@router.get("/list_mailboxes/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="List all MailBoxes under a specific MailBox Server")
async def list_mailboxes_under_server(server_id: str, email_starts_with: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all MailBoxes under a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBoxes under this server"}
        )
    
    # Retrieve all MailBoxes under the specified server
    mailboxes_and_stats = await get_mailboxes_under_server(
        db_session=PgDB,
        server_id=server_id,
        email_starts_with=email_starts_with,
        page=page,
        size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBoxes under the specified server retrieved successfully",
            "data": mailboxes_and_stats,
            "server_id": server_id
        }
    )


# Get all migrations for a MailBox Server
@router.get("/migrations/from/source_server/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="Get all MailBox migrations from a source server")
async def get_mailbox_migrations_from_source_server(server_id: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all MailBox migrations from a specific MailBox Server (Source Server)
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:migration:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox migrations from this server"}
        )

    # Retrieve all migrations from the specified server
    migrations = await list_migrations_from_source_server_id(
        db_session=PgDB,
        server_id=server_id,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBox migrations from the specified server retrieved successfully",
            "data": migrations,
            "source_server_id": server_id
        }
    )


# Do a MailBox migration - bypass all kinds of checks
@router.post("/migrations/manual/{source_server_id}/to/{target_server_id}", response_class=JSONResponse, tags=["Server Management"], description="Start a new MailBox migration (manual bypass)")
async def do_mailbox_migration(
    source_server_id: str,
    target_server_id: str,
    email: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Do a MailBox migration from a source server to a target server (manual bypass)
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:migration:create", "mailbox:migration:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to do a manual MailBox migration"}
        )

    # Start the manual migration process
    await do_manual_mailbox_migration(
        db_session=PgDB,
        email=email,
        source_server_id=source_server_id,
        target_server_id=target_server_id
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "MailBox migration started successfully (manual bypass)"}
    )


# Start a new MailBox migration
@router.post("/migrations/start/{source_server_id}/to/{target_server_id}", response_class=JSONResponse, tags=["Server Management"], description="Start a new MailBox migration")
async def start_mailbox_migration(
    source_server_id: str,
    target_server_id: str,
    email: str,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Start a new MailBox migration from a source server to a target server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:migration:create"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to start a MailBox migration"}
        )

    # Create a new migration entry
    try:
        migration_id = await create_new_migration_entry(
            db_session=PgDB,
            email=email,
            source_server_id=source_server_id,
            target_server_id=target_server_id,
            migration_details={
                "created_by": user.display_name,
            }
        )

        # Start the migration process (RMQ)
        start_new_migration(
            source_server_id=source_server_id,
            target_server_id=target_server_id,
            email_id=email,
            migration_id=migration_id
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "MailBox migration started successfully", "migration_id": migration_id}
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            content={"message": f"Failed to create new migration entry: {e}"}
        )


# Lock/Un-Lock a MailBox
@router.post("/lock/mailbox/{email}", response_class=JSONResponse, tags=["Server Management"], description="Lock/Un-Lock a MailBox on a specific MailBox Server")
async def lock_mailbox(email: str, is_locked: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Lock/Un-Lock a MailBox on a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:edit", "mailbox:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to lock/unlock MailBoxes"}
        )

    # Lock/Un-Lock the MailBox
    await update_mailbox_lock_status(
        db_session=PgDB,
        email=email,
        is_locked=is_locked,
        domain_name=email.split('@')[-1]  # Extract domain from email
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"MailBox {email} locked/unlocked successfully"}
    )


# Lock/Un-Lock a Domain
@router.post("/lock/domain/{domain_name}", response_class=JSONResponse, tags=["Server Management"], description="Lock/Un-Lock a Domain on a specific MailBox Server")
async def lock_domain(domain_name: str, is_locked: bool, locked_servers: list[str], user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Lock/Un-Lock a Domain to a group of MailBox Servers
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "domain:edit", "domain:view", "domain:migration:view", "domain:migration:create"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to lock/unlock Domains"}
        )

    # Lock/Un-Lock the Domain on the specified servers
    await update_domain_lock_status(
        db_session=PgDB,
        is_locked=is_locked,
        domain_name=domain_name,
        locked_servers_group=locked_servers
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Domain {domain_name} locked/unlocked successfully on specified servers"}
    )


# Get the MailBox lock status
@router.get("/lock/status/{email}", response_class=JSONResponse, tags=["Server Management"], description="Get the lock status of a MailBox")
async def get_emailbox_lock_status(email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get the lock status of a MailBox
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox lock status"}
        )

    # Retrieve the lock status of the MailBox
    lock_status = await get_mailbox_lock_status(db_session=PgDB, email=email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "MailBox lock status retrieved successfully", "data": lock_status}
    )


# Check if migration is in progress for a MailBox
@router.get("/migration/status/{email}", response_class=JSONResponse, tags=["Server Management"], description="Check if migration is in progress for a MailBox")
async def check_migration_status(email: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Check if migration is in progress for a MailBox
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:migration:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to check MailBox migration status"}
        )

    # Check if migration is in progress for the specified MailBox
    migration_status = await check_migration_in_progress_for_mailbox(db_session=PgDB, email=email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Migration status retrieved successfully", "data": migration_status}
    )


# Check if migration is in progress for a Domain
@router.get("/migration/domain/status/{domain_name}", response_class=JSONResponse, tags=["Server Management"], description="Check if migration is in progress for a Domain")
async def check_domain_migration_status(domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Check if migration is in progress for a Domain
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "domain:migration:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to check Domain migration status"}
        )

    # Check if migration is in progress for the specified Domain
    migration_status = await check_if_any_migration_in_progress_of_domain(db_session=PgDB, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain migration status retrieved successfully", "data": migration_status}
    )


# Get the domain lock status
@router.get("/lock/domain/status/{domain_name}", response_class=JSONResponse, tags=["Server Management"], description="Get the lock status of a Domain")
async def get_lock_domain_status(domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get the lock status of a Domain
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "domain:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view Domain lock status"}
        )

    # Retrieve the lock status of the Domain
    lock_status = await get_domain_lock_status(db_session=PgDB, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain lock status retrieved successfully", "data": lock_status}
    )


# Get all migrations entries of a mailbox regardless of source server
@router.get("/migrations/from/mailbox/{email}", response_class=JSONResponse, tags=["Server Management"], description="Get all MailBox migrations from a specific MailBox")
async def get_mailbox_migrations_from_email(email: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all MailBox migrations from a specific MailBox
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:migration:view", "mailbox:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox migrations from this MailBox"}
        )

    # Retrieve all migrations for the specified MailBox
    migrations = await list_migrations_from_email(
        db_session=PgDB,
        email=email,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBox migrations from the specified MailBox retrieved successfully",
            "data": migrations,
            "email": email
        }
    )


# Get all migrations stats for a MailBox Server
@router.get("/migrations/stats/{server_id}", response_class=JSONResponse, tags=["Server Management"], description="Get all MailBox migration stats for a specific MailBox Server")
async def get_server_migration_stats(server_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all MailBox migration stats for a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox migration stats"}
        )

    # Retrieve migration stats for the specified server
    migration_stats = await get_overall_migration_stats(
        db_session=PgDB,
        server_id=server_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBox migration stats retrieved successfully",
            "data": migration_stats,
            "server_id": server_id
        }
    )


# Get the Mail Queue from the specified server
@router.get("/mailq/{server_host_id}", response_class=JSONResponse, tags=["Server Management"], description="Get the Mail Queue from a specific MailBox Server")
async def get_mail_queue(server_host_id: str, user: CurrentUser) -> JSONResponse:
    """
    Get the Mail Queue from a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailq:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view the Mail Queue"}
        )

    if not server_host_id in SERVER_MANAGER_API_MAPS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid server host ID provided"}
        )

    # Retrieve the Mail Queue for the specified server
    mail_queue = get_mail_queue_for_server(server_host_name=SERVER_MANAGER_API_MAPS[server_host_id])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Mail Queue retrieved successfully",
            "data": mail_queue,
            "total": len(mail_queue),
            "server_host_name": SERVER_MANAGER_API_MAPS[server_host_id]
        }
    )


# Actions on Mail Queue
@router.post("/mailq/{action}/{server_host_id}", response_class=JSONResponse, tags=["Server Management"], description="Perform actions on the Mail Queue of a specific MailBox Server")
async def do_mail_queue_action(server_host_id: str, action: str, metadata: dict, user: CurrentUser) -> JSONResponse:
    """
    Perform actions on the Mail Queue of a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailq:edit"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to perform actions on the Mail Queue"}
        )

    if not server_host_id in SERVER_MANAGER_API_MAPS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid server host ID provided"}
        )

    if action in ["rm_msg", "hold_msg", "requeue_msg"]:
        message_id = metadata.get("message_id")
        if not message_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": f"Message ID is required for '{action}' action"}
            )

    # Perform the specified action on the Mail Queue
    if action in ["rm_msg", "clear_queue", "flush_queue", "hold_msg", "hold_all", "requeue_msg", "requeue_all", "release_all"]:
        message_id: str = metadata.get("message_id", '')
        perform_action_on_postfix_server(server_host_name=SERVER_MANAGER_API_MAPS[server_host_id], action=action, message_id=message_id)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": f"Action started successfully on the Mail Queue for server {SERVER_MANAGER_API_MAPS[server_host_id]}"}
        )

    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                    "message": "Invalid action specified for Mail Queue",
                    "valid_actions": ["rm_msg", "clear_queue", "flush_queue", "hold_msg", "hold_all", "requeue_msg", "requeue_all"]
                }
            )


# Get Server Mappings for list of email addresses
@router.post("/email/server-mappings", response_class=JSONResponse, tags=["Server Management"], description="Get MailBox Server mappings for a list of email addresses")
async def get_email_mappings_with_server(emails: list[str], user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get MailBox Server mappings for a list of email addresses
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailbox:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view MailBox Server mappings"}
        )

    # Retrieve server mappings for the specified email addresses
    email_server_mappings: dict[str, str] = await get_email_server_mappings(db_session=PgDB, emails=emails)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "MailBox Server mappings retrieved successfully",
            "data": email_server_mappings
        }
    )


# Recalculate and update all quota for Servers and MailBoxes
@router.post("/recalculate/quotas", response_class=JSONResponse, tags=["Server Management"], description="Recalculate and update all quota for Servers and MailBoxes")
async def recalculate_quotas(user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Recalculate and update all quota for Servers and MailBoxes
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:edit", "mailbox:edit"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to recalculate quotas"}
        )
    
    # Recalculate and update quotas
    await quota_recalculation_and_update(db_session=PgDB)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Quotas recalculated and updated successfully for all Servers and MailBoxes"}
    )


# Get the Postfix Logs Summary from the specified server (pflogsumm)
@router.get("/pflogsum/report/{server_host_id}", response_class=JSONResponse, tags=["Server Management"], description="Get the Postfix Logs Summary from a specific MailBox Server")
async def get_pflogsum_report(server_host_id: str, from_when: str, user: CurrentUser) -> JSONResponse:
    """
    Get the Postfix Logs Summary from a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "mailq:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view the Postfix Logs Summary"}
        )

    if not server_host_id in SERVER_MANAGER_API_MAPS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid server host ID provided"}
        )
    
    if from_when not in ["today", "yesterday"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid 'from_when' parameter provided. Valid values are 'today' or 'yesterday'"}
        )

    # Retrieve the Postfix Logs Summary for the specified server
    raw_pflogsum_report = get_pflogsum_report_for_server(server_host_name=SERVER_MANAGER_API_MAPS[server_host_id], which_data=from_when)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Postfix Logs Summary retrieved successfully",
            "raw_report": raw_pflogsum_report,
            "parsed_report": parse_pflogsum_report(raw_report=raw_pflogsum_report),
            "server_host_name": SERVER_MANAGER_API_MAPS[server_host_id]
        }
    )


# Get the Server Process List from the specified server (Like htop/top)
@router.get("/procs/list/{server_host_id}", response_class=JSONResponse, tags=["Server Management"], description="Get the Server Process List from a specific MailBox Server")
async def get_procs_list(server_host_id: str, user: CurrentUser) -> JSONResponse:
    """
    Get the Server Process List from a specific MailBox Server
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["server:view", "dashboard:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to list the Server Processes"}
        )

    if not server_host_id in SERVER_MANAGER_API_MAPS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid server host ID provided"}
        )

    # Retrieve the Server Process List for the specified server
    raw_procs_list = get_procs_list_for_server(server_host_name=SERVER_MANAGER_API_MAPS[server_host_id])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Server Process List retrieved successfully",
            "server_host_name": SERVER_MANAGER_API_MAPS[server_host_id],
            "data": raw_procs_list,
        }
    )
