"""
Handles all the Time Based One-Time Passwords (TOTP) for 2FA related database operations
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


# CREATE TABLE totp (
#     totp_id UUID PRIMARY KEY,
#     totp_name VARCHAR(100) NOT NULL,  -- e.g., 'My Office Phone'
#     user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
#     totp_secret TEXT NOT NULL,  -- Base32 encoded secret for TOTP
#     is_active BOOLEAN DEFAULT TRUE NOT NULL,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     UNIQUE (user_id, totp_name)
# );


async def create_new_totp_entry(db_session: PgSession, user_id: str, totp_name: str, totp_secret: str) -> None:
    """
    Create a new TOTP entry in the database
    """
    # Limit the number of TOTP entries per user by 10 devices
    existing_totp_count = await db_session.fetchval(
        """
        SELECT COUNT(*) FROM totp WHERE user_id = $1
        """,
        user_id
    )
    if existing_totp_count == 10:
        raise All_Exceptions(
            message="Maximum number of TOTP entries reached (10). Please delete an existing entry before adding a new one.",
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
        )

    try:
        # Insert the new TOTP into the database
        await db_session.execute(
            """
            INSERT INTO totp (totp_id, totp_name, user_id, totp_secret)
            VALUES ($1, $2, $3, $4)
            """,
            str(uuid.uuid4()),
            totp_name,
            user_id,
            totp_secret
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new TOTP entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_totp_secrets(db_session: PgSession, user_id: str) -> list[str]:
    """
    Get all TOTP secrets for a user
    """
    try:
        # Fetch all TOTP secrets for the user from the database
        results = await db_session.fetch(
            """
            SELECT totp_secret FROM totp WHERE user_id = $1 AND is_active = TRUE
            """,
            user_id
        )

        if not results:
            raise All_Exceptions(
                message="No active TOTP entries found for the user",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Extract and return the TOTP secrets
        return [result["totp_secret"] for result in results]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch TOTP secrets: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_totp_entry(db_session: PgSession, user_id: str, totp_id: str) -> None:
    """
    Delete a TOTP entry by its ID
    """
    try:
        # Delete the TOTP entry from the database
        result = await db_session.execute(
            """
            DELETE FROM totp WHERE totp_id = $1 AND user_id = $2
            """,
            totp_id,
            user_id
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="TOTP entry not found or already deleted",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete TOTP entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def can_enable_totp(db_session: PgSession, user_id: str) -> bool:
    """
    Check if a user can enable TOTP (i.e., they should have at least one active TOTP entry)
    """
    try:
        # Check if the user has any active TOTP entries
        result = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM totp WHERE user_id = $1 AND is_active = TRUE
            """,
            user_id
        )

        # If the count is greater than 0, they can enable TOTP
        return result > 0

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check if TOTP can be enabled: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def check_if_its_last_active_totp(db_session: PgSession, user_id: str) -> bool:
    """
    Check if the TOTP entry is the last active one for the user
    """
    try:
        # Count the number of active TOTP entries for the user
        result = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM totp WHERE user_id = $1 AND is_active = TRUE
            """,
            user_id
        )

        # If there's only one active TOTP entry, return True
        return result == 1

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check if it's the last active TOTP: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def alter_totp_entry(db_session: PgSession, user_id: str, totp_id: str, totp_name: str, is_active: bool) -> None:
    """
    Alter an existing TOTP entry
    """
    try:
        # If its last entry, and user is trying to disable it, raise an exception
        current_entry = await db_session.fetchrow(
            """
            SELECT is_active FROM totp WHERE totp_id = $1 AND user_id = $2
            """,
            totp_id,
            user_id
        )
        if current_entry is None:
            raise All_Exceptions(
                message="TOTP entry not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if not is_active and current_entry["is_active"] and await check_if_its_last_active_totp(db_session=db_session, user_id=user_id):
            raise All_Exceptions(
                message="Cannot disable the last active TOTP entry. Please create another TOTP entry before disabling this one.",
                status_code=status.HTTP_412_PRECONDITION_FAILED
            )

        # Update the TOTP entry in the database
        result = await db_session.execute(
            """
            UPDATE totp SET totp_name = $1, is_active = $2 WHERE totp_id = $3 AND user_id = $4
            """,
            totp_name,
            is_active,
            totp_id,
            user_id
        )

        if result == "UPDATE 0":
            raise All_Exceptions(
                message="TOTP entry not found or already updated",
                status_code=status.HTTP_406_NOT_ACCEPTABLE
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to alter TOTP entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_all_totp_entries(db_session: PgSession, user_id: str) -> list[dict]:
    """
    List all TOTP entries for a user
    """
    try:
        # Fetch all TOTP entries for the user from the database
        results = await db_session.fetch(
            """
            SELECT totp_id, totp_name, is_active, created_at
            FROM totp WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id
        )

        if not results:
            raise All_Exceptions(
                message="No TOTP entries found for the user",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Convert results to a list of dictionaries
        return [
            {
                "totp_id": str(result["totp_id"]),
                "totp_name": result["totp_name"],
                "is_active": result["is_active"],
                "created_at": result["created_at"].isoformat()
            } for result in results
        ]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list TOTP entries: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_totp_entry_active_status(db_session: PgSession, user_id: str) -> dict[str, bool]:
    """
    Get the active status of all TOTP entries for a user
    """
    try:
        # Fetch the active status of all TOTP entries for the user
        results = await db_session.fetch(
            """
            SELECT totp_id, is_active FROM totp WHERE user_id = $1
            """,
            user_id
        )

        if not results:
            raise All_Exceptions(
                message="No TOTP entries found for the user",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Convert results to a dictionary with TOTP ID as key and active status as value
        return {str(result["totp_id"]): result["is_active"] for result in results}

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to get TOTP entry active status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_auth_session(db_session: PgSession, session_id: str, phone: str, email: str, device_details: dict) -> None:
    """
    Create a new authentication session
    """
    try:
        await db_session.execute(
            """
            INSERT INTO auth_sessions (session_id, phone, email, domain_name, device_details)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session_id,
            phone,
            email,
            email.split('@')[1].lower(),  # Extract domain name from email
            orjson.dumps(device_details).decode("utf-8")
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create auth session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_auth_session(db_session: PgSession, session_id: str, phone: str, email: str) -> None:
    """
    Delete an authentication session
    """
    try:
        await db_session.execute(
            """
            DELETE FROM auth_sessions WHERE session_id = $1 AND phone = $2 AND email = $3
            """,
            session_id,
            phone,
            email
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete auth session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def check_if_app_session_is_valid(db_session: PgSession, session_id: str, phone: str, email: str) -> bool:
    """
    Get client sessions for the Auth App
    """
    try:
        session_active = await db_session.fetchval(
            """
            SELECT is_active FROM auth_sessions WHERE session_id = $1 AND phone = $2 AND email = $3
            """,
            session_id,
            phone,
            email
        )

        return session_active

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check if app session is valid: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_client_sessions_for_app(db_session: PgSession, primary_phone: str) -> list[dict]:
    """
    Get client sessions for the Auth App
    """
    try:
        results = await db_session.fetch(
            """
            SELECT origin_ip,
                   attempted_by,
                   geo_ip_location,
                   attempted_at,
                   is_active,
                   session_expires_at
            FROM mailbox_sessions
            WHERE primary_phone = $1
            """,
            primary_phone
        )

        return [
            {
                "origin_ip": result["origin_ip"],
                "attempted_by": result["attempted_by"],
                "geo_ip_location": orjson.loads(result["geo_ip_location"]),
                "is_active": result["is_active"],
                "attempted_at": result["attempted_at"].isoformat(),
                "session_expires_at": result["session_expires_at"].isoformat()
            } for result in results
        ]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to get client sessions for app: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def approve_deny_client_session_for_app(db_session: PgSession, primary_phone: str, origin_ip: str, is_active: bool, attempted_by: str) -> None:
    """
    Approve or deny a client session for the Auth App
    """
    try:
        await db_session.execute(
            """
            UPDATE mail25_app_sessions
            SET is_active = $1
            WHERE origin_ip = $2 AND attempted_by = $3 AND primary_phone = $4
            """,
            is_active,
            origin_ip,
            attempted_by,
            primary_phone
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to approve/deny client session for app: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def auth_app_validate_user(db_session: PgSession, phone: str, email: str) -> bool:
    """
    Check if the provided phone number is associated with any user in the system.
    Check if the provided email is associated with any user in the system.
    Note: Both phone number and email can belong to different users but both must exist.
    """
    try:
        result = await db_session.fetchrow(
            """
            SELECT 
                EXISTS (SELECT 1 FROM mailboxes WHERE primary_phone = $1) AS phone_exists,
                EXISTS (SELECT 1 FROM mailboxes WHERE email = $2) AS email_exists
            """,
            phone,
            email
        )

        return result["phone_exists"] and result["email_exists"]

    except Exception as e:
        logging.error(f"Failed to validate user for Auth App: {e}")
        return False


async def get_app_sessions(db_session: PgSession, domain_name: str, page: int, size: int) -> dict:
    """
    Get application sessions for a specific domain with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM mail25_app_sessions WHERE domain_name = $1
            """,
            domain_name
        )

        if total_count == 0:
            return {
                "total_count": 0,
                "has_next": False,
                "has_previous": False,
                "total_pages": 0,
                "page_size": size,
                "current_page": page,
                "data": []
            }

        offset = (page - 1) * size
        results = await db_session.fetch(
            """
            SELECT session_id, phone, email, device_details, last_active_at
            FROM mail25_app_sessions
            WHERE domain_name = $1
            ORDER BY last_active_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            size,
            offset
        )

        data = [
            {
                "session_id": str(result["session_id"]),
                "phone": result["phone"],
                "email": result["email"],
                "device_details": orjson.loads(result["device_details"]),
                "last_active_at": result["last_active_at"].isoformat()
            } for result in results
        ]

        return {
            "total_count": total_count,
            "has_next": (offset + size) < total_count,
            "has_previous": offset > 0,
            "total_pages": (total_count + size - 1) // size,
            "page_size": size,
            "current_page": page,
            "data": data
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to get app sessions: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_app_session(db_session: PgSession, session_id: str, domain_name: str) -> None:
    """
    Delete an application session by its ID and domain name
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM mail25_app_sessions WHERE session_id = $1 AND domain_name = $2
            """,
            session_id,
            domain_name
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="App session not found or already deleted",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete app session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_sso_sessions(db_session: PgSession, domain_name: str, page: int, size: int) -> dict:
    """
    List SSO sessions for a specific domain with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM sso_sessions WHERE domain_name = $1
            """,
            domain_name
        )
        if total_count == 0:
            return {
                "total_count": 0,
                "has_next": False,
                "has_previous": False,
                "total_pages": 0,
                "page_size": size,
                "current_page": page,
                "data": []
            }
        
        offset = (page - 1) * size
        results = await db_session.fetch(
            """
            SELECT session_id, email, device_details, created_at, last_auth_at, is_active
            FROM sso_sessions
            WHERE domain_name = $1
            ORDER BY last_auth_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            size,
            offset
        )

        data = [
            {
                "session_id": str(result["session_id"]),
                "email": result["email"],
                "device_details": orjson.loads(result["device_details"]),
                "is_active": result["is_active"],
                "created_at": result["created_at"].isoformat(),
                "last_auth_at": result["last_auth_at"].isoformat()
            } for result in results
        ]

        return {
            "total_count": total_count,
            "has_next": (offset + size) < total_count,
            "has_previous": offset > 0,
            "total_pages": (total_count + size - 1) // size,
            "page_size": size,
            "current_page": page,
            "data": data
        }
    
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list SSO sessions: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_sso_session(db_session: PgSession, session_id: str, domain_name: str) -> None:
    """
    Delete an SSO session by its ID and domain name
    """
    try:
        result = await db_session.execute(
            """
            DELETE FROM sso_sessions WHERE session_id = $1 AND domain_name = $2
            """,
            session_id,
            domain_name
        )

        if result == "DELETE 0":
            raise All_Exceptions(
                message="SSO session not found or already deleted",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete SSO session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_sso_session_active_status(db_session: PgSession, session_id: str, domain_name: str, is_active: bool) -> None:
    """
    Update the active status of an SSO session
    """
    try:
        result = await db_session.execute(
            """
            UPDATE sso_sessions SET is_active = $1 WHERE session_id = $2 AND domain_name = $3
            """,
            is_active,
            session_id,
            domain_name
        )

        if result == "UPDATE 0":
            raise All_Exceptions(
                message="SSO session not found or already updated",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update SSO session active status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
