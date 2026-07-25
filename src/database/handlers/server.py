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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, logging, status, uuid, orjson
from src.utils.models import All_Exceptions


PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


async def create_new_server_entry(
    db_session: PgSession,
    host_name: str,
    smtp_port: int,
    server_info: dict,
    is_active: bool,
    is_monitoring: bool,
    is_mailbox_server: bool,
    is_accepting_new_mailboxes: bool,
    quota_allocated: float,
    quota_utilized: float,
    storage_path: str
) -> str:
    """
    Create a new server entry in the database
    """
    try:
        # Generate a unique server ID
        server_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, host_name))

        # Insert the new server into the database
        await db_session.execute(
            """
            INSERT INTO servers (server_id, host_name, server_info, is_active,
            smtp_port, quota_allocated, quota_utilized, storage_path, is_monitoring, is_mailbox_server, is_accepting_new_mailboxes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            server_id,
            host_name,
            orjson.dumps(server_info).decode("utf-8"),
            is_active,
            smtp_port,
            quota_allocated,
            quota_utilized,
            storage_path,
            is_monitoring,
            is_mailbox_server,
            is_accepting_new_mailboxes
        )

        return server_id

    except Exception as e:
        logging.error(f"Error creating new server entry: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new server entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_servers(db_session: PgSession, query: str = "", page: int = 1, page_size: int = 10) -> dict:
    """
    Retrieve all servers with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM servers WHERE host_name ILIKE '%' || $1 || '%'
            """,
            query
        )

        offset = (page - 1) * page_size
        servers = await db_session.fetch(
            """
            SELECT server_id, host_name, is_active, quota_allocated, is_accepting_new_mailboxes,
            quota_utilized, created_at, is_monitoring, is_mailbox_server
            FROM servers
            WHERE host_name ILIKE '%' || $1 || '%'
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            query,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        server_list = [
            {
                "server_id": str(server["server_id"]),
                "host_name": server["host_name"],
                "is_active": server["is_active"],
                "is_monitoring": server["is_monitoring"],
                "is_mailbox_server": server["is_mailbox_server"],
                "is_accepting_new_mailboxes": server["is_accepting_new_mailboxes"],
                "quota_allocated": float(server["quota_allocated"]),
                "quota_utilized": float(server["quota_utilized"]),
                "created_at": server["created_at"].isoformat()
            }
            for server in servers
        ]

        return {
            "servers": server_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    except Exception as e:
        logging.error(f"Error retrieving servers: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to retrieve servers: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_server_details(db_session: PgSession, server_id: str) -> dict:
    """
    Retrieve details of a specific server by its ID
    """
    try:
        server = await db_session.fetchrow(
            """
            SELECT server_id, host_name, server_info, is_active, smtp_port, is_mailbox_server, is_accepting_new_mailboxes,
                   quota_allocated, quota_utilized, storage_path, created_at, is_monitoring
            FROM servers
            WHERE server_id = $1
            """,
            server_id
        )

        if not server:
            raise All_Exceptions(
                message="Server not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "server_id": str(server["server_id"]),
            "host_name": server["host_name"],
            "smtp_port": int(server["smtp_port"]),
            "server_info": orjson.loads(server["server_info"]),
            "is_active": server["is_active"],
            "is_mailbox_server": server["is_mailbox_server"],
            "is_accepting_new_mailboxes": server["is_accepting_new_mailboxes"],
            "quota_allocated": float(server["quota_allocated"]),
            "quota_utilized": float(server["quota_utilized"]),
            "storage_path": server["storage_path"],
            "created_at": server["created_at"].isoformat(),
            "is_monitoring": server["is_monitoring"]
        }

    except Exception as e:
        logging.error(f"Error retrieving server details: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to retrieve server details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_server_details(
    db_session: PgSession,
    server_id: str,
    smtp_port: int,
    server_info: dict,
    is_active: bool,
    is_monitoring: bool,
    is_mailbox_server: bool,
    is_accepting_new_mailboxes: bool,
    quota_allocated: float,
    storage_path: str
) -> None:
    """
    Update details of a specific server
    """
    # Check if the server exists
    existing_server = await db_session.fetchrow(
        """
        SELECT quota_utilized, is_active, quota_allocated
        FROM servers WHERE server_id = $1
        """,
        server_id
    )

    if not existing_server:
        raise All_Exceptions(
            message="Server not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Check if the server is active and quota is sufficient
    if not existing_server["is_active"]:
        raise All_Exceptions(
            message="Cannot update details of an inactive server",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )

    if quota_allocated <= float(existing_server["quota_utilized"]):
        # It should be greater than the current quota utilized (reverse the logic to raise an exception)
        raise All_Exceptions(
            message=f"Quota allocated must be greater than the current quota utilized ({existing_server['quota_utilized']}), but got {quota_allocated}",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )

    try:
        # Update the server details
        await db_session.execute(
            """
            UPDATE servers
            SET server_info = $1, is_active = $2, smtp_port = $3, is_mailbox_server = $4,
                is_accepting_new_mailboxes = $5, quota_allocated = $6, storage_path = $7, is_monitoring = $8
            WHERE server_id = $9 AND is_active = TRUE
            """,
            orjson.dumps(server_info).decode("utf-8"),
            is_active,
            smtp_port,
            is_mailbox_server,
            is_accepting_new_mailboxes,
            quota_allocated,
            storage_path,
            is_monitoring,
            server_id
        )

    except Exception as e:
        logging.error(f"Error updating server details: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update server details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_server_and_related_data(db_session: PgSession, server_id: str) -> None:
    """
    Delete a server and all related data (cascading delete)
    """
    try:
        # Check if the server exists
        existing_server = await db_session.fetchrow(
            """
            SELECT server_id FROM servers WHERE server_id = $1
            """,
            server_id
        )

        if not existing_server:
            raise All_Exceptions(
                message="Server not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Delete the server and all related data
        await db_session.execute(
            """
            DELETE FROM servers WHERE server_id = $1
            """,
            server_id
        )

    except Exception as e:
        logging.error(f"Error deleting server: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to delete server: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_server_active_status(db_session: PgSession, server_id: str, is_active: bool) -> None:
    """
    Update the active status of a specific server
    """
    try:
        # Update the server active status
        await db_session.execute(
            """
            UPDATE servers
            SET is_active = $1
            WHERE server_id = $2
            """,
            is_active,
            server_id
        )

    except Exception as e:
        logging.error(f"Error updating server active status: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update server active status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def quota_recalculation_and_update(db_session: PgSession) -> None:
    """
    Recalculate and update quota_utilized for all servers based on mailboxes
    """
    try:
        # Update Re-Calculated Quotas for Servers first
        await db_session.execute(
            """
            UPDATE servers s
            SET quota_utilized = sub.total_allocated
            FROM (
                SELECT
                    server_id,
                    ROUND(SUM(quota_allocated), 2) AS total_allocated
                FROM mailboxes
                GROUP BY server_id
            ) sub
            WHERE s.server_id = sub.server_id;
            """
        )

    except Exception as e:
        logging.error(f"Error recalculating and updating server quotas: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to recalculate and update server quotas: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
