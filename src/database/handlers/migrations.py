"""
Handles all the Migrations related to server management in the database
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


# -- MailBox that are currently being migrated/moved across servers
# CREATE TABLE mailbox_migrations (
#     migration_id UUID PRIMARY KEY,

#     email VARCHAR(254) NOT NULL REFERENCES mailboxes(email) ON DELETE CASCADE,
#     migration_status VARCHAR(50) NOT NULL,  -- e.g., 'in_progress', 'completed', 'failed'

#     source_server_id UUID NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
#     target_server_id UUID NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,

#     start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     end_time TIMESTAMP,  -- NULL if still in progress

#     migration_details JSONB NOT NULL  -- metadata, not indexed
# );


async def create_new_migration_entry(
    db_session: PgSession,
    email: str,
    source_server_id: str,
    target_server_id: str,
    migration_details: dict
) -> str:
    """
    Create a new migration entry in the database
    Possible Statuses:
    - INITIALIZING: Migration is being prepared
    - IN_PROGRESS: Migration is currently happening
    - COMPLETED: Migration has successfully completed
    - FAILED: Migration has failed
    """
    try:
        # Generate a unique migration ID
        migration_id = str(uuid.uuid4())

        # Insert the new migration into the database
        await db_session.execute(
            """
            INSERT INTO mailbox_migrations (migration_id, email, migration_status,
                                            source_server_id, target_server_id,
                                            migration_details)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            migration_id,
            email,
            'INITIALIZING',  # Initial status
            source_server_id,
            target_server_id,
            orjson.dumps(migration_details).decode("utf-8")
        )

        return migration_id

    except Exception as e:
        logging.error(f"Error creating new migration entry: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new migration entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_migrations_from_source_server_id(
    db_session: PgSession,
    server_id: str,
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    List all migrations from a specific source server with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM mailbox_migrations
            WHERE source_server_id = $1
            """,
            server_id
        )

        offset = (page - 1) * page_size
        migrations = await db_session.fetch(
            """
            SELECT migration_id, email, migration_status, start_time, end_time,
                   target_server_id, migration_details
            FROM mailbox_migrations
            WHERE source_server_id = $1
            ORDER BY start_time DESC
            LIMIT $2 OFFSET $3
            """,
            server_id,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        migration_list = [
            {
                "migration_id": str(migration["migration_id"]),
                "email": migration["email"],
                "migration_status": migration["migration_status"],
                "start_time": migration["start_time"].isoformat(),
                "end_time": migration["end_time"].isoformat() if migration["end_time"] else None,
                "target_server_id": str(migration["target_server_id"]),
                "migration_details": orjson.loads(migration["migration_details"])
            }
            for migration in migrations
        ]

        return {
            "migrations": migration_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    except Exception as e:
        logging.error(f"Error listing migrations: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to list migrations: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_migrations_from_email(
    db_session: PgSession,
    email: str,
    page: int = 1,
    page_size: int = 10
) -> dict:
    """
    List all migrations for a specific email with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM mailbox_migrations
            WHERE email = $1
            """,
            email
        )

        offset = (page - 1) * page_size
        migrations = await db_session.fetch(
            """
            SELECT migration_id, source_server_id, migration_status, start_time, end_time,
                   target_server_id, migration_details
            FROM mailbox_migrations
            WHERE email = $1
            ORDER BY start_time DESC
            LIMIT $2 OFFSET $3
            """,
            email,
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        migration_list = [
            {
                "migration_id": str(migration["migration_id"]),
                "source_server_id": str(migration["source_server_id"]),
                "migration_status": migration["migration_status"],
                "start_time": migration["start_time"].isoformat(),
                "end_time": migration["end_time"].isoformat() if migration["end_time"] else None,
                "target_server_id": str(migration["target_server_id"]),
                "migration_details": orjson.loads(migration["migration_details"])
            }
            for migration in migrations
        ]

        return {
            "migrations": migration_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }

    except Exception as e:
        logging.error(f"Error listing migrations for email {email}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to list migrations for email {email}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_overall_migration_stats(db_session: PgSession, server_id: str) -> dict:
    """
    Get overall migration statistics for a specific server
    Get total of migrations, completed migrations, in-progress migrations, and failed migrations (all types)
    """
    try:
        stats = await db_session.fetchrow(
            """
            SELECT
                COUNT(*) AS total_migrations,
                COUNT(CASE WHEN migration_status = 'INITIALIZING' THEN 1 END) AS initializing_migrations,
                COUNT(CASE WHEN migration_status = 'COMPLETED' THEN 1 END) AS completed_migrations,
                COUNT(CASE WHEN migration_status = 'IN_PROGRESS' THEN 1 END) AS in_progress_migrations,
                COUNT(CASE WHEN migration_status = 'FAILED' THEN 1 END) AS failed_migrations
            FROM mailbox_migrations
            WHERE source_server_id = $1 OR target_server_id = $1
            """,
            server_id
        )
        if not stats:
            return {
                "total_migrations": 0,
                "initializing_migrations": 0,
                "completed_migrations": 0,
                "in_progress_migrations": 0,
                "failed_migrations": 0
            }

        return {
            "total_migrations": stats["total_migrations"],
            "initializing_migrations": stats["initializing_migrations"],
            "completed_migrations": stats["completed_migrations"],
            "in_progress_migrations": stats["in_progress_migrations"],
            "failed_migrations": stats["failed_migrations"]
        }

    except Exception as e:
        logging.error(f"Error getting overall migration stats for server {server_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to get overall migration stats for server {server_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def do_manual_mailbox_migration(
    source_server_id: str,
    target_server_id: str,
    email: str,
    db_session: PgSession
) -> None:
    """
    Perform the manual mailbox migration logic
    This is a placeholder function where the actual migration logic would be implemented
    """
    # First check if the mailbox exists on the source server
    # Along that, Get MailBox Allocated Size (to ensure target server has enough space and other checks)
    mailbox_size = await db_session.fetchval(
        """
        SELECT quota_allocated FROM mailboxes
        WHERE email = $1 AND server_id = $2 AND is_enabled = TRUE
        """,
        email,
        source_server_id
    )

    if not mailbox_size:
        raise All_Exceptions(
            message=f"Mailbox {email} does not exist on source server {source_server_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Get Target Server Available Space
    target_server_quota = await db_session.fetchval(
        """
        SELECT quota_allocated - quota_utilized FROM servers
        WHERE server_id = $1 AND is_active = TRUE
        """,
        target_server_id
    )
    if target_server_quota is None:
        raise All_Exceptions(
            message=f"Target server {target_server_id} does not exist or is inactive",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Check if target server has enough space
    if target_server_quota < mailbox_size:
        raise All_Exceptions(
            message=f"Target server {target_server_id} does not have enough space for mailbox {email}, required: {mailbox_size}, available: {target_server_quota}",
            status_code=status.HTTP_409_CONFLICT
        )

    # Check if there is already an ongoing migration for this mailbox
    ongoing_migration = await db_session.fetchval(
        """
        SELECT COUNT(*) FROM mailbox_migrations
        WHERE email = $1 AND migration_status = 'IN_PROGRESS'
        """,
        email
    )

    if ongoing_migration > 0:
        raise All_Exceptions(
            message=f"Mailbox {email} is already undergoing migration",
            status_code=status.HTTP_409_CONFLICT
        )

    # Now just move the mailbox to the target server
    await db_session.execute(
        """
        UPDATE mailboxes
        SET server_id = $1
        WHERE email = $2 AND server_id = $3 AND is_enabled = TRUE
        """,
        target_server_id,
        email,
        source_server_id
    )

    # Remove the quota utilized from source server and add to target server
    await db_session.execute(
        """
        UPDATE servers
        SET quota_utilized = quota_utilized - $1
        WHERE server_id = $2 AND is_active = TRUE
        """,
        mailbox_size,
        source_server_id
    )

    # Add quota to target server
    await db_session.execute(
        """
        UPDATE servers
        SET quota_utilized = quota_utilized + $1
        WHERE server_id = $2 AND is_active = TRUE
        """,
        mailbox_size,
        target_server_id
    )

    # Add a manual migration entry with status COMPLETED
    migration_id = str(uuid.uuid4())    # Generate a unique migration ID

    await db_session.execute(
        """
        INSERT INTO mailbox_migrations (migration_id, email, migration_status,
                                        source_server_id, target_server_id,
                                        migration_details, start_time, end_time)
        VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        migration_id,
        email,
        'COMPLETED',  # Status
        source_server_id,
        target_server_id,
        orjson.dumps({"method": "manual_bypass"}).decode("utf-8")
    )


async def create_new_imap_sync_job(
    db_session: PgSession,
    from_email: str,
    from_email_password: str,
    from_imap_server: str,
    from_imap_port: int,
    to_email: str,
    to_domain_name: str
):
    """
    Create a new IMAP Sync Job in the database
    """
    try:
        # Generate a unique job ID
        job_id = str(uuid.uuid4())

        # Insert the new IMAP Sync Job into the database
        await db_session.execute(
            """
            INSERT INTO imap_sync_jobs (job_id, from_email, from_email_password,
                                        from_imap_server, from_imap_port,
                                        to_email, to_domain_name, sync_status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            job_id,
            from_email,
            from_email_password,
            from_imap_server,
            from_imap_port,
            to_email,
            to_domain_name,
            'PENDING'  # Initial status
        )

        return job_id

    except Exception as e:
        logging.error(f"Error creating new IMAP Sync Job: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new IMAP Sync Job: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_all_paginated_imap_sync_jobs(db_session: PgSession, domain_name: str, page: int, limit: int) -> dict:
    """
    Fetch all paginated IMAP Sync Jobs for a specific domain
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM imap_sync_jobs
            WHERE to_domain_name = $1
            """,
            domain_name
        )

        offset = (page - 1) * limit
        jobs = await db_session.fetch(
            """
            SELECT job_id, from_email, from_imap_server, from_imap_port,
                   to_email, sync_status, created_at, updated_at
            FROM imap_sync_jobs
            WHERE to_domain_name = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            limit,
            offset
        )

        # Convert the result to a list of dictionaries
        job_list = [
            {
                "job_id": str(job["job_id"]),
                "from_email": job["from_email"],
                "from_imap_server": job["from_imap_server"],
                "from_imap_port": job["from_imap_port"],
                "to_email": job["to_email"],
                "sync_status": job["sync_status"],
                "created_at": job["created_at"].isoformat(),
                "updated_at": job["updated_at"].isoformat()
            }
            for job in jobs
        ]

        return {
            "imap_sync_jobs": job_list,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }

    except Exception as e:
        logging.error(f"Error fetching IMAP Sync Jobs for domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch IMAP Sync Jobs for domain {domain_name}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
