"""
Handles all the general Policy (domain level) related database operations
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


from src.utils.base.libraries import asyncpg, TypeAlias, status, uuid
from src.utils.models import All_Exceptions

PgSession: TypeAlias = asyncpg.Connection


async def create_general_policy_entry(
    db_session: PgSession,
    policy_name: str,
    policy_description: str,
    domain_name: str,
    block_all_incoming_emails: bool,
    block_all_outgoing_emails: bool,
    block_all_incoming_domains: bool,
    block_all_outgoing_domains: bool,
    incoming_exception_domains: list[str],
    incoming_exception_emails: list[str],
    outgoing_exception_domains: list[str],
    outgoing_exception_emails: list[str],
    outgoing_size_limit_mb: float,
    is_active: bool
) -> None:
    """
    Create a new General Policy entry in the database
    """
    try:
        # Insert the new General Policy entry into the database
        await db_session.execute(
            """
            INSERT INTO general_policies (
                policy_id, policy_name, policy_description, domain_name, 
                block_all_incoming_emails, block_all_outgoing_emails,
                incoming_exception_domains, incoming_exception_emails,
                outgoing_exception_domains, outgoing_exception_emails,
                block_all_incoming_domains, block_all_outgoing_domains,
                outgoing_size_limit_mb, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            str(uuid.uuid4()),
            policy_name,
            policy_description,
            domain_name,
            block_all_incoming_emails,
            block_all_outgoing_emails,
            incoming_exception_domains,
            incoming_exception_emails,
            outgoing_exception_domains,
            outgoing_exception_emails,
            block_all_incoming_domains,
            block_all_outgoing_domains,
            outgoing_size_limit_mb,
            is_active
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create General Policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def edit_general_policy_entry(
    db_session: PgSession,
    policy_id: str,
    policy_name: str,
    policy_description: str,
    domain_name: str,
    block_all_incoming_emails: bool,
    block_all_outgoing_emails: bool,
    block_all_incoming_domains: bool,
    block_all_outgoing_domains: bool,
    incoming_exception_domains: list[str],
    incoming_exception_emails: list[str],
    outgoing_exception_domains: list[str],
    outgoing_exception_emails: list[str],
    outgoing_size_limit_mb: float,
    is_active: bool
) -> None:
    """
    Edit an existing General Policy entry in the database
    """
    try:
        # Update the existing General Policy entry in the database
        await db_session.execute(
            """
            UPDATE general_policies
            SET policy_name = $1, policy_description = $2, domain_name = $3,
                block_all_incoming_emails = $4, block_all_outgoing_emails = $5,
                incoming_exception_domains = $6, incoming_exception_emails = $7,
                outgoing_exception_domains = $8, outgoing_exception_emails = $9,
                block_all_incoming_domains = $10, block_all_outgoing_domains = $11,
                outgoing_size_limit_mb = $12, is_active = $13, updated_at = CURRENT_TIMESTAMP
            WHERE policy_id = $14
            """,
            policy_name,
            policy_description,
            domain_name,
            block_all_incoming_emails,
            block_all_outgoing_emails,
            incoming_exception_domains,
            incoming_exception_emails,
            outgoing_exception_domains,
            outgoing_exception_emails,
            block_all_incoming_domains,
            block_all_outgoing_domains,
            outgoing_size_limit_mb,
            is_active,
            policy_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to edit General Policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_general_policy_entries(
    db_session: PgSession,
    domain_name: str,
    search_query: str = "",
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    Get all General Policy list entries for a specific domain
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM general_policies
            WHERE domain_name = $1 AND policy_name ILIKE $2
            """,
            domain_name,
            f"%{search_query}%"
        )
        if not total_count or total_count == 0:
            return {
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "entries": [],
                "total_pages": 0
            }

        offset = (page - 1) * page_size
        entries = await db_session.fetch(
            """
            SELECT policy_id, policy_name, is_active, created_at, updated_at
            FROM general_policies
            WHERE domain_name = $1 AND policy_name ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            domain_name,
            f"%{search_query}%",
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        entry_list = [
            {
                "policy_id": str(entry["policy_id"]),
                "policy_name": entry["policy_name"],
                "is_active": entry["is_active"],
                "updated_at": entry["updated_at"].isoformat(),
                "created_at": entry["created_at"].isoformat()
            }
            for entry in entries
        ]

        return {
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "entries": entry_list,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve General Policy list entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_general_policy_entries(db_session: PgSession, domain_name: str, page: int, page_size: int) -> list[dict]:
    """
    Export General Policy entries for a specific domain with pagination support
    """
    try:
        offset = (page - 1) * page_size
        entries = await db_session.fetch(
            """
            SELECT policy_id, policy_name, policy_description, domain_name, 
                   block_all_incoming_emails, block_all_outgoing_emails,
                   block_all_incoming_domains, block_all_outgoing_domains,
                   incoming_exception_domains, incoming_exception_emails,
                   outgoing_exception_domains, outgoing_exception_emails,
                   outgoing_size_limit_mb, is_active, created_at, updated_at
            FROM general_policies
            WHERE domain_name = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        entry_list = [
            {
                "policy_id": str(entry["policy_id"]),
                "policy_name": entry["policy_name"],
                "policy_description": entry["policy_description"],
                "domain_name": entry["domain_name"],
                "block_all_incoming_emails": entry["block_all_incoming_emails"],
                "block_all_outgoing_emails": entry["block_all_outgoing_emails"],
                "block_all_incoming_domains": entry["block_all_incoming_domains"],
                "block_all_outgoing_domains": entry["block_all_outgoing_domains"],
                "incoming_exception_domains": list(entry["incoming_exception_domains"]),
                "incoming_exception_emails": list(entry["incoming_exception_emails"]),
                "outgoing_exception_domains": list(entry["outgoing_exception_domains"]),
                "outgoing_exception_emails": list(entry["outgoing_exception_emails"]),
                "outgoing_size_limit_mb": float(entry["outgoing_size_limit_mb"]),
                "is_active": entry["is_active"],
                "created_at": entry["created_at"].isoformat(),
                "updated_at": entry["updated_at"].isoformat()
            }
            for entry in entries
        ]

        return entry_list

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export General Policy entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_general_policy_entry(
    db_session: PgSession,
    policy_id: str,
    domain_name: str
) -> None:
    """
    Delete an General Policy list entry by its ID
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM general_policies
            WHERE policy_id = $1 AND domain_name = $2
            """,
            policy_id,
            domain_name
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="General Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete General Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_general_policy_entry_by_id(
    db_session: PgSession,
    policy_id: str
) -> dict:
    """
    Get an General Policy list entry by its ID
    """
    try:
        entry = await db_session.fetchrow(
            """
            SELECT policy_name, policy_description, domain_name, 
                   block_all_incoming_emails, block_all_outgoing_emails,
                   block_all_incoming_domains, block_all_outgoing_domains,
                   incoming_exception_domains, incoming_exception_emails,
                   outgoing_exception_domains, outgoing_exception_emails,
                   outgoing_size_limit_mb, is_active, created_at, updated_at
            FROM general_policies
            WHERE policy_id = $1
            """,
            policy_id
        )

        if not entry:
            raise All_Exceptions(
                message="General Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "policy_name": entry["policy_name"],
            "policy_description": entry["policy_description"],
            "domain_name": entry["domain_name"],
            "block_all_incoming_emails": entry["block_all_incoming_emails"],
            "block_all_outgoing_emails": entry["block_all_outgoing_emails"],
            "block_all_incoming_domains": entry["block_all_incoming_domains"],
            "block_all_outgoing_domains": entry["block_all_outgoing_domains"],
            "incoming_exception_domains": list(entry["incoming_exception_domains"]),
            "incoming_exception_emails": list(entry["incoming_exception_emails"]),
            "outgoing_exception_domains": list(entry["outgoing_exception_domains"]),
            "outgoing_exception_emails": list(entry["outgoing_exception_emails"]),
            "outgoing_size_limit_mb": float(entry["outgoing_size_limit_mb"]),
            "is_active": entry["is_active"],
            "created_at": entry["created_at"].isoformat(),
            "updated_at": entry["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve General Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
