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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, status, uuid, orjson, datetime
from src.utils.base.constants import MAX_AGE_OF_CACHE
from .organization import validate_organization_quota
from src.utils.models import All_Exceptions

PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


async def _raise_check_user_name_exists(db_session: PgSession, user_name: str, raise_exception_if_exists: bool = False) -> None:
    """
    Check if the user name already exists in the database
    Returns None if the user name does not exist, raises an exception otherwise
    """
    row = await db_session.fetchrow(
        "SELECT 1 FROM users WHERE user_name = $1 AND is_active = TRUE", user_name
    )
    if row and raise_exception_if_exists:
        raise All_Exceptions(
            message="User already exists",
            status_code=status.HTTP_409_CONFLICT
        )
    elif not row and not raise_exception_if_exists:
        raise All_Exceptions(
            message="User does not exist or is inactive",
            status_code=status.HTTP_404_NOT_FOUND
        )


async def get_basic_user_details(db_session: PgSession, user_name: str) -> dict:
    """
    Get domain details from the database
    """
    # Check if the user exists
    await _raise_check_user_name_exists(db_session=db_session, user_name=user_name, raise_exception_if_exists=False)

    # Fetch user details
    try:
        row = await db_session.fetchrow(
            """
            SELECT user_id, user_name, user_email, primary_phone, display_name,
            password_hash, user_details, is_active, is_totp_2fa_active,
            is_sms_2fa_active, is_email_2fa_active, is_email_verified, is_phone_verified,
            permissions_template, permissions, organization_id, created_at
            FROM users WHERE user_name = $1 AND is_active = TRUE
            """,
            user_name
        )
        if row:
            return {
                "user_id": str(row["user_id"]),
                "user_name": user_name,
                "user_email": row["user_email"],
                "primary_phone": row["primary_phone"],
                "display_name": row["display_name"],
                "password_hash": row["password_hash"],
                "user_details": orjson.loads(row["user_details"]),
                "is_active": row["is_active"],
                "is_totp_2fa_active": row["is_totp_2fa_active"],
                "is_sms_2fa_active": row["is_sms_2fa_active"],
                "is_email_2fa_active": row["is_email_2fa_active"],
                "is_email_verified": row["is_email_verified"],
                "is_phone_verified": row["is_phone_verified"],
                "permissions_template": orjson.loads(row["permissions_template"]),
                "permissions": list(set(row["permissions"])),
                "organization_id": str(row["organization_id"]),
                "created_at": row["created_at"].isoformat()
            }
        else:
            raise All_Exceptions(
                message="User not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch user details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_basic_user_details_by_id(db_session: PgSession, user_id: str, organization_id: str) -> dict:
    """
    Get domain details from the database
    """
    # Fetch user details
    try:
        row = await db_session.fetchrow(
            """
            SELECT user_id, user_name, user_email, primary_phone,
            user_details, is_active, is_totp_2fa_active, display_name,
            is_sms_2fa_active, is_email_2fa_active, is_email_verified, is_phone_verified,
            permissions_template, permissions, organization_id, created_at
            FROM users WHERE user_id = $1 AND organization_id = $2
            """,
            user_id,
            organization_id
        )
        if row:
            return {
                "user_id": str(row["user_id"]),
                "user_name": row["user_name"],
                "user_email": row["user_email"],
                "primary_phone": row["primary_phone"],
                "display_name": row["display_name"],
                "user_details": orjson.loads(row["user_details"]),
                "is_active": row["is_active"],
                "is_totp_2fa_active": row["is_totp_2fa_active"],
                "is_sms_2fa_active": row["is_sms_2fa_active"],
                "is_email_2fa_active": row["is_email_2fa_active"],
                "is_email_verified": row["is_email_verified"],
                "is_phone_verified": row["is_phone_verified"],
                "permissions_template": orjson.loads(row["permissions_template"]),
                "permissions": list(set(row["permissions"])),
                "organization_id": str(row["organization_id"]),
                "created_at": row["created_at"].isoformat()
            }

        else:
            raise All_Exceptions(
                message="User not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch user details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_user_session_in_cache(cache_session: MemCacheSession, user_details: dict) -> tuple[str, str]:
    """
    Create a user session in the cache and return the session ID and CSRF token
    This function generates a session ID and CSRF token, and stores the user name and CSRF token in the cache
    """
    try:
        # Create a session ID (UUID)
        session_id = str(uuid.uuid4())
        csrf_token = str(uuid.uuid4())
        user_details["csrf_token"] = csrf_token

        # Store the session details in the cache
        await cache_session.set(
            key=session_id.encode("utf-8"),
            value=orjson.dumps(user_details),
            exptime=MAX_AGE_OF_CACHE
        )

        return session_id, csrf_token

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create user session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_new_user(
    db_session: PgSession,
    user_name: str,
    user_email: str,
    primary_phone: str,
    display_name: str,
    password_hash: str,
    user_details: dict,
    is_active: bool,
    permissions_template: dict,
    permissions: list[str],
    organization_id: str
) -> None:
    """
    Create a new user in the database
    """
    # Check if the user already exists
    await _raise_check_user_name_exists(db_session=db_session, user_name=user_name, raise_exception_if_exists=True)

    try:
        # Create a new user
        await db_session.execute(
            """
            INSERT INTO users (user_id, user_name, user_email, primary_phone, display_name,
            password_hash, user_details, is_active, permissions_template, permissions, organization_id, ui_info)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            str(uuid.uuid4()),
            user_name,
            user_email,
            primary_phone,
            display_name,
            password_hash,
            orjson.dumps(user_details).decode("utf-8"),
            is_active,
            orjson.dumps(permissions_template).decode("utf-8"),
            permissions,
            organization_id,
            "{}"  # Initialize ui_info as an empty dictionary
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new user: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def check_user_name_exists(db_session: PgSession, user_name: str) -> bool:
    """
    Check if the user name already exists in the database
    Returns True if the user name exists, False otherwise
    """
    try:
        row = await db_session.fetchrow(
            "SELECT 1 FROM users WHERE user_name = $1", user_name
        )
        return row is not None

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check user name: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_user(db_session: PgSession, user_id: str, organization_id: str) -> None:
    """
    Delete a user from the database
    """
    try:
        # Delete the user
        await db_session.execute(
            """
            DELETE FROM users WHERE user_id = $1 AND organization_id = $2
            """,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete user: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def is_parent_user(db_session: PgSession, user_name: str, hierarchy_path: str) -> bool:
    """
    Check if the user is a parent user
    Returns True if the user is a parent user, False if its the last user in the hierarchy
    """
    # Check if the user exists
    await _raise_check_user_name_exists(db_session=db_session, user_name=user_name, raise_exception_if_exists=False)

    try:
        # Check if the user is a parent user
        row = await db_session.fetchrow(
            """
            SELECT 1 FROM users WHERE hierarchy_path LIKE $1 LIMIT 1
            """,
            hierarchy_path + "/%"
        )
        return row is not None

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check if user is a parent: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_hierarchy_users_list(db_session: PgSession, organization_id: str, page: int, page_size: int) -> tuple[list[dict], int]:
    """
    Get a list of users in the hierarchy
    """
    try:
        # Fetch users in the hierarchy
        rows = await db_session.fetch(
            """
            SELECT user_id, user_name, display_name, is_active, is_totp_2fa_active, created_at
            FROM users WHERE organization_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            page_size,
            (page - 1) * page_size
        )

        # Fetch total count of users in the hierarchy
        total_count_row = await db_session.fetchrow(
            """
            SELECT COUNT(*) FROM users WHERE organization_id = $1
            """,
            organization_id
        )
        if not total_count_row:
            raise All_Exceptions(
                message="Failed to fetch total count of users",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        return [
            {
                "user_id": str(row["user_id"]),
                "user_name": row["user_name"],
                "display_name": row["display_name"],
                "is_active": row["is_active"],
                "is_totp_2fa_active": row["is_totp_2fa_active"],
                "created_at": row["created_at"].isoformat()
            }
            for row in rows
        ], int(total_count_row["count"])

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch hierarchy users list: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_user_password(db_session: PgSession, organization_id: str, user_id: str, new_password_hash: str) -> None:
    """
    Update the user's password
    """
    try:
        # Update the user's password
        await db_session.execute(
            """
            UPDATE users SET password_hash = $1
            WHERE user_id = $2 AND organization_id = $3
            """,
            new_password_hash,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update user password: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def replace_user_permissions_template(db_session: PgSession, organization_id: str, user_id: str, new_permissions_template: dict) -> None:
    """
    Replace the user's permissions template
    """
    try:
        # Update the user's permissions template
        await db_session.execute(
            """
            UPDATE users SET permissions_template = $1
            WHERE user_id = $2 AND organization_id = $3
            """,
            orjson.dumps(new_permissions_template).decode("utf-8"),
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to replace user permissions template: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def replace_user_permissions(db_session: PgSession, organization_id: str, user_id: str, new_permissions: list[str]) -> None:
    """
    Replace the user's permissions
    """
    try:
        # Update the user's permissions
        await db_session.execute(
            """
            UPDATE users SET permissions = $1
            WHERE user_id = $2 AND organization_id = $3
            """,
            new_permissions,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to replace user permissions: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def replace_user_details(
    db_session: PgSession,
    organization_id: str,
    user_id: str,
    user_name: str,
    new_user_details: dict,
    primary_phone: str,
    display_name: str,
    is_active: bool,
    user_email: str,
    is_mail_updated: bool,
    is_phone_updated: bool
) -> None:
    """
    Replace the user's details
    """
    try:
        # Get is_email_verified and is_phone_verified status
        status_row = await db_session.fetchrow(
            """
            SELECT is_email_verified, is_phone_verified FROM users
            WHERE user_id = $1 AND organization_id = $2
            """,
            user_id,
            organization_id
        )
        if not status_row:
            raise All_Exceptions(
                message="User not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get existing verification statuses
        is_email_verified = status_row["is_email_verified"]
        is_phone_verified = status_row["is_phone_verified"]

        # Update the user's details
        await db_session.execute(
            """
            UPDATE users SET user_details = $1, primary_phone = $2, display_name = $3, user_email = $4, user_name = $5,
            is_active = $6, is_email_verified = $7, is_phone_verified = $8
            WHERE user_id = $9 AND organization_id = $10
            """,
            orjson.dumps(new_user_details).decode("utf-8"),
            primary_phone,
            display_name,
            user_email,
            user_name,
            is_active,

            # Logic: If the email/phone is updated, set is_email_verified/is_phone_verified to False Else keep the existing value
            is_email_verified if not is_mail_updated else False,
            is_phone_verified if not is_phone_updated else False,

            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to replace user details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def enable_two_factor_totp(db_session: PgSession, user_id: str, organization_id: str) -> None:
    """
    Enable two-factor TOTP for the user
    """
    try:
        # Update the user's TOTP status
        await db_session.execute(
            """
            UPDATE users SET is_totp_2fa_active = TRUE
            WHERE user_id = $1 AND organization_id = $2
            """,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to enable two-factor TOTP: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def disable_two_factor_totp(db_session: PgSession, user_id: str, organization_id: str) -> None:
    """
    Disable two-factor TOTP for the user
    """
    try:
        # Update the user's TOTP status
        await db_session.execute(
            """
            UPDATE users SET is_totp_2fa_active = FALSE
            WHERE user_id = $1 AND organization_id = $2
            """,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to disable two-factor TOTP: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_user_template_permissions(db_session: PgSession, user_id: str, organization_id: str) -> dict:
    """
    Get the user's permissions template from the database along with the permissions
    """
    try:
        row = await db_session.fetchrow(
            """
            SELECT permissions_template, permissions FROM users WHERE user_id = $1 AND organization_id = $2
            """,
            user_id,
            organization_id
        )
        if row:
            return {
                "permissions_template": orjson.loads(row["permissions_template"]),
                "permissions": list(set(row["permissions"]))
            }

        else:
            raise All_Exceptions(
                message="User not found or does not have a permissions template",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch user permissions template: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def set_email_verified(db_session: PgSession, user_id: str, organization_id: str, is_verified: bool = True) -> None:
    """
    Set the user's email as verified in the database
    """
    try:
        # Update the user's email verification status
        await db_session.execute(
            """
            UPDATE users SET is_email_verified = $1
            WHERE user_id = $2 AND organization_id = $3
            """,
            is_verified,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to set email verified status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def manage_email_2fa(db_session: PgSession, user_id: str, organization_id: str, enable: bool) -> None:
    """
    Enable or disable email 2FA for the user
    """
    try:
        # Update the user's email 2FA status
        await db_session.execute(
            """
            UPDATE users SET is_email_2fa_active = $1
            WHERE user_id = $2 AND organization_id = $3 And is_email_verified = TRUE
            """,
            enable,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to manage email 2FA: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def set_phone_verified(db_session: PgSession, user_id: str, organization_id: str, is_verified: bool = True) -> None:
    """
    Set the user's phone number as verified in the database
    """
    try:
        # Update the user's phone verification status
        await db_session.execute(
            """
            UPDATE users SET is_phone_verified = $1
            WHERE user_id = $2 AND organization_id = $3
            """,
            is_verified,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to set phone verified status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def manage_sms_2fa(db_session: PgSession, user_id: str, organization_id: str, enable: bool) -> None:
    """
    Enable or disable SMS 2FA for the user
    """
    try:
        # Update the user's SMS 2FA status
        await db_session.execute(
            """
            UPDATE users SET is_sms_2fa_active = $1
            WHERE user_id = $2 AND organization_id = $3 And is_phone_verified = TRUE
            """,
            enable,
            user_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to manage SMS 2FA: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def replace_ui_info(db_session: PgSession, user_id: str, ui_info: dict) -> None:
    """
    Replace the user's UI info
    """
    try:
        # Update the user's UI info
        await db_session.execute(
            """
            UPDATE users SET ui_info = $1
            WHERE user_id = $2
            """,
            orjson.dumps(ui_info).decode("utf-8"),
            user_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to replace user UI info: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_ui_info(db_session: PgSession, user_id: str) -> dict:
    """
    Get the user's UI info from the database
    """
    try:
        row = await db_session.fetchrow(
            """
            SELECT ui_info FROM users WHERE user_id = $1
            """,
            user_id
        )
        if row:
            return orjson.loads(row["ui_info"])

        else:
            raise All_Exceptions(
                message="User not found or does not have UI info",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch user UI info: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_email_client_sessions(db_session: PgSession, domain_name: str, page: int, size: int) -> dict:
    """
    Get the email client sessions under one domain
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM mailbox_sessions WHERE domain_name = $1
            """,
            domain_name
        )
        if total_count is None:
            raise All_Exceptions(
                message="Failed to fetch total count of email client sessions",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        email_client_sessions = await db_session.fetch(
            """
            SELECT origin_ip, attempted_by, geo_ip_location,
                   is_active, attempted_at, session_expires_at
            FROM mailbox_sessions
            WHERE domain_name = $1
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            size,
            (page - 1) * size
        )
        return {
            "current_page": page,
            "page_size": size,
            "has_more": (page * size) < total_count,
            "total_count": total_count,
            "total_pages": (total_count // size) + (1 if total_count % size > 0 else 0),
            "data": [
                {
                    "origin_ip": str(session["origin_ip"]),
                    "attempted_by": session["attempted_by"],
                    "geo_ip_location": orjson.loads(session["geo_ip_location"]),
                    "is_active": session["is_active"],
                    "attempted_at": session["attempted_at"].isoformat(),
                    "session_expires_at": session["session_expires_at"].isoformat()
                }
                for session in email_client_sessions
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch email client sessions: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def switch_email_client_session(db_session: PgSession, origin_ip: str, attempted_by: str, domain_name: str) -> None:
    """
    Switch an email client session
    """
    try:
        await db_session.execute(
            """
            UPDATE mailbox_sessions SET is_active = NOT is_active
            WHERE origin_ip = $1 AND attempted_by = $2 AND domain_name = $3
            """,
            origin_ip,
            attempted_by,
            domain_name
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to switch email client session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_email_client_session(db_session: PgSession, origin_ip: str, attempted_by: str, domain_name: str) -> None:
    """
    Delete an email client session
    """
    try:
        await db_session.execute(
            """
            DELETE FROM mailbox_sessions
            WHERE origin_ip = $1 AND attempted_by = $2 AND domain_name = $3
            """,
            origin_ip,
            attempted_by,
            domain_name
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete email client session: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_maintenance_data(db_session: PgSession, is_active: bool) -> list[dict]:
    """
    Get maintenance data from the database
    """
    try:
        rows = await db_session.fetch(
            """
            SELECT maintenance_id, title, description, affected, severity, type, start_time, end_time
            FROM maintenance_alerts
            WHERE is_active = $1
            """,
            is_active
        )
        return [
            {
                "maintenance_id": int(row["maintenance_id"]),
                "title": row["title"],
                "description": row["description"],
                "affected": list(row["affected"]),
                "severity": str(row["severity"]),
                "type": row["type"],
                "start_time": row["start_time"].isoformat(),
                "end_time": row["end_time"].isoformat()
            }
            for row in rows
        ]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch maintenance data: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_maintenance_entry(db_session: PgSession, maintenance_id: int) -> None:
    """
    Delete a maintenance entry from the database
    """
    try:
        await db_session.execute(
            """
            DELETE FROM maintenance_alerts
            WHERE maintenance_id = $1
            """,
            maintenance_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete maintenance entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_maintenance_entry(
    db_session: PgSession,
    maintenance_id: int,
    title: str,
    description: str,
    affected: list[str],
    severity: str,
    type: str,
    is_active: bool,
    start_time: str,
    end_time: str
) -> None:
    """
    Update a maintenance entry in the database
    """
    try:
        await db_session.execute(
            """
            UPDATE maintenance_alerts
            SET title = $1,
                description = $2,
                affected = $3,
                severity = $4,
                type = $5,
                start_time = $6,
                end_time = $7,
                is_active = $8
            WHERE maintenance_id = $9
            """,
            title,
            description,
            affected,
            severity,
            type,
            datetime.fromisoformat(start_time),
            datetime.fromisoformat(end_time),
            is_active,
            maintenance_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update maintenance entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_maintenance_entry(
    db_session: PgSession,
    title: str,
    description: str,
    affected: list[str],
    severity: str,
    type: str,
    is_active: bool,
    start_time: str,
    end_time: str
) -> None:
    """
    Create a new maintenance entry in the database
    """
    try:
        await db_session.execute(
            """
            INSERT INTO maintenance_alerts (title, description, affected, severity, type, start_time, end_time, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            title,
            description,
            affected,
            severity,
            type,
            datetime.fromisoformat(start_time),
            datetime.fromisoformat(end_time),
            is_active
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create maintenance entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_new_support_ticket(
    db_session: PgSession,
    organization_id: str,
    ticket_title: str,
    ticket_description: str,
    details: dict,
    created_by: str
) -> None:
    """
    Create a new support ticket in the database
    """
    try:
        await db_session.execute(
            """
            INSERT INTO support_tickets (organization_id, ticket_title, ticket_description, details, created_by)
            VALUES ($1, $2, $3, $4, $5)
            """,
            organization_id,
            ticket_title,
            ticket_description,
            orjson.dumps(details).decode("utf-8"),
            created_by
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new support ticket: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def add_follow_up_to_ticket(
    db_session: PgSession,
    ticket_id: int,
    organization_id: str,
    follow_up_text: str,
    details: dict,
    created_by: str
) -> None:
    """
    Add a follow-up to a support ticket in the database
    """
    try:
        # Make sure the ticket exists and belongs to the organization
        row = await db_session.fetchrow(
            """
            SELECT 1 FROM support_tickets
            WHERE
                ticket_id = $1 AND
                organization_id = $2 AND
                ticket_status != 'RESOLVED'
            """,
            ticket_id,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message="Support ticket not found or already resolved",
                status_code=status.HTTP_404_NOT_FOUND
            )

        await db_session.execute(
            """
            INSERT INTO ticket_follow_ups (ticket_id, message, details, created_by)
            VALUES ($1, $2, $3, $4)
            """,
            ticket_id,
            follow_up_text,
            orjson.dumps(details).decode("utf-8"),
            created_by
        )

        # Update the ticket's updated_at timestamp
        await db_session.execute(
            """
            UPDATE support_tickets
            SET updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = $1
            """,
            ticket_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to add follow-up to support ticket: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def fetch_all_support_tickets(db_session: PgSession, organization_id: str, page: int, page_size: int, query='') -> dict:
    """
    Fetch all support tickets for an organization with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM support_tickets
            WHERE organization_id = $1 AND ticket_title ILIKE $2
            """,
            organization_id,
            f"%{query}%"
        )
        if total_count is None:
            raise All_Exceptions(
                message="Failed to fetch total count of support tickets",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        tickets = await db_session.fetch(
            """
            SELECT ticket_id, ticket_title, ticket_description, details, ticket_status, created_by, created_at, updated_at
            FROM support_tickets
            WHERE organization_id = $1 AND ticket_title ILIKE $2
            ORDER BY updated_at DESC
            LIMIT $3 OFFSET $4
            """,
            organization_id,
            f"%{query}%",
            page_size,
            (page - 1) * page_size
        )
        return {
            "current_page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total_count,
            "total_count": total_count,
            "total_pages": (total_count // page_size) + (1 if total_count % page_size > 0 else 0),
            "data": [
                {
                    "ticket_id": int(ticket["ticket_id"]),
                    "ticket_title": ticket["ticket_title"],
                    "ticket_description": ticket["ticket_description"],
                    "details": orjson.loads(ticket["details"]),
                    "ticket_status": ticket["ticket_status"],
                    "created_by": ticket["created_by"],
                    "created_at": ticket["created_at"].isoformat(),
                    "updated_at": ticket["updated_at"].isoformat()
                }
                for ticket in tickets
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch support tickets: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def fetch_ticket_follow_ups(db_session: PgSession, organization_id: str, ticket_id: int, page: int, page_size: int) -> dict:
    """
    Fetch all follow-ups for a support ticket with pagination
    """
    try:
        # Check if the ticket exists and of the organization
        row = await db_session.fetchrow(
            """
            SELECT 1 FROM support_tickets
            WHERE ticket_id = $1 AND organization_id = $2
            """,
            ticket_id,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message="Support ticket not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM ticket_follow_ups
            WHERE ticket_id = $1
            """,
            ticket_id
        )
        if total_count is None:
            raise All_Exceptions(
                message="Failed to fetch total count of ticket follow-ups",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        follow_ups = await db_session.fetch(
            """
            SELECT follow_up_id, message, details, created_by, created_at
            FROM ticket_follow_ups
            WHERE ticket_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            ticket_id,
            page_size,
            (page - 1) * page_size
        )
        return {
            "current_page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total_count,
            "total_count": total_count,
            "total_pages": (total_count // page_size) + (1 if total_count % page_size > 0 else 0),
            "data": [
                {
                    "follow_up_id": int(follow_up["follow_up_id"]),
                    "message": follow_up["message"],
                    "details": orjson.loads(follow_up["details"]),
                    "created_by": follow_up["created_by"],
                    "created_at": follow_up["created_at"].isoformat()
                }
                for follow_up in follow_ups
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch ticket follow-ups: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def admin_fetch_all_support_tickets(
    db_session: PgSession,
    organization_id: str | None,
    ticket_status: str | None,
    ticket_id: int | None,
    title_search: str | None,
    created_by: str | None,
    assigned_to: str | None,
    page: int,
    page_size: int
) -> dict:
    """
    Admin fetch all support tickets with advanced filtering and pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM support_tickets
            WHERE
                ($1::uuid IS NULL OR organization_id = $1::uuid)
                AND ($2::ticket_status_enum IS NULL OR ticket_status = $2::ticket_status_enum)
                AND ($3::text IS NULL OR ticket_title ILIKE $3)
                AND ($4::text IS NULL OR created_by = $4)
                AND ($5::text IS NULL OR $5 = ANY(assigned_to))
                AND ($6::int IS NULL OR ticket_id = $6)
            """,
            organization_id if organization_id else None,
            ticket_status if ticket_status else None,
            f"%{title_search}%" if title_search else None,
            created_by if created_by else None,
            assigned_to if assigned_to else None,
            ticket_id if ticket_id else None
        )
        if total_count is None:
            raise All_Exceptions(
                message="Failed to fetch total count of support tickets",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        tickets = await db_session.fetch(
            """
            SELECT
                ticket_id, organization_id, ticket_title, ticket_description, details,
                ticket_status, created_by, assigned_to, created_at, updated_at
            FROM support_tickets
            WHERE
                ($1::uuid IS NULL OR organization_id = $1::uuid)
                AND ($2::ticket_status_enum IS NULL OR ticket_status = $2::ticket_status_enum)
                AND ($3::text IS NULL OR ticket_title ILIKE $3)
                AND ($4::text IS NULL OR created_by = $4)
                AND ($5::text IS NULL OR $5 = ANY(assigned_to))
                AND ($6::int IS NULL OR ticket_id = $6)
            ORDER BY updated_at DESC
            LIMIT $7 OFFSET $8
            """,
            organization_id if organization_id else None,
            ticket_status if ticket_status else None,
            f"%{title_search}%" if title_search else None,
            created_by if created_by else None,
            assigned_to if assigned_to else None,
            ticket_id if ticket_id else None,
            page_size,
            (page - 1) * page_size,
        )

        return {
            "current_page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total_count,
            "total_count": total_count,
            "total_pages": (total_count // page_size) + (1 if total_count % page_size > 0 else 0),
            "data": [
                {
                    "ticket_id": int(ticket["ticket_id"]),
                    "organization_id": str(ticket["organization_id"]),
                    "ticket_title": ticket["ticket_title"],
                    "ticket_description": ticket["ticket_description"],
                    "details": orjson.loads(ticket["details"]),
                    "ticket_status": ticket["ticket_status"],
                    "created_by": ticket["created_by"],
                    "assigned_to": ticket["assigned_to"],
                    "created_at": ticket["created_at"].isoformat(),
                    "updated_at": ticket["updated_at"].isoformat()
                }
                for ticket in tickets
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch support tickets: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def admin_update_ticket_info(
    db_session: PgSession,
    ticket_id: int,
    organization_id: str,
    ticket_status: str,
    assigned_to: list[str]
) -> None:
    """
    Admin update support ticket information
    """
    try:
        await db_session.execute(
            """
            UPDATE support_tickets
            SET ticket_status = $1,
                assigned_to = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = $3 AND organization_id = $4
            """,
            ticket_status,
            assigned_to,
            ticket_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update support ticket info: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_support_ticket(
    db_session: PgSession,
    ticket_id: int,
    organization_id: str
) -> None:
    """
    Delete a support ticket from the database
    """
    try:
        await db_session.execute(
            """
            DELETE FROM support_tickets
            WHERE ticket_id = $1 AND organization_id = $2
            """,
            ticket_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete support ticket: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def fetch_support_ticket_by_id(db_session: PgSession, ticket_id: int, organization_id: str) -> dict:
    """
    Fetch a support ticket by its ID
    """
    try:
        row = await db_session.fetchrow(
            """
            SELECT ticket_id, ticket_title, ticket_description,
            details, ticket_status, created_by, created_at, updated_at
            FROM support_tickets
            WHERE ticket_id = $1 AND organization_id = $2
            """,
            ticket_id,
            organization_id
        )
        if row:
            return {
                "ticket_id": int(row["ticket_id"]),
                "ticket_title": row["ticket_title"],
                "ticket_description": row["ticket_description"],
                "details": orjson.loads(row["details"]),
                "ticket_status": row["ticket_status"],
                "created_by": row["created_by"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat()
            }

        else:
            raise All_Exceptions(
                message="Support ticket not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch support ticket by ID: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_all_chat_users_under_domain(db_session: PgSession, domain_name: str, page: int, page_size: int) -> dict:
    """
    List all users who have used the chat feature under a specific domain with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM chat_users WHERE domain_name = $1
            """,
            domain_name
        )
        if total_count is None:
            raise All_Exceptions(
                message="Failed to fetch total count of chat users",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        users = await db_session.fetch(
            """
            SELECT email, is_enabled, last_active_at FROM chat_users
            WHERE domain_name = $1
            ORDER BY last_active_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            page_size,
            (page - 1) * page_size
        )
        return {
            "current_page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total_count,
            "total_count": total_count,
            "total_pages": (total_count // page_size) + (1 if total_count % page_size > 0 else 0),
            "data": [
                {
                    "email": user["email"],
                    "is_enabled": user["is_enabled"],
                    "last_active_at": user["last_active_at"].isoformat()
                }
                for user in users
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list chat users: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def toggle_chat_user_status(db_session: PgSession, domain_name: str, email: str) -> None:
    """
    Toggle the status (enabled/disabled) of a chat user for a specific domain
    """
    try:
        await db_session.execute(
            """
            UPDATE chat_users
            SET is_enabled = NOT is_enabled
            WHERE domain_name = $1 AND email = $2
            """,
            domain_name,
            email
        )
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to toggle chat user status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_chat_user(db_session: PgSession, domain_name: str, email: str) -> None:
    """
    Delete a chat user for a specific domain
    """
    try:
        await db_session.execute(
            """
            DELETE FROM chat_users
            WHERE domain_name = $1 AND email = $2
            """,
            domain_name,
            email
        )
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete chat user: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_chat_user(db_session: PgSession, domain_name: str, email: str) -> None:
    """
    Create a new chat user for a specific domain
    """
    try:
        await db_session.execute(
            """
            INSERT INTO chat_users (domain_name, email, is_enabled, last_active_at)
            VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
            """,
            domain_name,
            email
        )
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create chat user: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_all_files_users_under_domain(db_session: PgSession, domain_name: str, page: int, page_size: int) -> dict:
    """
    List all users who have used the file management feature under a specific domain with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM file_users WHERE domain_name = $1
            """,
            domain_name
        )
        if total_count is None:
            raise All_Exceptions(
                message="Failed to fetch total count of file users",
                status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        users = await db_session.fetch(
            """
            SELECT email, is_enabled, quota_allocated, quota_utilized, last_active_at FROM file_users
            WHERE domain_name = $1
            ORDER BY last_active_at DESC
            LIMIT $2 OFFSET $3
            """,
            domain_name,
            page_size,
            (page - 1) * page_size
        )
        return {
            "current_page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total_count,
            "total_count": total_count,
            "total_pages": (total_count // page_size) + (1 if total_count % page_size > 0 else 0),
            "data": [
                {
                    "email": user["email"],
                    "is_enabled": user["is_enabled"],
                    "quota_allocated": float(user["quota_allocated"]),
                    "quota_utilized": float(user["quota_utilized"]),
                    "last_active_at": user["last_active_at"].isoformat()
                }
                for user in users
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list file users: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def toggle_file_user_status(db_session: PgSession, domain_name: str, email: str) -> None:
    """
    Toggle the status (enabled/disabled) of a file user for a specific domain
    """
    try:
        await db_session.execute(
            """
            UPDATE file_users
            SET is_enabled = NOT is_enabled
            WHERE domain_name = $1 AND email = $2
            """,
            domain_name,
            email
        )
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to toggle file user status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_file_user(db_session: PgSession, domain_name: str, email: str, organization_id: str) -> None:
    """
    Delete a file user for a specific domain
    """
    row = await db_session.fetchrow(
        """
        SELECT quota_allocated FROM file_users WHERE domain_name = $1 AND email = $2
        """,
        domain_name,
        email
    )
    if not row:
        raise All_Exceptions(
            message="File user not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    quota_allocated = row["quota_allocated"]

    try:
        await db_session.execute(
            """
            DELETE FROM file_users
            WHERE domain_name = $1 AND email = $2
            """,
            domain_name,
            email
        )

        # Update the organization's used quota
        await db_session.execute(
            """
            UPDATE organizations SET quota_utilized = quota_utilized - $1 WHERE organization_id = $2
            """,
            quota_allocated,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete file user: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_file_user(
    db_session: PgSession,
    domain_name: str,
    organization_id: str,
    email: str,
    quota_allocated: float,
    is_enabled: bool
) -> None:
    """
    Create a new file user for a specific domain
    """
    # Make sure there is enough quota in the organization to allocate to this user
    # Check the space for the organization
    await validate_organization_quota(
        db_session=db_session,
        organization_id=organization_id,
        required_storage_quota=quota_allocated,
        required_email_identities=-1
    )

    try:
        await db_session.execute(
            """
            INSERT INTO file_users (domain_name, email, is_enabled, quota_allocated, quota_utilized)
            VALUES ($1, $2, $3, $4, 0.0)
            """,
            domain_name,
            email,
            is_enabled,
            quota_allocated
        )

        # Update the organization's used quota
        await db_session.execute(
            """
            UPDATE organizations SET quota_utilized = quota_utilized + $1 WHERE organization_id = $2
            """,
            quota_allocated,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create file user: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_file_user_quota(
    db_session: PgSession,
    domain_name: str,
    organization_id: str,
    email: str,
    new_quota_allocated: float
) -> None:
    """
    Update the quota allocated to a file user for a specific domain
    """
    # Fetch the current quota allocated to the user
    row = await db_session.fetchrow(
        """
        SELECT quota_allocated, quota_utilized FROM file_users WHERE domain_name = $1 AND email = $2
        """,
        domain_name,
        email
    )
    if not row:
        raise All_Exceptions(
            message="File user not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Calculate the difference between the new quota and the current quota
    quota_difference = new_quota_allocated - row["quota_allocated"]
    
    # Check if its less than or equal to already utilized quota (if yes, then we cannot reduce the quota)
    if new_quota_allocated <= row["quota_utilized"]:
        raise All_Exceptions(
            message="New quota cannot be less than or equal to the already utilized quota",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Make sure there is enough quota in the organization to allocate to this user
    await validate_organization_quota(
        db_session=db_session,
        organization_id=organization_id,
        required_storage_quota=quota_difference,
        required_email_identities=-1
    )

    try:
        await db_session.execute(
            """
            UPDATE file_users SET quota_allocated = $1 WHERE domain_name = $2 AND email = $3
            """,
            new_quota_allocated,
            domain_name,
            email
        )

        # Update the organization's used quota
        await db_session.execute(
            """
            UPDATE organizations SET quota_utilized = quota_utilized + $1 WHERE organization_id = $2
            """,
            quota_difference,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update file user quota: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
