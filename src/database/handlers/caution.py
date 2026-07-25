"""
Handles all the Caution Message related database operations
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


# -- Caution for domains
# CREATE TABLE cautions (
#     caution_id UUID PRIMARY KEY,
#     organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

#     caution_name VARCHAR(250) NOT NULL,
#     info JSONB NOT NULL,  -- metadata, not indexed

#     html_content TEXT NOT NULL,  -- HTML content of the caution
#     text_content TEXT NOT NULL,  -- Text content of the caution

#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     UNIQUE (organization_id, caution_name)
# );


async def create_new_caution_entry(
    db_session: PgSession,
    organization_id: str,
    caution_name: str,
    info: dict,
    html_content: str,
    text_content: str
) -> None:
    """
    Create a new caution entry in the database
    """
    try:
        # Insert the new caution into the database
        await db_session.execute(
            """
            INSERT INTO cautions (caution_id, organization_id, caution_name, info, html_content, text_content)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(uuid.uuid4()),
            organization_id,
            caution_name,
            orjson.dumps(info).decode("utf-8"),
            html_content,
            text_content
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new caution entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_caution_details(
    db_session: PgSession,
    organization_id: str,
    caution_id: str
) -> dict:
    """
    Get details of a specific caution
    """
    try:
        # Fetch the caution details from the database
        result = await db_session.fetchrow(
            """
            SELECT caution_id, organization_id, caution_name, info, html_content, text_content, created_at, updated_at
            FROM cautions
            WHERE organization_id = $1 AND caution_id = $2
            """,
            organization_id,
            caution_id
        )
        if result is None:
            raise All_Exceptions(
                message="Caution ID not found or does not belong to the organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Convert the result to a dictionary
        return {
            "caution_id": str(result["caution_id"]),
            "organization_id": str(result["organization_id"]),
            "caution_name": result["caution_name"],
            "info": orjson.loads(result["info"]),
            "html_content": result["html_content"],
            "text_content": result["text_content"],
            "created_at": result["created_at"].isoformat(),
            "updated_at": result["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch caution details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_cautions_under_organization(
    db_session: PgSession,
    organization_id: str,
    search_query: str = "",
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    List all cautions under an organization with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM cautions WHERE organization_id = $1 AND caution_name ILIKE $2
            """,
            organization_id,
            f"%{search_query}%"
        )

        if not total_count or total_count == 0:
            return {
                "cautions": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        offset = (page - 1) * page_size
        cautions = await db_session.fetch(
            """
            SELECT caution_id, caution_name, created_at, updated_at
            FROM cautions
            WHERE organization_id = $1 AND caution_name ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            organization_id,
            f"%{search_query}%",
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        caution_list = [
            {
                "caution_id": str(caution["caution_id"]),
                "caution_name": caution["caution_name"],
                "created_at": caution["created_at"].isoformat(),
                "updated_at": caution["updated_at"].isoformat()
            }
            for caution in cautions
        ]

        return {
            "cautions": caution_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list cautions for organization {organization_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_cautions_under_organization(db_session: PgSession, organization_id: str, page: int, page_size: int) -> list[dict]:
    """
    Export all cautions under an organization with pagination
    """
    try:
        offset = (page - 1) * page_size
        cautions = await db_session.fetch(
            """
            SELECT caution_id, caution_name, info, html_content, text_content, created_at, updated_at
            FROM cautions
            WHERE organization_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        return [
            {
                "caution_id": str(caution["caution_id"]),
                "caution_name": caution["caution_name"],
                "info": orjson.loads(caution["info"]),
                "html_content": caution["html_content"],
                "text_content": caution["text_content"],
                "created_at": caution["created_at"].isoformat(),
                "updated_at": caution["updated_at"].isoformat()
            }
            for caution in cautions
        ]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export cautions for organization {organization_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_caution(
    db_session: PgSession,
    organization_id: str,
    caution_id: str
) -> None:
    """
    Delete a caution from the database
    """
    try:
        # Delete the caution from the database
        result = await db_session.execute(
            """
            DELETE FROM cautions
            WHERE organization_id = $1 AND caution_id = $2
            """,
            organization_id,
            caution_id
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Caution ID not found or does not belong to the organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete caution: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
    

async def update_caution_details(
    db_session: PgSession,
    organization_id: str,
    caution_id: str,
    caution_name: str,
    info: dict,
    html_content: str,
    text_content: str
) -> None:
    """
    Update the details of a specific caution
    """
    try:
        # Update the caution details in the database
        result = await db_session.execute(
            """
            UPDATE cautions
            SET caution_name = $1, info = $2, html_content = $3, text_content = $4, updated_at = CURRENT_TIMESTAMP
            WHERE organization_id = $5 AND caution_id = $6
            """,
            caution_name,
            orjson.dumps(info).decode("utf-8"),
            html_content,
            text_content,
            organization_id,
            caution_id
        )

        if result == "UPDATE 0":
            raise All_Exceptions(
                message="Caution ID not found or does not belong to the organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update caution details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
