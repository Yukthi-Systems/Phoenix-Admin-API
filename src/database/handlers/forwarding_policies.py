"""
Handles all the Mail Forwarding Policy (domain level) related database operations
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



async def create_forwarding_policy_entry(
    db_session: PgSession,
    policy_name: str,
    policy_description: str,
    domain_name: str,
    is_active: bool,
    subject_contains: list[str],
    from_emails: list[str],
    forward_to_emails: list[str]
) -> None:
    """
    Create a new Forwarding Policy entry in the database
    """
    try:
        # Insert the new Forwarding Policy entry into the database
        await db_session.execute(
            """
            INSERT INTO forwarding_policies (
                policy_id, policy_name, policy_description, domain_name,
                subject_contains, from_emails, forward_to_emails, is_active
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            uuid.uuid4(),
            policy_name,
            policy_description,
            domain_name,
            subject_contains,
            from_emails,
            forward_to_emails,
            is_active
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create Forwarding Policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def edit_forwarding_policy_entry(
    db_session: PgSession,
    policy_id: str,
    policy_name: str,
    policy_description: str,
    domain_name: str,
    subject_contains: list[str],
    from_emails: list[str],
    forward_to_emails: list[str],
    is_active: bool
) -> None:
    """
    Edit an existing Forwarding Policy entry in the database
    """
    try:
        # Update the existing Forwarding Policy entry in the database
        await db_session.execute(
            """
            UPDATE forwarding_policies
            SET policy_name = $1, policy_description = $2,
                subject_contains = $3, from_emails = $4,
                forward_to_emails = $5, is_active = $6, updated_at = CURRENT_TIMESTAMP
            WHERE policy_id = $7 AND domain_name = $8
            """,
            policy_name,
            policy_description,
            subject_contains,
            from_emails,
            forward_to_emails,
            is_active,
            policy_id,
            domain_name
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to edit Forwarding Policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_forwarding_policy_entries(
    db_session: PgSession,
    domain_name: str,
    search_query: str = "",
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    Get all Forwarding Policy list entries for a specific domain
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM forwarding_policies
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
            FROM forwarding_policies
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
            message=f"Failed to retrieve Forwarding Policy list entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_forwarding_policy_entries(db_session: PgSession, domain_name: str, page: int, page_size: int) -> list[dict]:
    """
    Export Forwarding Policy entries for a specific domain with pagination support
    """
    try:
        offset = (page - 1) * page_size
        entries = await db_session.fetch(
            """
            SELECT policy_id, policy_name, policy_description, domain_name, 
                   is_active, created_at, updated_at, subject_contains, from_emails, forward_to_emails
            FROM forwarding_policies
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
                "subject_contains": list(entry["subject_contains"]),
                "from_emails": list(entry["from_emails"]),
                "forward_to_emails": list(entry["forward_to_emails"]),
                "is_active": entry["is_active"],
                "created_at": entry["created_at"].isoformat(),
                "updated_at": entry["updated_at"].isoformat()
            }
            for entry in entries
        ]

        return entry_list

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export Forwarding Policy entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_forwarding_policy_entry(
    db_session: PgSession,
    policy_id: str,
    domain_name: str
) -> None:
    """
    Delete an Forwarding Policy list entry by its ID
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM forwarding_policies
            WHERE policy_id = $1 AND domain_name = $2
            """,
            policy_id,
            domain_name
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Forwarding Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete Forwarding Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_forwarding_policy_entry_by_id(
    db_session: PgSession,
    policy_id: str
) -> dict:
    """
    Get an Forwarding Policy list entry by its ID
    """
    try:
        entry = await db_session.fetchrow(
            """
            SELECT policy_name, policy_description, domain_name, 
                   subject_contains, from_emails, forward_to_emails,
                   is_active, created_at, updated_at
            FROM forwarding_policies
            WHERE policy_id = $1
            """,
            policy_id
        )

        if not entry:
            raise All_Exceptions(
                message="Forwarding Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "policy_name": entry["policy_name"],
            "policy_description": entry["policy_description"],
            "domain_name": entry["domain_name"],
            "subject_contains": list(entry["subject_contains"]),
            "from_emails": list(entry["from_emails"]),
            "forward_to_emails": list(entry["forward_to_emails"]),
            "is_active": entry["is_active"],
            "created_at": entry["created_at"].isoformat(),
            "updated_at": entry["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve Forwarding Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
