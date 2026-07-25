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



async def create_restriction_policy_entry(
    db_session: PgSession,
    policy_name: str,
    policy_description: str,
    organization_id: str,
    ip_restrictions: list[str],
    geo_restrictions: list[str],
    is_active: bool
) -> None:
    """
    Create a new Restriction Policy entry in the database
    """
    try:
        # Insert the new Restriction Policy entry into the database
        await db_session.execute(
            """
            INSERT INTO restriction_policies (
                policy_id, policy_name, policy_description, organization_id,
                ip_restriction, geo_restriction, is_active
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            uuid.uuid4(),
            policy_name,
            policy_description,
            organization_id,
            ip_restrictions,
            geo_restrictions,
            is_active
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create Restriction Policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def edit_restriction_policy_entry(
    db_session: PgSession,
    policy_id: str,
    policy_name: str,
    policy_description: str,
    organization_id: str,
    ip_restrictions: list[str],
    geo_restrictions: list[str],
    is_active: bool
) -> None:
    """
    Edit an existing Restriction Policy entry in the database
    """
    try:
        # Update the existing Restriction Policy entry in the database
        await db_session.execute(
            """
            UPDATE restriction_policies
            SET policy_name = $1, policy_description = $2,
                ip_restriction = $3, geo_restriction = $4,
                is_active = $5, updated_at = CURRENT_TIMESTAMP
            WHERE policy_id = $6 AND organization_id = $7
            """,
            policy_name,
            policy_description,
            ip_restrictions,
            geo_restrictions,
            is_active,
            policy_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to edit Restriction Policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_restriction_policy_entries(
    db_session: PgSession,
    organization_id: str,
    search_query: str = "",
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    Get all Restriction Policy list entries for a specific organization with pagination and search support
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM restriction_policies
            WHERE organization_id = $1 AND policy_name ILIKE $2
            """,
            organization_id,
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
            FROM restriction_policies
            WHERE organization_id = $1 AND policy_name ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            organization_id,
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
            message=f"Failed to retrieve Restriction Policy list entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_restriction_policy_entries(db_session: PgSession, organization_id: str, page: int, page_size: int) -> list[dict]:
    """
    Export Restriction Policy entries for a specific organization with pagination support
    """
    try:
        offset = (page - 1) * page_size
        entries = await db_session.fetch(
            """
            SELECT policy_id, policy_name, policy_description,
                   is_active, created_at, updated_at, ip_restriction, geo_restriction
            FROM restriction_policies
            WHERE organization_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        entry_list = [
            {
                "policy_id": str(entry["policy_id"]),
                "policy_name": entry["policy_name"],
                "policy_description": entry["policy_description"],
                "ip_restriction": list(entry["ip_restriction"]),
                "geo_restriction": list(entry["geo_restriction"]),
                "is_active": entry["is_active"],
                "created_at": entry["created_at"].isoformat(),
                "updated_at": entry["updated_at"].isoformat()
            }
            for entry in entries
        ]

        return entry_list

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export Restriction Policy entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_restriction_policy_entry(
    db_session: PgSession,
    policy_id: str,
    organization_id: str
) -> None:
    """
    Delete an Restriction Policy list entry by its ID
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM restriction_policies
            WHERE policy_id = $1 AND organization_id = $2
            """,
            policy_id,
            organization_id
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Restriction Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete Restriction Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_restriction_policy_entry_by_id(
    db_session: PgSession,
    organization_id: str,
    policy_id: str
) -> dict:
    """
    Get an Restriction Policy list entry by its ID
    """
    try:
        entry = await db_session.fetchrow(
            """
            SELECT policy_name, policy_description, 
                   ip_restriction, geo_restriction,
                   is_active, created_at, updated_at
            FROM restriction_policies
            WHERE policy_id = $1 AND organization_id = $2
            """,
            policy_id,
            organization_id
        )

        if not entry:
            raise All_Exceptions(
                message="Restriction Policy list entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "policy_name": entry["policy_name"],
            "policy_description": entry["policy_description"],
            "ip_restriction": list(entry["ip_restriction"]),
            "geo_restriction": list(entry["geo_restriction"]),
            "is_active": entry["is_active"],
            "created_at": entry["created_at"].isoformat(),
            "updated_at": entry["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve Restriction Policy list entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
