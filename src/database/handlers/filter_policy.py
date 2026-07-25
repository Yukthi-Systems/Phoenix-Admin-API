"""
Handles all the Black White Listing (domain level) related database operations
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


async def create_filter_policy_entry(
    db_session: PgSession,
    policy_name: str,
    domain_name: str,
    is_active: bool,
    white_entries: list[str],
    black_entries: list[str]
) -> None:
    """
    Create a new Filter Policy list entry in the database
    """
    try:
        # Insert the new Filter Policy list entry into the database
        await db_session.execute(
            """
            INSERT INTO filter_policies (policy_id, domain_name, policy_name, white_entries, black_entries, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(uuid.uuid4()),
            domain_name,
            policy_name,
            white_entries,
            black_entries,
            is_active
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create Filter Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def edit_filter_policy_entry(
    db_session: PgSession,
    policy_id: str,
    policy_name: str,
    is_active: bool,
    white_entries: list[str],
    black_entries: list[str]
) -> None:
    """
    Edit an existing Filter Policy list entry in the database
    """
    try:
        # Update the existing Filter Policy list entry in the database
        await db_session.execute(
            """
            UPDATE filter_policies
            SET policy_name = $1, white_entries = $2, black_entries = $3, is_active = $4, updated_at = CURRENT_TIMESTAMP
            WHERE policy_id = $5
            """,
            policy_name,
            white_entries,
            black_entries,
            is_active,
            policy_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to edit Filter Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_filter_policy_entries(
    db_session: PgSession,
    domain_name: str,
    search_query: str = "",
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    Get all Filter Policy list entries for a specific domain
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM filter_policies
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
            SELECT policy_id, policy_name, created_at, updated_at, is_active
            FROM filter_policies
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
            message=f"Failed to retrieve Filter Policy list entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_filter_policy_entries(db_session: PgSession, domain_name: str, page: int, page_size: int) -> list[dict]:
    """
    Export Filter Policy list entries for a specific domain with pagination
    """
    try:
        offset = (page - 1) * page_size
        entries = await db_session.fetch(
            """
            SELECT policy_id, policy_name, created_at, updated_at, is_active, white_entries, black_entries
            FROM filter_policies
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
                "white_entries": list(entry["white_entries"]),
                "black_entries": list(entry["black_entries"]),
                "is_active": entry["is_active"],
                "updated_at": entry["updated_at"].isoformat(),
                "created_at": entry["created_at"].isoformat()
            }
            for entry in entries
        ]

        return entry_list

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export Filter Policy list entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_filter_policy_entry(
    db_session: PgSession,
    policy_id: str
) -> None:
    """
    Delete a Filter Policy list entry by its ID
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM filter_policies
            WHERE policy_id = $1
            """,
            policy_id
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Filter Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete Filter Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_filter_policy_entry_by_id(
    db_session: PgSession,
    policy_id: str
) -> dict:
    """
    Get a Filter Policy list entry by its ID
    """
    try:
        entry = await db_session.fetchrow(
            """
            SELECT policy_name, domain_name, created_at, updated_at, is_active, white_entries, black_entries
            FROM filter_policies
            WHERE policy_id = $1
            """,
            policy_id
        )

        if not entry:
            raise All_Exceptions(
                message="Filter Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "policy_name": entry["policy_name"],
            "domain_name": entry["domain_name"],
            "white_entries": list(entry["white_entries"]),
            "black_entries": list(entry["black_entries"]),
            "is_active": entry["is_active"],
            "created_at": entry["created_at"].isoformat(),
            "updated_at": entry["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve Filter Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
