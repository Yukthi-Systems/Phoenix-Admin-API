"""
Handles all the Attachment Policy related database operations

-- Attachment Policies for Domains (Attachment Restrictions)
CREATE TABLE attachment_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Corporate Attachment Policy'
    policy_description TEXT NOT NULL,  -- Description of the policy

    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,
    blocked_file_types TEXT[] NOT NULL,  -- e.g., ['exe', 'bat', 'cmd']
    allowed_file_types TEXT[] NOT NULL,  -- e.g., ['pdf', 'docx', 'xlsx']
    max_attachment_size_mb NUMERIC(5,2) NOT NULL,  -- Max attachment size in MB

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
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


async def create_new_attachment_policy_entry(
    db_session: PgSession,
    domain_name: str,
    policy_name: str,
    policy_description: str,
    blocked_file_types: list[str],
    allowed_file_types: list[str],
    max_attachment_size_mb: float,
    is_active: bool = True
) -> None:
    """
    Create a new attachment policy entry in the database
    """
    try:
        # Insert the new attachment policy into the database
        await db_session.execute(
            """
            INSERT INTO attachment_policies (policy_id, domain_name, policy_name,
            policy_description, blocked_file_types, allowed_file_types,
            max_attachment_size_mb, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            str(uuid.uuid4()),
            domain_name,
            policy_name,
            policy_description,
            blocked_file_types,
            allowed_file_types,
            max_attachment_size_mb,
            is_active
        )

    except Exception as e:
        logging.error(f"Error creating new attachment policy entry: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new attachment policy entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_attachment_policy_by_domain(
    db_session: PgSession,
    domain_name: str,
    search_query: str = "",
    page: int = 1,
    limit: int = 10
) -> dict:
    """
    Get attachment policies for a specific domain with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM attachment_policies WHERE domain_name = $1 AND policy_name ILIKE $2
            """,
            domain_name,
            f"%{search_query}%"
        )

        offset = (page - 1) * limit
        policies = await db_session.fetch(
            """
            SELECT policy_id, policy_name, is_active, created_at, updated_at
            FROM attachment_policies
            WHERE domain_name = $1 AND policy_name ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            domain_name,
            f"%{search_query}%",
            limit,
            offset
        )

        # Convert the result to a list of dictionaries
        policy_list = [
            {
                "policy_id": str(policy["policy_id"]),
                "policy_name": policy["policy_name"],
                "is_active": policy["is_active"],
                "created_at": policy["created_at"].isoformat(),
                "updated_at": policy["updated_at"].isoformat()
            }
            for policy in policies
        ]

        return {
            "attachment_policies": policy_list,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }

    except Exception as e:
        logging.error(f"Error retrieving attachment policies for domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to retrieve attachment policies for domain {domain_name}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_attachment_policies_by_domain(
    db_session: PgSession,
    domain_name: str,
    page: int,
    limit: int
) -> list[dict]:
    """
    Export attachment policies for a specific domain with pagination
    """
    try:
        offset = (page - 1) * limit
        policies = await db_session.fetch(
            """
            SELECT policy_id, policy_name, policy_description, blocked_file_types,
            allowed_file_types, max_attachment_size_mb, is_active, created_at, updated_at
            FROM attachment_policies
            WHERE domain_name = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            limit,
            offset
        )

        # Convert the result to a list of dictionaries
        policy_list = [
            {
                "policy_id": str(policy["policy_id"]),
                "policy_name": policy["policy_name"],
                "policy_description": policy["policy_description"],
                "blocked_file_types": policy["blocked_file_types"],
                "allowed_file_types": policy["allowed_file_types"],
                "max_attachment_size_mb": float(policy["max_attachment_size_mb"]),
                "is_active": policy["is_active"],
                "created_at": policy["created_at"].isoformat(),
                "updated_at": policy["updated_at"].isoformat()
            }
            for policy in policies
        ]

        return policy_list

    except Exception as e:
        logging.error(f"Error exporting attachment policies for domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to export attachment policies for domain {domain_name}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_attachment_policy_details_by_id(
    db_session: PgSession,
    domain_name: str,
    policy_id: str
) -> dict:
    """
    Get details of a specific attachment policy by its ID
    """
    try:
        policy = await db_session.fetchrow(
            """
            SELECT policy_id, domain_name, policy_name, policy_description,
            blocked_file_types, allowed_file_types, max_attachment_size_mb,
            is_active, created_at, updated_at
            FROM attachment_policies
            WHERE policy_id = $1 AND domain_name = $2
            """,
            policy_id,
            domain_name
        )

        if not policy:
            raise All_Exceptions(
                message="Attachment Policy not found or not accessible by this domain",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "policy_id": str(policy["policy_id"]),
            "domain_name": policy["domain_name"],
            "policy_name": policy["policy_name"],
            "policy_description": policy["policy_description"],
            "blocked_file_types": policy["blocked_file_types"],
            "allowed_file_types": policy["allowed_file_types"],
            "max_attachment_size_mb": float(policy["max_attachment_size_mb"]),
            "is_active": policy["is_active"],
            "created_at": policy["created_at"].isoformat(),
            "updated_at": policy["updated_at"].isoformat()
        }

    except Exception as e:
        logging.error(f"Error retrieving attachment policy details for ID {policy_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to retrieve attachment policy details for ID {policy_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_attachment_policy_by_id(
    db_session: PgSession,
    domain_name: str,
    policy_id: str
) -> None:
    """
    Delete an attachment policy by its ID
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM attachment_policies WHERE policy_id = $1 AND domain_name = $2
            """,
            policy_id,
            domain_name
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="Attachment Policy not found or already deleted",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error deleting attachment policy with ID {policy_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to delete attachment policy with ID {policy_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_attachment_policy_details(
    db_session: PgSession,
    policy_id: str,
    domain_name: str,
    policy_name: str,
    policy_description: str,
    blocked_file_types: list[str],
    allowed_file_types: list[str],
    max_attachment_size_mb: float,
    is_active: bool
) -> None:
    """
    Update the details of a specific attachment policy
    """
    try:
        result = await db_session.execute(
            """
            UPDATE attachment_policies
            SET policy_name = $1, policy_description = $2, blocked_file_types = $3,
            allowed_file_types = $4, max_attachment_size_mb = $5, is_active = $6
            WHERE policy_id = $7 AND domain_name = $8
            """,
            policy_name,
            policy_description,
            blocked_file_types,
            allowed_file_types,
            max_attachment_size_mb,
            is_active,
            policy_id,
            domain_name
        )

        if result == "UPDATE 0":
            raise All_Exceptions(
                message="Attachment Policy not found or no changes made",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error updating attachment policy with ID {policy_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update attachment policy with ID {policy_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
