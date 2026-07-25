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


from src.utils.base.libraries import asyncpg, TypeAlias, status, uuid
from src.utils.models import All_Exceptions


PgSession: TypeAlias = asyncpg.Connection


# CREATE TABLE backup_codes (
#     code_id UUID PRIMARY KEY,
#     user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
#     code VARCHAR(6) NOT NULL,  -- e.g., 'ABC123'
#     is_used BOOLEAN DEFAULT FALSE NOT NULL,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     UNIQUE (user_id, code)
# );


async def replace_backup_codes_for_user(db_session: PgSession, user_id: str, codes: list[str]) -> None:
    """
    Replace all backup codes for a user with new codes
    """
    try:
        # Delete existing backup codes for the user
        await db_session.execute(
            """
            DELETE FROM backup_codes WHERE user_id = $1
            """,
            user_id
        )

        # Insert new backup codes into the database
        for code in codes:
            await db_session.execute(
                """
                INSERT INTO backup_codes (code_id, user_id, code)
                VALUES ($1, $2, $3)
                """,
                str(uuid.uuid4()),
                user_id,
                code
            )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to replace backup codes: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def use_one_backup_code(db_session: PgSession, user_id: str, code: str) -> bool:
    """
    Mark a backup code as used
    """
    try:
        result = await db_session.fetchrow(
            """
            SELECT code FROM backup_codes
            WHERE user_id = $1 AND code = $2 AND is_used = FALSE
            """,
            user_id,
            code
        )

        if not result:
            return False

        update_result = await db_session.execute(
            """
            UPDATE backup_codes
            SET is_used = TRUE
            WHERE user_id = $1 AND code = $2
            """,
            user_id,
            code
        )

        return update_result == "UPDATE 1"

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to use backup code: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def check_backup_codes_for_user(db_session: PgSession, user_id: str) -> tuple[bool, int]:
    """
    Check if backup codes are available for a user and how many are left/active
    """
    try:
        result = await db_session.fetchrow(
            """
            SELECT COUNT(*) AS count FROM backup_codes
            WHERE user_id = $1 AND is_used = FALSE
            """,
            user_id
        )

        if not result:
            return False, 0

        return True, result["count"]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check backup codes: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
