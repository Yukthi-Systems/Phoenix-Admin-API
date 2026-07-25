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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, status, uuid, orjson
from src.utils.models import All_Exceptions


PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


# -- Department for mailbox
# CREATE TABLE departments (
#     department_id UUID PRIMARY KEY,
#     organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

#     department_name VARCHAR(250) NOT NULL,
#     details JSONB NOT NULL,  -- metadata, not indexed

#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     UNIQUE (organization_id, department_name)
# );

async def create_new_department_entry(
    db_session: PgSession,
    organization_id: str,
    department_name: str,
    details: dict
) -> None:
    """
    Create a new department entry in the database
    """
    try:
        # Insert the new department into the database
        await db_session.execute(
            """
            INSERT INTO departments (department_id, organization_id, department_name, details)
            VALUES ($1, $2, $3, $4)
            """,
            str(uuid.uuid4()),
            organization_id,
            department_name,
            orjson.dumps(details).decode("utf-8")
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new department entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_department_details(
    db_session: PgSession,
    organization_id: str,
    department_id: str
) -> dict:
    """
    Get details of a specific department
    """
    try:
        # Fetch the department details from the database
        result = await db_session.fetchrow(
            """
            SELECT department_id, organization_id, department_name, details, created_at, updated_at
            FROM departments
            WHERE organization_id = $1 AND department_id = $2
            """,
            organization_id,
            department_id
        )
        if result is None:
            raise All_Exceptions(
                message="Department ID not found or does not belong to the organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Convert the result to a dictionary
        return {
            "department_id": str(result["department_id"]),
            "organization_id": str(result["organization_id"]),
            "department_name": result["department_name"],
            "details": orjson.loads(result["details"]),
            "created_at": result["created_at"].isoformat(),
            "updated_at": result["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch department details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_departments_under_organization(
    db_session: PgSession,
    organization_id: str,
    search_query: str = "",
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    List all departments under an organization with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM departments WHERE organization_id = $1 AND department_name ILIKE $2
            """,
            organization_id,
            f"%{search_query}%"
        )

        if not total_count or total_count == 0:
            return {
                "departments": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        offset = (page - 1) * page_size
        departments = await db_session.fetch(
            """
            SELECT department_id, department_name, created_at, updated_at
            FROM departments
            WHERE organization_id = $1 AND department_name ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            organization_id,
            f"%{search_query}%",
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        department_list = [
            {
                "department_id": str(department["department_id"]),
                "department_name": department["department_name"],
                "created_at": department["created_at"].isoformat(),
                "updated_at": department["updated_at"].isoformat()
            }
            for department in departments
        ]

        return {
            "departments": department_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list departments for organization {organization_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_departments_under_org(db_session: PgSession, organization_id: str, page: int = 1, page_size: int = 10) -> dict:
    """
    Export all departments under an organization with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM departments WHERE organization_id = $1
            """,
            organization_id
        )

        if not total_count or total_count == 0:
            return {
                "departments": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        offset = (page - 1) * page_size
        departments = await db_session.fetch(
            """
            SELECT department_id, department_name, details, created_at, updated_at
            FROM departments
            WHERE organization_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        department_list = [
            {
                "department_id": str(department["department_id"]),
                "department_name": department["department_name"],
                "details": orjson.loads(department["details"]),
                "created_at": department["created_at"].isoformat(),
                "updated_at": department["updated_at"].isoformat()
            }
            for department in departments
        ]

        return {
            "departments": department_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export departments for organization {organization_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_department(
    db_session: PgSession,
    organization_id: str,
    department_id: str
) -> None:
    """
    Delete a department from the database
    """
    try:
        # Delete the department from the database
        result = await db_session.execute(
            """
            DELETE FROM departments
            WHERE organization_id = $1 AND department_id = $2
            """,
            organization_id,
            department_id
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Department ID not found or does not belong to the organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete department: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_department_details(
    db_session: PgSession,
    organization_id: str,
    department_id: str,
    department_name: str,
    details: dict
) -> None:
    """
    Update the details of a specific department
    """
    try:
        # Update the department details in the database
        result = await db_session.execute(
            """
            UPDATE departments
            SET department_name = $1, details = $2, updated_at = CURRENT_TIMESTAMP
            WHERE organization_id = $3 AND department_id = $4
            """,
            department_name,
            orjson.dumps(details).decode("utf-8"),
            organization_id,
            department_id
        )

        if result == "UPDATE 0":
            raise All_Exceptions(
                message="Department ID not found or does not belong to the organization",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update department details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
