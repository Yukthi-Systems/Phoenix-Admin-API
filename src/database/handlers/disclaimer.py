"""
Handles all the Disclaimer related database operations
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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, logging, status, uuid, orjson
from src.utils.models import All_Exceptions


PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


async def create_new_disclaimer_entry(
    db_session: PgSession,
    organization_id: str,
    disclaimer_name: str,
    info: dict,
    html_content: str,
    text_content: str
) -> None:
    """
    Create a new disclaimer entry in the database
    """
    try:
        # Insert the new disclaimer into the database
        await db_session.execute(
            """
            INSERT INTO disclaimers (disclaimer_id, organization_id, disclaimer_name,
            info, html_content, text_content)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(uuid.uuid4()),
            organization_id,
            disclaimer_name,
            orjson.dumps(info).decode("utf-8"),
            html_content,
            text_content
        )

    except Exception as e:
        logging.error(f"Error creating new disclaimer entry: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new disclaimer entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_all_paginated_disclaimers_by_organization(
    db_session: PgSession,
    organization_id: str,
    search_query: str = "",
    page: int = 1,
    limit: int = 10
) -> dict:
    """
    Get all disclaimers for a specific organization with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM disclaimers WHERE organization_id = $1 AND disclaimer_name ILIKE $2
            """,
            organization_id,
            f"%{search_query}%"
        )

        offset = (page - 1) * limit
        disclaimers = await db_session.fetch(
            """
            SELECT disclaimer_id, disclaimer_name, created_at, updated_at
            FROM disclaimers
            WHERE organization_id = $1 AND disclaimer_name ILIKE $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            """,
            organization_id,
            f"%{search_query}%",
            limit,
            offset
        )

        # Convert the result to a list of dictionaries
        disclaimer_list = [
            {
                "disclaimer_id": str(disclaimer["disclaimer_id"]),
                "disclaimer_name": disclaimer["disclaimer_name"],
                "created_at": disclaimer["created_at"].isoformat(),
                "updated_at": disclaimer["updated_at"].isoformat()
            }
            for disclaimer in disclaimers
        ]

        return {
            "disclaimers": disclaimer_list,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }

    except Exception as e:
        logging.error(f"Error retrieving disclaimers for organization {organization_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to retrieve disclaimers for organization {organization_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_disclaimers_by_org(db_session: PgSession, organization_id: str, page: int, limit: int) -> list[dict]:
    """
    Export disclaimers for a specific organization with pagination
    """
    try:
        offset = (page - 1) * limit
        disclaimers = await db_session.fetch(
            """
            SELECT disclaimer_id, disclaimer_name, info, html_content, text_content, created_at, updated_at
            FROM disclaimers
            WHERE organization_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            limit,
            offset
        )

        # Convert the result to a list of dictionaries
        disclaimer_list = [
            {
                "disclaimer_id": str(disclaimer["disclaimer_id"]),
                "disclaimer_name": disclaimer["disclaimer_name"],
                "info": orjson.loads(disclaimer["info"]),
                "html_content": disclaimer["html_content"],
                "text_content": disclaimer["text_content"],
                "created_at": disclaimer["created_at"].isoformat(),
                "updated_at": disclaimer["updated_at"].isoformat()
            }
            for disclaimer in disclaimers
        ]

        return disclaimer_list

    except Exception as e:
        logging.error(f"Error exporting disclaimers for organization {organization_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to export disclaimers for organization {organization_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_disclaimer_details_by_id(
    db_session: PgSession,
    organization_id: str,
    disclaimer_id: str
) -> dict:
    """
    Get details of a specific disclaimer by its ID
    """
    try:
        disclaimer = await db_session.fetchrow(
            """
            SELECT disclaimer_id, organization_id, disclaimer_name, info, html_content, text_content, created_at, updated_at
            FROM disclaimers
            WHERE disclaimer_id = $1 AND organization_id = $2
            """,
            disclaimer_id,
            organization_id
        )

        if not disclaimer:
            raise All_Exceptions(
                message="Disclaimer not found or not accessible by this organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "disclaimer_id": str(disclaimer["disclaimer_id"]),
            "organization_id": str(disclaimer["organization_id"]),
            "disclaimer_name": disclaimer["disclaimer_name"],
            "info": orjson.loads(disclaimer["info"]),
            "html_content": disclaimer["html_content"],
            "text_content": disclaimer["text_content"],
            "created_at": disclaimer["created_at"].isoformat(),
            "updated_at": disclaimer["updated_at"].isoformat()
        }

    except Exception as e:
        logging.error(f"Error retrieving disclaimer details for ID {disclaimer_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to retrieve disclaimer details for ID {disclaimer_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_disclaimer_by_id(
    db_session: PgSession,
    organization_id: str,
    disclaimer_id: str
) -> None:
    """
    Delete a disclaimer by its ID
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM disclaimers WHERE disclaimer_id = $1
            """,
            disclaimer_id
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Disclaimer not found or already deleted",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error deleting disclaimer with ID {disclaimer_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to delete disclaimer with ID {disclaimer_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_disclaimer_details(
    db_session: PgSession,
    disclaimer_id: str,
    organization_id: str,
    disclaimer_name: str,
    info: dict,
    html_content: str,
    text_content: str
) -> None:
    """
    Update the details of a specific disclaimer
    """
    try:
        result = await db_session.execute(
            """
            UPDATE disclaimers
            SET disclaimer_name = $1, info = $2, html_content = $3, text_content = $4, updated_at = CURRENT_TIMESTAMP
            WHERE disclaimer_id = $5 AND organization_id = $6
            """,
            disclaimer_name,
            orjson.dumps(info).decode("utf-8"),
            html_content,
            text_content,
            disclaimer_id,
            organization_id
        )

        if result == "UPDATE 0":
            raise All_Exceptions(
                message="Disclaimer not found or no changes made",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error updating disclaimer with ID {disclaimer_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update disclaimer with ID {disclaimer_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
