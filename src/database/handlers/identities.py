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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, status, uuid, orjson, os, hashlib, base64, bcrypt
from src.utils.models import All_Exceptions


PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


# -- E-Mail ID's - Users
# CREATE TABLE email_identities (
#     email VARCHAR(254) PRIMARY KEY,
#     domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

#     first_name TEXT NOT NULL,
#     last_name TEXT,
#     primary_phone VARCHAR(20) NOT NULL, -- Used for 2FA/recovery/notifications
#     secondary_email VARCHAR(254),   -- Used for 2FA/recovery/notifications

#     password_hash_ssha1 TEXT NOT NULL,
#     password_bcrypt TEXT NOT NULL,

#     is_app_2fa_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Is app-based 2FA enabled
#     is_sms_2fa_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Is SMS-based 2FA enabled
#     is_email_2fa_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Is Email-based 2FA enabled

#     restriction_policy_id UUID REFERENCES restriction_policies(policy_id) ON DELETE SET NULL,
#     department_id UUID REFERENCES departments(department_id) ON DELETE SET NULL,

#     is_password_expired BOOLEAN DEFAULT FALSE NOT NULL,
#     is_enabled BOOLEAN DEFAULT TRUE NOT NULL,

#     password_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

#     created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
# );


def _generate_password_hashs(raw_password: bytes) -> tuple[str, str]:
    """
    Generate a password hash and salt
    Returns a tuple of (password_hash_ssha1, password_hash_md5_crypt)
    """
    salt = os.urandom(4)
    sha1 = hashlib.sha1(raw_password)
    sha1.update(salt)
    digest = sha1.digest() + salt

    return (
        f"{{SSHA}}{base64.b64encode(digest).decode('utf-8')}",  # SSHA hash
        bcrypt.hashpw(raw_password, bcrypt.gensalt()).decode('utf-8')  # Bcrypt hash
    )


async def get_identity_info(db_session: PgSession, email: str) -> dict:
    """
    Get details of a specific email identity
    """
    try:
        # Fetch the email identity details from the database
        result = await db_session.fetchrow(
            """
            SELECT email, domain_name, first_name, last_name, primary_phone, secondary_email,
                   is_app_2fa_enabled, is_sms_2fa_enabled, is_email_2fa_enabled,
                   is_password_expired, is_enabled, password_updated_at, department_id,
                   created_at, updated_at, restriction_policy_id
            FROM email_identities
            WHERE email = $1
            """,
            email
        )
        if result is None:
            raise All_Exceptions(
                message="Email identity not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Convert the result to a dictionary
        return {
            "email": result["email"],
            "domain_name": result["domain_name"],
            "first_name": result["first_name"],
            "last_name": result["last_name"],
            "primary_phone": result["primary_phone"],
            "secondary_email": result["secondary_email"],
            "is_app_2fa_enabled": result["is_app_2fa_enabled"],
            "is_sms_2fa_enabled": result["is_sms_2fa_enabled"],
            "is_email_2fa_enabled": result["is_email_2fa_enabled"],
            "is_password_expired": result["is_password_expired"],
            "is_enabled": result["is_enabled"],
            "restriction_policy_id": str(result["restriction_policy_id"]) if result["restriction_policy_id"] else None,
            "department_id": str(result["department_id"]) if result["department_id"] else None,
            "password_updated_at": result["password_updated_at"].isoformat(),
            "created_at": result["created_at"].isoformat(),
            "updated_at": result["updated_at"].isoformat()
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch email identity details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_new_identity_entry(
    db_session: PgSession,
    email: str,
    domain_name: str,
    first_name: str,
    last_name: str,
    primary_phone: str,
    secondary_email: str,
    base64_encoded_password: str,
    is_app_2fa_enabled: bool,
    is_sms_2fa_enabled: bool,
    is_email_2fa_enabled: bool,
    restriction_policy_id: str | None,
    department_id: str | None,
    is_enabled: bool
) -> None:
    """
    Create a new email identity entry in the database
    """
    try:
        # Insert the new email identity into the database
        await db_session.execute(
            """
            INSERT INTO email_identities (
                email, domain_name, first_name, last_name, primary_phone, secondary_email,
                password_hash_ssha1, password_bcrypt,
                is_app_2fa_enabled, is_sms_2fa_enabled, is_email_2fa_enabled,
                restriction_policy_id, department_id, is_enabled
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            email,
            domain_name,
            first_name,
            last_name,
            primary_phone,
            secondary_email,
            *_generate_password_hashs(base64.b64decode(base64_encoded_password)),
            is_app_2fa_enabled,
            is_sms_2fa_enabled,
            is_email_2fa_enabled,
            restriction_policy_id,
            department_id,
            is_enabled
        )

        # After creating the email identity, we need to update the utilized_email_identities count for the organization
        await db_session.execute(
            """
            UPDATE organizations
            SET utilized_email_identities = utilized_email_identities + 1
            WHERE organization_id = (
                SELECT managed_by FROM domains WHERE domain_name = $1
            )
            """,
            domain_name
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new email identity entry: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def list_identities_under_domain(
    db_session: PgSession,
    domain_name: str,
    search_query: str,
    page: int,
    page_size: int
) -> dict:
    """
    List all email identities under a domain with pagination
    """
    try:
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM email_identities
            WHERE domain_name = $1 AND email ILIKE $2
            """,
            domain_name,
            f"%{search_query}%"
        )
        if not total_count or total_count == 0:
            return {"total_count": 0, "identities": []}

        offset = (page - 1) * page_size
        identities = await db_session.fetch(
            """
            SELECT
                ei.email,
                ei.domain_name,
                ei.first_name,
                ei.last_name,
                ei.primary_phone,
                ei.secondary_email,

                ei.is_app_2fa_enabled,
                ei.is_sms_2fa_enabled,
                ei.is_email_2fa_enabled,

                ei.is_password_expired,
                ei.is_enabled,

                ei.password_updated_at,
                ei.department_id,
                ei.created_at,
                ei.updated_at,
                ei.restriction_policy_id,

                -- Chat
                (cu.email IS NOT NULL) AS is_chat_user_present,
                COALESCE(cu.is_enabled, FALSE) AS is_chat_user_enabled,

                -- Mailbox
                (mb.email IS NOT NULL) AS is_mailbox_present,
                COALESCE(mb.is_enabled, FALSE) AS is_mailbox_enabled,

                -- File
                (fu.email IS NOT NULL) AS is_file_user_present,
                COALESCE(fu.is_enabled, FALSE) AS is_file_user_enabled

            FROM email_identities ei

            LEFT JOIN chat_users cu
                ON cu.email = ei.email

            LEFT JOIN file_users fu
                ON fu.email = ei.email

            LEFT JOIN mailboxes mb
                ON mb.email = ei.email

            WHERE
                ei.domain_name = $1
                AND ei.email ILIKE $2

            ORDER BY ei.updated_at DESC
            LIMIT $3 OFFSET $4;
            """,
            domain_name,
            f"%{search_query}%",
            page_size,
            offset
        )

        # Convert the result to a list of dictionaries
        identity_list = [
            {
                "email": identity["email"],
                "domain_name": identity["domain_name"],
                "first_name": identity["first_name"],
                "last_name": identity["last_name"],
                "primary_phone": identity["primary_phone"],
                "secondary_email": identity["secondary_email"],
                "is_app_2fa_enabled": identity["is_app_2fa_enabled"],
                "is_sms_2fa_enabled": identity["is_sms_2fa_enabled"],
                "is_email_2fa_enabled": identity["is_email_2fa_enabled"],
                "is_password_expired": identity["is_password_expired"],
                "is_enabled": identity["is_enabled"],
                "restriction_policy_id": str(identity["restriction_policy_id"]) if identity["restriction_policy_id"] else None,
                "department_id": str(identity["department_id"]) if identity["department_id"] else None,
                "is_chat_user_present": identity["is_chat_user_present"],
                "is_chat_user_enabled": identity["is_chat_user_enabled"],
                "is_mailbox_present": identity["is_mailbox_present"],
                "is_mailbox_enabled": identity["is_mailbox_enabled"],
                "is_file_user_present": identity["is_file_user_present"],
                "is_file_user_enabled": identity["is_file_user_enabled"],
                "password_updated_at": identity["password_updated_at"].isoformat(),
                "created_at": identity["created_at"].isoformat(),
                "updated_at": identity["updated_at"].isoformat()
            }
            for identity in identities
        ]

        return {"total_count": total_count, "identities": identity_list}
    
    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to list email identities for domain {domain_name}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_identity(
    db_session: PgSession,
    email: str
) -> None:
    """
    Delete a specific email identity from the database
    """
    # Check if any of the 3 Services are present (E-Mail, Chat, Files)
    entry_status = await db_session.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM mailboxes WHERE email = $1
        ) OR EXISTS (
            SELECT 1 FROM chat_users WHERE email = $1
        ) OR EXISTS (
            SELECT 1 FROM file_users WHERE email = $1
        )
        """,
        email
    )
    if entry_status:
        raise All_Exceptions(
            message="Cannot delete email identity as it is associated with existing services (Mailboxes/Chat/Files). Please delete the associated services first.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    org_id = await db_session.fetchval(
        """
        SELECT managed_by FROM domains WHERE domain_name = (
            SELECT domain_name FROM email_identities WHERE email = $1
        )
        """,
        email
    )
    if org_id is None:
        raise All_Exceptions(
            message="Organization not found for the given email identity.",
            status_code=status.HTTP_404_NOT_FOUND
        )

    try:
        await db_session.execute(
            """
            DELETE FROM email_identities
            WHERE email = $1
            """,
            email
        )

        # After deleting the email identity, we need to update the utilized_email_identities count for the organization
        await db_session.execute(
            """
            UPDATE organizations
            SET utilized_email_identities = utilized_email_identities - 1
            WHERE organization_id = $1
            """,
            org_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete email identity {email}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_identity_details(
    db_session: PgSession,
    email: str,
    first_name: str,
    last_name: str,
    primary_phone: str,
    secondary_email: str,
    is_app_2fa_enabled: bool,
    is_sms_2fa_enabled: bool,
    is_email_2fa_enabled: bool,
    restriction_policy_id: str | None,
    department_id: str | None,
    is_enabled: bool
) -> None:
    """
    Update the details of a specific email identity
    """
    try:
        await db_session.execute(
            """
            UPDATE email_identities
            SET first_name = $1, last_name = $2, primary_phone = $3, secondary_email = $4,
                is_app_2fa_enabled = $5, is_sms_2fa_enabled = $6, is_email_2fa_enabled = $7,
                restriction_policy_id = $8, department_id = $9, is_enabled = $10, updated_at = CURRENT_TIMESTAMP
            WHERE email = $11
            """,
            first_name, last_name, primary_phone, secondary_email,
            is_app_2fa_enabled, is_sms_2fa_enabled, is_email_2fa_enabled,
            restriction_policy_id, department_id, is_enabled, email
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update email identity {email}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_identity_password(
    db_session: PgSession,
    email: str,
    new_base64_password: str
) -> None:
    """
    Update the password of a specific email identity
    """
    try:
        await db_session.execute(
            """
            UPDATE email_identities
            SET password_hash_ssha1 = $1, password_bcrypt = $2, password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, is_password_expired = FALSE
            WHERE email = $3
            """,
            *_generate_password_hashs(base64.b64decode(new_base64_password)),
            email
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update password for email identity {email}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def fetch_full_id_info_by_admin(email: str, db_session: PgSession) -> dict:
    """
    Fetch full identity information for a specific email identity
    Domain, MailBox, Chat, All attached Policies, Org Info, Server Info (MailBox)
    """
    try:
        result = await db_session.fetchrow(
            """
            SELECT
                -- Identity
                ei.email,
                ei.domain_name,
                ei.first_name,
                ei.last_name,
                ei.primary_phone,
                ei.secondary_email,
                ei.is_app_2fa_enabled,
                ei.is_sms_2fa_enabled,
                ei.is_email_2fa_enabled,
                ei.is_password_expired,
                ei.is_enabled AS is_identity_enabled,
                ei.department_id,
                ei.restriction_policy_id,

                -- Domain
                d.managed_by AS organization_id,
                d.is_active AS is_domain_active,
                d.is_dns_txt_verified,
                d.catch_all AS is_catch_all_enabled,
                d.is_hybrid,
                d.is_locked AS is_domain_locked,
                d.locked_servers_group AS domain_locked_to_servers,
                d.session_timeout,
                d.filter_policy_id,
                d.attachment_policy_id,
                d.disclaimer_id,
                d.caution_id,

                -- Mailbox
                mb.server_id,
                mb.is_enabled AS is_mailbox_enabled,
                mb.is_locked AS is_mailbox_locked,
                mb.forwarding_policy_id,
                mb.distribution_policy_id,
                mb.general_policy_id,
                mb.quota_allocated AS mailbox_quota_allocated,
                mb.quota_utilized_bytes AS mailbox_quota_utilized_bytes,
                mb.total_messages_count AS mailbox_total_messages_count,

                -- Chat
                cu.is_enabled AS is_chat_user_enabled

            FROM email_identities ei

            LEFT JOIN domains d
                ON d.domain_name = ei.domain_name
            
            LEFT JOIN chat_users cu
                ON cu.email = ei.email

            LEFT JOIN mailboxes mb
                ON mb.email = ei.email

            WHERE ei.email = $1
            """,
            email
        )
        if result is None:
            raise All_Exceptions(
                message="Email identity not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "email": result["email"],
            "domain_name": result["domain_name"],
            "first_name": result["first_name"],
            "last_name": result["last_name"],
            "primary_phone": result["primary_phone"],
            "secondary_email": result["secondary_email"],
            "is_app_2fa_enabled": result["is_app_2fa_enabled"],
            "is_sms_2fa_enabled": result["is_sms_2fa_enabled"],
            "is_email_2fa_enabled": result["is_email_2fa_enabled"],
            "is_password_expired": result["is_password_expired"],
            "is_identity_enabled": result["is_identity_enabled"],
            "department_id": str(result["department_id"]) if result["department_id"] else None,
            "restriction_policy_id": str(result["restriction_policy_id"]) if result["restriction_policy_id"] else None,
            "organization_id": str(result["organization_id"]) if result["organization_id"] else None,
            "is_domain_active": result["is_domain_active"],
            "is_dns_txt_verified": result["is_dns_txt_verified"],
            "is_catch_all_enabled": result["is_catch_all_enabled"],
            "is_hybrid": result["is_hybrid"],
            "is_domain_locked": result["is_domain_locked"],
            "domain_locked_to_servers": [str(server_id) for server_id in result["domain_locked_to_servers"]] if result["domain_locked_to_servers"] else [],
            "session_timeout": int(result["session_timeout"]) if result["session_timeout"] else None,
            "filter_policy_id": str(result["filter_policy_id"]) if result["filter_policy_id"] else None,
            "attachment_policy_id": str(result["attachment_policy_id"]) if result["attachment_policy_id"] else None,
            "disclaimer_id": str(result["disclaimer_id"]) if result["disclaimer_id"] else None,
            "caution_id": str(result["caution_id"]) if result["caution_id"] else None,
            "server_id": str(result["server_id"]) if result["server_id"] else None,
            "is_mailbox_enabled": result["is_mailbox_enabled"],
            "is_mailbox_locked": result["is_mailbox_locked"],
            "forwarding_policy_id": str(result["forwarding_policy_id"]) if result["forwarding_policy_id"] else None,
            "distribution_policy_id": str(result["distribution_policy_id"]) if result["distribution_policy_id"] else None,
            "general_policy_id": str(result["general_policy_id"]) if result["general_policy_id"] else None,
            "mailbox_quota_allocated": float(result["mailbox_quota_allocated"]) if result["mailbox_quota_allocated"] else None,
            "mailbox_quota_utilized_bytes": int(result["mailbox_quota_utilized_bytes"]) if result["mailbox_quota_utilized_bytes"] else None,
            "mailbox_total_messages_count": int(result["mailbox_total_messages_count"]) if result["mailbox_total_messages_count"] else None
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch full identity information for email {email}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
