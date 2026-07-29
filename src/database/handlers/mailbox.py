"""
Handles all the Users operations
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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, status, logging
from src.utils.base.constants import DEFAULT_SERVER_ID
from .organization import validate_organization_quota
from .domain import _raise_check_domain_exists
from src.utils.models import All_Exceptions


PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


async def _raise_check_mailbox_exists(db_session: PgSession, exception_message: str, email: str, raise_exception_if_exists: bool = False) -> None:
    """
    Check if the mailbox already exists in the database
    """
    row = await db_session.fetchrow(
        "SELECT 1 FROM mailboxes WHERE email = $1", email
    )

    if row and raise_exception_if_exists:
        raise All_Exceptions(
            message=exception_message,
            status_code=status.HTTP_409_CONFLICT
        )
    elif not row and not raise_exception_if_exists:
        raise All_Exceptions(
            message=exception_message,
            status_code=status.HTTP_404_NOT_FOUND
        )


async def create_new_mailbox(
    db_session: PgSession,
    email_identity: str,
    allocated_quota: float,
    general_policy_id: str | None,
    forwarding_policy_id: str | None,
    distribution_policy_id: str | None,
    domain_name: str,
    org_id: str
) -> None:
    """
    Create a new mailbox in the database
    """
    # Check if the mailbox already exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email_identity,
        raise_exception_if_exists=True,
        exception_message=f"Mailbox with email {email_identity} already exists"
    )

    # Check the space for the organization
    await validate_organization_quota(
        db_session=db_session,
        organization_id=org_id,
        required_storage_quota=allocated_quota,
        required_email_identities=-1
    )

    try:
        # Create a new mailbox
        await db_session.execute(
            """
            INSERT INTO mailboxes (email, domain_name, is_enabled, quota_allocated, quota_utilized_bytes, server_id,
            general_policy_id, forwarding_policy_id, distribution_policy_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            email_identity,
            domain_name,
            False,
            allocated_quota,
            0.0,
            DEFAULT_SERVER_ID,  # Default server ID
            general_policy_id,
            forwarding_policy_id,
            distribution_policy_id
        )

        # Manage the quota for the Organization
        await db_session.execute(
            """
            UPDATE organizations SET quota_utilized = quota_utilized + $1 WHERE organization_id = $2
            """,
            allocated_quota,
            org_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Error creating new mailbox: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def get_mailbox_details(db_session: PgSession, email: str) -> dict:
    """
    Get details of a mailbox by its email address
    """
    # Check if the mailbox exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email,
        raise_exception_if_exists=False,
        exception_message=f"Mailbox with email {email} does not exist"
    )

    # Fetch the mailbox details
    row = await db_session.fetchrow(
        """
        SELECT email, domain_name, is_enabled, quota_allocated, quota_utilized_bytes, general_policy_id,
               total_messages_count, forwarding_policy_id, distribution_policy_id
        FROM mailboxes
        WHERE email = $1
        """,
        email
    )

    return {
        "email": row["email"],
        "domain_name": row["domain_name"],
        "is_enabled": row["is_enabled"],
        "quota_allocated": float(row["quota_allocated"]),
        "quota_utilized_bytes": int(row["quota_utilized_bytes"]),
        "total_messages_count": int(row["total_messages_count"]),
        "general_policy_id": str(row["general_policy_id"]) if row["general_policy_id"] else None,
        "forwarding_policy_id": str(row["forwarding_policy_id"]) if row["forwarding_policy_id"] else None,
        "distribution_policy_id": str(row["distribution_policy_id"]) if row["distribution_policy_id"] else None,
    }


async def get_all_mailboxes_under_domain(db_session: PgSession, email_search: str, domain_name: str, page: int, size: int) -> dict:
    """
    Get all mailboxes under a specific domain
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    count_query = "SELECT COUNT(*) FROM mailboxes WHERE domain_name = $1"
    search_query = """
    SELECT email, is_enabled, quota_allocated, quota_utilized_bytes, total_messages_count
    FROM mailboxes
    WHERE domain_name = $1
    """

    if email_search:
        count_query += f" AND email ILIKE '%{email_search}%'"
        search_query += f" AND email ILIKE '%{email_search}%'"

    search_query += """
    ORDER BY email ASC
    LIMIT $2 OFFSET $3
    """

    try:
        # Fetch all mailboxes under the domain with pagination
        total_rows = await db_session.fetchval(
            count_query,
            domain_name
        )

        if total_rows == 0:
            return {
                "total_rows": 0,
                "mailboxes": []
            }

        rows = await db_session.fetch(
            search_query,
            domain_name,
            size,
            (page - 1) * size
        )

        mailboxes = [
            {
                "email": row["email"],
                "is_enabled": row["is_enabled"],
                "quota_allocated": float(row["quota_allocated"]),
                "quota_utilized_bytes": int(row["quota_utilized_bytes"]),
                "total_messages_count": int(row["total_messages_count"])
            }
            for row in rows
        ]

        return {
            "mailboxes": mailboxes,
            "total_rows": total_rows,
            "total_pages": (total_rows + size - 1) // size,
            "current_page": page,
            "page_size": size
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Error fetching mailboxes under domain {domain_name}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def update_mailbox_info(
    db_session: PgSession,
    email: str,
    general_policy_id: str | None,
    forwarding_policy_id: str | None,
    distribution_policy_id: str | None
) -> None:
    """
    Update mailbox information
    """
    # Check if the mailbox exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email,
        raise_exception_if_exists=False,
        exception_message=f"Mailbox with email {email} does not exist"
    )

    try:
        # Update the mailbox information
        await db_session.execute(
            """
            UPDATE mailboxes
            SET general_policy_id = $1,
                forwarding_policy_id = $2, distribution_policy_id = $3
            WHERE email = $4
            """,
            general_policy_id, forwarding_policy_id, distribution_policy_id, email
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Error updating mailbox {email}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def update_mailbox_activation_status(db_session: PgSession, email: str, is_enabled: bool) -> None:
    """
    Activate or deactivate a mailbox
    """
    # Check if the mailbox exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email,
        raise_exception_if_exists=False,
        exception_message=f"Mailbox with email {email} does not exist"
    )

    try:
        # If the MailBox is attached to default server and is not enabled, then we do not allow to enable it
        row = await db_session.fetchrow(
            "SELECT server_id FROM mailboxes WHERE email = $1", email
        )
        if row and str(row["server_id"]) == DEFAULT_SERVER_ID and is_enabled:
            raise All_Exceptions(
                message=f"Cannot enable mailbox {email} as it is attached to the default server",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Update the activation status of the mailbox
        await db_session.execute(
            """
            UPDATE mailboxes
            SET is_enabled = $1
            WHERE email = $2
            """,
            is_enabled,
            email
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Error updating activation status for mailbox {email}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def update_mailbox_quota(db_session: PgSession, email: str, domain_name: str, org_id: str, new_quota: float) -> None:
    """
    Update the quota for a mailbox
    """
    # Check if the mailbox exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email,
        raise_exception_if_exists=False,
        exception_message=f"Mailbox with email {email} does not exist"
    )

    # Get the current quota and utilized space for the mailbox
    row = await db_session.fetchrow(
        """
        SELECT server_id, quota_allocated, quota_utilized_bytes FROM mailboxes WHERE email = $1
        """,
        email
    )
    if not row:
        raise All_Exceptions(
            message=f"Mailbox with email {email} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    server_id = str(row["server_id"])
    current_quota = float(row["quota_allocated"])   # Quota in GB
    utilized_space = float(int(row["quota_utilized_bytes"]) / 1024**3) if row["quota_utilized_bytes"] else 0.0  # Utilized space in GB

    # Check if the new quota is less than the utilized space
    if new_quota < utilized_space:
        raise All_Exceptions(
            message=f"New quota {new_quota} is less than the utilized space {utilized_space} for mailbox {email}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if the new quota is same as the utilized space
    if new_quota == utilized_space:
        raise All_Exceptions(
            message=f"New quota {new_quota} is the same as the utilized space {utilized_space} for mailbox {email}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if the new quota is the same as the current quota
    if new_quota == current_quota:
        raise All_Exceptions(
            message=f"New quota {new_quota} is the same as the current quota for mailbox {email}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Calculate the required quota for the domain
    # There are only two cases:
    # 1. If the new quota is greater than the current quota, we need to increase the domain quota
    # 2. If the new quota is less than the current quota, we need to decrease the domain quota
    if new_quota > current_quota:   # Case 1
        required_quota = new_quota - current_quota
        # Check the space for the organization
        await validate_organization_quota(
            db_session=db_session,
            organization_id=org_id,
            required_storage_quota=required_quota,
            required_email_identities=-1
        )
    else:   # Case 2
        # No need to validate organization quota if the new quota is less than the current quota
        # That means we are just reducing the quota for the mailbox (and just adding back the quota to the organization)
        pass

    try:
        # Update the mailbox quota
        await db_session.execute(
            """
            UPDATE mailboxes
            SET quota_allocated = $1
            WHERE email = $2
            """,
            new_quota,
            email
        )

        # Update the organization and server quota based on the new mailbox quota
        if new_quota > current_quota:
            await db_session.execute(
                """
                UPDATE organizations SET quota_utilized = quota_utilized + $1 WHERE organization_id = $2
                """,
                new_quota - current_quota,
                org_id
            )
            await db_session.execute(
                """
                UPDATE servers SET quota_utilized = quota_utilized + $1 WHERE server_id = $2
                """,
                new_quota - current_quota,
                server_id
            )

        elif new_quota < current_quota:
            await db_session.execute(
                """
                UPDATE organizations SET quota_utilized = quota_utilized - $1 WHERE organization_id = $2
                """,
                current_quota - new_quota,
                org_id
            )
            await db_session.execute(
                """
                UPDATE servers SET quota_utilized = quota_utilized - $1 WHERE server_id = $2
                """,
                current_quota - new_quota,
                server_id
            )

        else:
            # This casse is not expected as we have already checked that the new quota is not same as the current quota
            pass

    except Exception as e:
        raise All_Exceptions(
            message=f"Error updating quota for mailbox {email}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def delete_mailbox_and_update_quota(db_session: PgSession, email: str, org_id: str) -> str:
    """
    Delete a mailbox and update the organization quota
    """
    # Check if the mailbox exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email,
        raise_exception_if_exists=False,
        exception_message=f"Mailbox with email {email} does not exist"
    )

    try:
        # Get the current quota for the mailbox
        row = await db_session.fetchrow(
            "SELECT quota_allocated, server_id FROM mailboxes WHERE email = $1", email
        )
        if not row:
            raise All_Exceptions(
                message=f"Mailbox with email {email} does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        current_quota = float(row["quota_allocated"])
        server_id = str(row["server_id"])
        logging.info(f"Deleting mailbox {email} with current quota {current_quota} and server_id {server_id}")

        # TODO: Do it in a transaction to ensure that either both the mailbox is deleted and the quota is updated or neither happens

        # Delete the mailbox
        await db_session.execute(
            "DELETE FROM mailboxes WHERE email = $1", email
        )

        # Update the organization quota
        await db_session.execute(
            """
            UPDATE organizations SET quota_utilized = quota_utilized - $1 WHERE organization_id = $2
            """,
            current_quota,
            org_id
        )

        # Update Server quota
        await db_session.execute(
            """
            UPDATE servers SET quota_utilized = quota_utilized - $1 WHERE server_id = $2
            """,
            current_quota,
            server_id
        )

        return server_id

    except Exception as e:
        raise All_Exceptions(
            message=f"Error deleting mailbox {email}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def get_mailboxes_space(domain_names: list[str], db: PgSession) -> dict:
    """
    Get the space metrics for mailboxes under the given domain names
    """
    if not domain_names:
        return {}

    try:
        # Fetch the space metrics for mailboxes under the given domain names
        rows = await db.fetch(
            """
            SELECT domain_name, COUNT(*) AS total_mailboxes, SUM(quota_allocated) AS total_quota_allocated,
                   SUM(quota_utilized_bytes) AS total_quota_utilized_bytes, SUM(CASE WHEN is_enabled THEN 1 ELSE 0 END) AS total_active_mailboxes,
                   SUM(total_messages_count) AS total_emails_count
            FROM mailboxes
            WHERE domain_name = ANY($1)
            GROUP BY domain_name
            """,
            domain_names
        )

        return {
            row["domain_name"]: {
                "total_mailboxes": row["total_mailboxes"],
                "total_active_mailboxes": row["total_active_mailboxes"],
                "total_inactive_mailboxes": row["total_mailboxes"] - row["total_active_mailboxes"],
                "total_quota_allocated": float(row["total_quota_allocated"]),
                "total_quota_utilized_bytes": int(row["total_quota_utilized_bytes"]),
                "total_emails_count": int(row["total_emails_count"])
            }
            for row in rows
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Error fetching mailboxes space metrics: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def bulk_export_mailboxes(db_session: PgSession, domain_name: str, page: int, size: int) -> dict:
    """
    Bulk export mailboxes under a specific domain
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    try:
        # Fetch all mailboxes under the domain with pagination
        total_rows = await db_session.fetchval(
            "SELECT COUNT(*) FROM mailboxes WHERE domain_name = $1",
            domain_name
        )

        if total_rows == 0:
            return {
                "total_rows": 0,
                "mailboxes": []
            }

        rows = await db_session.fetch(
            """
            SELECT email, is_enabled, quota_allocated, quota_utilized_bytes,
                   total_messages_count, general_policy_id,
                   forwarding_policy_id, distribution_policy_id
            FROM mailboxes
            WHERE domain_name = $1
            ORDER BY email ASC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            size,
            (page - 1) * size
        )

        mailboxes = [
            {
                "email": row["email"],
                "is_enabled": row["is_enabled"],
                "quota_allocated": float(row["quota_allocated"]),
                "quota_utilized_bytes": int(row["quota_utilized_bytes"]),
                "total_messages_count": int(row["total_messages_count"]),
                "general_policy_id": str(row["general_policy_id"]) if row["general_policy_id"] else None,
                "forwarding_policy_id": str(row["forwarding_policy_id"]) if row["forwarding_policy_id"] else None,
                "distribution_policy_id": str(row["distribution_policy_id"]) if row["distribution_policy_id"] else None,
            }
            for row in rows
        ]

        return {
            "mailboxes": mailboxes,
            "total_rows": total_rows,
            "total_pages": (total_rows + size - 1) // size,
            "current_page": page,
            "page_size": size
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Error fetching mailboxes under domain {domain_name}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def get_mailboxes_under_server(db_session: PgSession, server_id: str, page: int, size: int, email_starts_with: str = '') -> dict:
    """
    Get all mailboxes under a specific server with pagination and optional email prefix search.
    """
    try:
        # Prepare base query parts
        where_clause = "WHERE server_id = $1"
        params = [server_id]
        param_idx = 2  # Next parameter index for SQL

        if email_starts_with:
            where_clause += f" AND email ILIKE ${param_idx}"
            params.append(f"{email_starts_with}%")
            param_idx += 1

        # Get total count
        total_rows = await db_session.fetchval(
            f"SELECT COUNT(*) FROM mailboxes {where_clause}",
            *params
        )

        if total_rows == 0:
            return {
                "total_rows": 0,
                "mailboxes": [],
                "total_pages": 0,
                "current_page": page,
                "page_size": size
            }

        # Add LIMIT and OFFSET
        limit_offset_query = f"""
            SELECT email, is_enabled, quota_allocated, quota_utilized_bytes, is_locked, total_messages_count
            FROM mailboxes
            {where_clause}
            ORDER BY email DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([size, (page - 1) * size])

        rows = await db_session.fetch(limit_offset_query, *params)

        mailboxes = [
            {
                "email": row["email"],
                "is_enabled": row["is_enabled"],
                "quota_allocated": float(row["quota_allocated"]),
                "quota_utilized_bytes": int(row["quota_utilized_bytes"]),
                "total_messages_count": int(row["total_messages_count"]),
                "is_locked": row["is_locked"]
            }
            for row in rows
        ]

        return {
            "mailboxes": mailboxes,
            "total_rows": total_rows,
            "total_pages": (total_rows + size - 1) // size,
            "current_page": page,
            "page_size": size
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Error fetching mailboxes under server {server_id}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def update_mailbox_lock_status(db_session: PgSession, email: str, is_locked: bool, domain_name: str) -> None:
    """
    Update the lock status of a mailbox if domain is not locked
    """
    # Check if the mailbox exists
    await _raise_check_mailbox_exists(
        db_session=db_session,
        email=email,
        raise_exception_if_exists=False,
        exception_message=f"Mailbox with email {email} does not exist"
    )

    # Check if the domain is locked
    row = await db_session.fetchrow(
        "SELECT is_locked FROM domains WHERE domain_name = $1", domain_name
    )
    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    if row["is_locked"]:
        raise All_Exceptions(
            message=f"Cannot update lock status for mailbox {email} as the domain {domain_name} is locked",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # Also check if the mailbox is in process of migration
    migration_status = await db_session.fetchval(
        """
        SELECT COUNT(*) FROM mailbox_migrations
        WHERE email = $1 AND (migration_status = 'INITIALIZING' OR migration_status = 'IN_PROGRESS')
        """,
        email
    )
    if migration_status > 0:
        raise All_Exceptions(
            message=f"Cannot update lock status for mailbox {email} as it is currently being migrated",
            status_code=status.HTTP_423_LOCKED
        )

    try:
        # Update the lock status of the mailbox
        await db_session.execute(
            """
            UPDATE mailboxes
            SET is_locked = $1
            WHERE email = $2
            """,
            is_locked,
            email
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Error updating lock status for mailbox {email}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def check_migration_in_progress_for_mailbox(db_session: PgSession, email: str) -> dict:
    """
    Check if a mailbox is currently being migrated
    """
    row = await db_session.fetchrow(
        """
        SELECT COUNT(*) AS migration_count
        FROM mailbox_migrations
        WHERE email = $1 AND (migration_status = 'INITIALIZING' OR migration_status = 'IN_PROGRESS')
        """,
        email
    )
    if not row:
        raise All_Exceptions(
            message=f"Mailbox with email {email} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return {
        "migration_in_progress": row["migration_count"] > 0,
        "migration_count": row["migration_count"],
        "email": email
    }


async def get_mailbox_lock_status(db_session: PgSession, email: str) -> dict:
    """
    Get the lock status of a mailbox
    """
    row = await db_session.fetchrow(
        "SELECT is_locked FROM mailboxes WHERE email = $1", email
    )
    if not row:
        raise All_Exceptions(
            message=f"Mailbox with email {email} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return {
        "email": email,
        "is_locked": row["is_locked"]
    }


async def get_email_server_mappings(db_session: PgSession, emails: list[str]) -> dict:
    """
    Get the server ID mappings for the given email addresses
    """
    try:
        rows = await db_session.fetch(
            """
            SELECT email, server_id FROM mailboxes WHERE email = ANY($1)
            """,
            emails
        )

        return {
            row["email"]: str(row["server_id"])
            for row in rows
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Error fetching email server mappings: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )


async def list_only_mailboxes(db_session: PgSession, domain_name: str, query: str, page: int, size: int) -> list[str]:
    """
    List only the email addresses of mailboxes under a specific domain with optional search query.
    """
    try:
        rows = await db_session.fetch(
            """
            SELECT email FROM mailboxes
            WHERE domain_name = $1 AND email ILIKE $2
            ORDER BY email ASC
            LIMIT $3 OFFSET $4
            """,
            domain_name,
            f"%{query}%",
            size,
            (page - 1) * size
        )

        return [row["email"] for row in rows]

    except Exception as e:
        raise All_Exceptions(
            message=f"Error listing mailboxes under domain {domain_name}: {e}",
            status_code=status.HTTP_417_EXPECTATION_FAILED
        )
