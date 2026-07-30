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
from .organization import validate_organization_quota
from src.utils.models import All_Exceptions, ConnectorProperties


PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


async def _raise_check_domain_exists(db_session: PgSession, exception_message: str, domain_name: str, raise_exception_if_exists: bool = False) -> None:
    """
    Check if the domain already exists in the database
    """
    row = await db_session.fetchrow(
        "SELECT 1 FROM domains WHERE domain_name = $1", domain_name
    )

    if row and raise_exception_if_exists:
        raise All_Exceptions(
            message=exception_message,
            status_code=status.HTTP_409_CONFLICT
        )
    elif not row and not raise_exception_if_exists:
        raise All_Exceptions(
            message=exception_message,
            status_code=status.HTTP_404_NOT_FOUND
        )


async def get_domain_details(db_session: PgSession, domain_name: str) -> dict:
    """
    Get the details of a domain
    """
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    row = await db_session.fetchrow(
        """
        SELECT domain_name, managed_by, details,
            is_active, spam_destination, spam_destination_properties, anti_phishing_secret_code,
            max_password_age, max_password_age_properties, catch_all, catch_all_forward_to_email,
            is_hybrid, connector_properties, created_at, caution_id, disclaimer_id,
            filter_policy_id, attachment_policy_id, session_timeout, is_dns_txt_verified, dns_txt_verification_key
        FROM domains WHERE domain_name = $1
        """,
        domain_name
    )

    return {
        "domain_name": row["domain_name"],
        "managed_by": str(row["managed_by"]),
        "details": orjson.loads(row["details"]),
        "is_active": row["is_active"],
        "spam_destination": row["spam_destination"],
        "anti_phishing_secret_code": str(row["anti_phishing_secret_code"]),
        "spam_destination_properties": orjson.loads(row["spam_destination_properties"]),
        "max_password_age": row["max_password_age"],
        "max_password_age_properties": orjson.loads(row["max_password_age_properties"]),
        "catch_all": row["catch_all"],
        "catch_all_forward_to_email": row["catch_all_forward_to_email"],
        "is_hybrid": row["is_hybrid"],
        "caution_id": str(row["caution_id"]) if row["caution_id"] else None,
        "disclaimer_id": str(row["disclaimer_id"]) if row["disclaimer_id"] else None,
        "filter_policy_id": str(row["filter_policy_id"]) if row["filter_policy_id"] else None,
        "attachment_policy_id": str(row["attachment_policy_id"]) if row["attachment_policy_id"] else None,
        "connector_properties": orjson.loads(row["connector_properties"]),
        "session_timeout": int(row["session_timeout"]),
        "is_dns_txt_verified": row["is_dns_txt_verified"],
        "dns_txt_verification_key": str(row["dns_txt_verification_key"]),
        "created_at": row["created_at"].isoformat()
    }


async def create_new_domain(
    db_session: PgSession,
    domain_name: str,
    organization_id: str,
    is_active: bool,
    details: dict,
    spam_destination: str,
    spam_destination_properties: dict,
    max_password_age: int,
    max_password_age_properties: dict,
    enable_catch_all: bool,
    enable_hybrid_mode: bool,
    dns_txt_verification_key: str,
    anti_phishing_secret_code: str,
    caution_id: str | None,
    disclaimer_id: str | None,
    filter_policy_id: str | None,
    attachment_policy_id: str | None,
    session_timeout: int,
    catch_all_forwarding_address: str | None,
    hybrid_connector_properties: ConnectorProperties | None
) -> None:
    """
    Create a new domain in the database
    """
    # Check if the domain already exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=True,
        exception_message=f"Domain {domain_name} already exists"
    )

    if not hybrid_connector_properties:
        hybrid_connector_properties = ConnectorProperties(
            description="Default Hybrid Connector",
            fqdn="",
            port=-1,
            ipv4="",
            ipv6=None
        )

    connector_properties = {
        "description": hybrid_connector_properties.description,
        "fqdn": hybrid_connector_properties.fqdn,
        "port": hybrid_connector_properties.port,
        "ipv4": hybrid_connector_properties.ipv4,
        "ipv6": hybrid_connector_properties.ipv6 or ""
    }

    try:
        # Create a new domain
        await db_session.execute(
            """
            INSERT INTO domains (domain_name, managed_by, details,
            is_active, spam_destination, spam_destination_properties,
            max_password_age, max_password_age_properties,
            catch_all, catch_all_forward_to_email, is_hybrid, connector_properties,
            caution_id, disclaimer_id, filter_policy_id, attachment_policy_id, session_timeout, dns_txt_verification_key, anti_phishing_secret_code)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            """,
            domain_name,
            organization_id,
            orjson.dumps(details).decode("utf-8"),
            is_active,
            spam_destination,
            orjson.dumps(spam_destination_properties).decode("utf-8"),
            max_password_age,
            orjson.dumps(max_password_age_properties).decode("utf-8"),
            enable_catch_all,
            catch_all_forwarding_address,
            enable_hybrid_mode,
            orjson.dumps(connector_properties).decode("utf-8"),
            caution_id if caution_id else None,
            disclaimer_id if disclaimer_id else None,
            filter_policy_id if filter_policy_id else None,
            attachment_policy_id if attachment_policy_id else None,
            session_timeout,
            dns_txt_verification_key,
            anti_phishing_secret_code
        )

    except Exception as e:
        logging.error(f"Error creating new domain: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error creating new domain: {e}",
            status_code=status.HTTP_410_GONE
        )


async def get_all_domains_by_organization(db_session: PgSession, organization_id: str, search_query: str = "",page: int = 1, page_size: int = 10) -> dict:
    """
    Get all domains by organization
    """
    total_count = await db_session.fetchval(
        "SELECT COUNT(*) FROM domains WHERE managed_by = $1 AND domain_name ILIKE $2",
        organization_id,
        f"%{search_query}%"
    )
    if total_count is None:
        raise All_Exceptions(
            message=f"No domains found for organization {organization_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )

    offset = (page - 1) * page_size
    rows = await db_session.fetch(
        """
        SELECT domain_name, is_active, created_at, is_dns_txt_verified
        FROM domains WHERE managed_by = $1 AND domain_name ILIKE $2
        ORDER BY domain_name
        LIMIT $3 OFFSET $4
        """,
        organization_id,
        f"%{search_query}%",
        page_size,
        offset
    )

    domains = [
        {
            "domain_name": row["domain_name"],
            "is_active": row["is_active"],
            "is_dns_txt_verified": row["is_dns_txt_verified"],
            "created_at": row["created_at"].isoformat()
        }
        for row in rows
    ]
    return {
        "domains": domains,
        "total_count": total_count,
        "current_page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }


async def update_domain_info(
    db_session: PgSession,
    organization_id: str,
    domain_name: str,
    details: dict,
    anti_phishing_secret_code: str,
    enable_catch_all: bool,
    catch_all_forwarding_address: str | None,
    enable_hybrid_mode: bool,
    hybrid_connector_properties: ConnectorProperties | None,
    spam_destination: str,
    spam_destination_properties: dict,
    max_password_age: int,
    max_password_age_properties: dict,
    caution_id: str | None,
    disclaimer_id: str | None,
    filter_policy_id: str | None,
    attachment_policy_id: str | None,
    session_timeout: int
) -> None:
    """
    Update the domain information in the database
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    if not hybrid_connector_properties:
        hybrid_connector_properties = ConnectorProperties(
            description="Default Hybrid Connector",
            fqdn="",
            port=-1,
            ipv4="",
            ipv6=None
        )

    connector_properties = {
        "description": hybrid_connector_properties.description,
        "fqdn": hybrid_connector_properties.fqdn,
        "port": hybrid_connector_properties.port,
        "ipv4": hybrid_connector_properties.ipv4,
        "ipv6": hybrid_connector_properties.ipv6 or ""
    }

    try:
        # Update the domain information
        await db_session.execute(
            """
            UPDATE domains SET details = $1, is_active = TRUE,
                catch_all = $2, catch_all_forward_to_email = $3, is_hybrid = $4,
                connector_properties = $5, spam_destination = $6,
                spam_destination_properties = $7, max_password_age = $8,
                max_password_age_properties = $9, caution_id = $10, disclaimer_id = $11,
                filter_policy_id = $12, attachment_policy_id = $13, session_timeout = $14,
                anti_phishing_secret_code = $15
            WHERE domain_name = $16 AND managed_by = $17
            """,
            orjson.dumps(details).decode("utf-8"),
            enable_catch_all,
            catch_all_forwarding_address,
            enable_hybrid_mode,
            orjson.dumps(connector_properties).decode("utf-8"),
            spam_destination,
            orjson.dumps(spam_destination_properties).decode("utf-8"),
            max_password_age,
            orjson.dumps(max_password_age_properties).decode("utf-8"),
            caution_id,
            disclaimer_id,
            filter_policy_id,
            attachment_policy_id,
            session_timeout,
            anti_phishing_secret_code,
            domain_name,
            organization_id
        )

    except Exception as e:
        logging.error(f"Error updating domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error updating domain {domain_name}: {e}",
            status_code=status.HTTP_410_GONE
        )


async def update_domain_activation_status(db_session: PgSession, organization_id: str, domain_name: str, is_active: bool) -> None:
    """
    Update the activation status of a domain
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    try:
        # Update the activation status of the domain
        await db_session.execute(
            "UPDATE domains SET is_active = $1 WHERE domain_name = $2 AND managed_by = $3 AND is_dns_txt_verified = TRUE",
            is_active,
            domain_name,
            organization_id
        )

    except Exception as e:
        logging.error(f"Error updating activation status for domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error updating activation status for domain {domain_name}: {e}",
            status_code=status.HTTP_410_GONE
        )


async def delete_domain_and_update_quota(db_session: PgSession, organization_id: str, domain_name: str) -> None:
    """
    Delete a domain and update the organization's quota
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    # Get all the sum of the allocated quota of mailboxes under the domain to update the organization's quota after deleting the domain
    row = await db_session.fetchrow(
        "SELECT SUM(quota_allocated) AS total_mailbox_quota FROM mailboxes WHERE domain_name = $1",
        domain_name
    )
    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )

    total_mailbox_quota = float(row["total_mailbox_quota"] or 0.0)

    # TODO: As we add more services (like chat, file), we need to also calculate the utilized quota 
    # for those services under the domain and add it to total_mailbox_quota 
    # to get the total utilized quota for the domain before
    # deleting it, so that we can update the organization's quota correctly

    try:
        # Delete the domain
        await db_session.execute(
            "DELETE FROM domains WHERE domain_name = $1 AND managed_by = $2",
            domain_name,
            organization_id
        )   # Note: This will automatically cascade delete all related mailboxes and other data

        # Update the organization's quota
        await db_session.execute(
            """
            UPDATE organizations
            SET quota_utilized = quota_utilized - $1
            WHERE organization_id = $2
            """,
            total_mailbox_quota,
            organization_id
        )

    except Exception as e:
        logging.error(f"Error deleting domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error deleting domain {domain_name}: {e}",
            status_code=status.HTTP_410_GONE
        )


async def check_domain_organization_mapping(
    db_session: PgSession,
    organization_id: str,
    domain_name: str
) -> None:
    """
    Check if the domain is managed by the organization, if not raise an exception
    """
    row = await db_session.fetchrow(
        "SELECT 1 FROM domains WHERE domain_name = $1 AND managed_by = $2",
        domain_name,
        organization_id
    )
    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} is not managed by organization {organization_id} or does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )


async def migrate_domain_to_new_organization(db_session: PgSession, organization_id: str, domain_name: str, new_organization_id: str) -> None:
    """
    Migrate a domain from one organization to another
    """
    # Check if the domain exists and is managed by the current organization
    await check_domain_organization_mapping(
        db_session=db_session,
        organization_id=organization_id,
        domain_name=domain_name
    )

    # Check if the new organization exists
    row = await db_session.fetchrow(
        "SELECT 1 FROM organizations WHERE organization_id = $1",
        new_organization_id
    )
    if not row:
        raise All_Exceptions(
            message=f"New organization {new_organization_id} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # Get full domain details that need to be migrated
    domain_details = await get_domain_details(
        db_session=db_session,
        domain_name=domain_name
    )

    # Get the total allocated quota for the domain (including all services like mailbox, chat, file, etc.)
    # to validate the new organization's quota before migrating the domain
    row = await db_session.fetchrow(
        """
        SELECT 
            (SELECT SUM(quota_allocated) FROM mailboxes WHERE domain_name = $1) AS total_mailbox_quota
        """,
        domain_name
    )
    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    total_mailbox_quota = float(row["total_mailbox_quota"] or 0.0)

    # TODO: Add more services (like chat, file) in the above query to get the total allocated quota for the domain across all services

    # Quota validation for the new organization
    await validate_organization_quota(
        db_session=db_session,
        organization_id=new_organization_id,
        required_storage_quota=total_mailbox_quota,
        required_email_identities=-1
    )

    try:
        # Transaction to ensure atomicity
        # If any step fails, the transaction will be rolled back
        # This is important to ensure that the domain is not left in an inconsistent state
        async with db_session.transaction():
            # Copy discaimers and cautions under the new organization (and save their ids)
            new_caution_id, new_disclaimer_id = None, None
            if domain_details["disclaimer_id"]:
                new_disclaimer_id = str(uuid.uuid4())
                await db_session.execute(
                    """
                    INSERT INTO disclaimers (
                        disclaimer_id,
                        organization_id,
                        disclaimer_name,
                        info,
                        html_content,
                        text_content,
                        created_at,
                        updated_at
                    )
                    SELECT
                        $1,
                        $2,
                        disclaimer_name,
                        info,
                        html_content,
                        text_content,
                        created_at,
                        updated_at
                    FROM disclaimers
                    WHERE disclaimer_id = $3
                    """,
                    new_disclaimer_id,
                    new_organization_id,
                    domain_details["disclaimer_id"]
                )

            if domain_details["caution_id"]:
                new_caution_id = str(uuid.uuid4())
                await db_session.execute(
                    """
                    INSERT INTO cautions (
                        caution_id,
                        organization_id,
                        caution_name,
                        info,
                        html_content,
                        text_content,
                        created_at,
                        updated_at
                    )
                    SELECT
                        $1,
                        $2,
                        caution_name,
                        info,
                        html_content,
                        text_content,
                        created_at,
                        updated_at
                    FROM cautions
                    WHERE caution_id = $3
                    """,
                    new_caution_id,
                    new_organization_id,
                    domain_details["caution_id"]
                )

            # TODO: Copy all the departments under the domain to the new organization (and save their ids)

            # Unlink the department_id from all the mailboxes under the domain
            await db_session.execute(
                """
                UPDATE email_identities
                SET department_id = NULL
                WHERE domain_name = $1
                """,
                domain_name
            )

            # Update the domain to be managed by the new organization
            await db_session.execute(
                """
                UPDATE domains
                SET managed_by = $1, caution_id = $2, disclaimer_id = $3
                WHERE domain_name = $4 AND managed_by = $5
                """,
                new_organization_id,
                new_caution_id,
                new_disclaimer_id,
                domain_name,
                organization_id
            )

            # Update the old organization's quota (decrease the quota_utilized)
            await db_session.execute(
                """
                UPDATE organizations
                SET quota_utilized = quota_utilized - $1
                WHERE organization_id = $2
                """,
                total_mailbox_quota,
                organization_id
            )

            # Update the new organization's quota (increase the quota_utilized)
            await db_session.execute(
                """
                UPDATE organizations
                SET quota_utilized = quota_utilized + $1
                WHERE organization_id = $2
                """,
                total_mailbox_quota,
                new_organization_id
            )

    except Exception as e:
        logging.error(f"Error migrating domain {domain_name} to organization {new_organization_id}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error migrating domain {domain_name} to organization {new_organization_id}: {e}",
            status_code=status.HTTP_410_GONE
        )


async def update_domain_lock_status(
    db_session: PgSession,
    domain_name: str,
    is_locked: bool,
    locked_servers_group: list[str] | None
) -> None:
    """
    Update the lock status of a domain
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    # If its locked, there should be a list of servers group that are locked
    if is_locked and not locked_servers_group:
        raise All_Exceptions(
            message="Locked servers group must be provided when locking the domain",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Two cases:
    # Unlocking the domain (is_locked=False) - locked_servers_group should be None
    # Locking the domain (is_locked=True) - locked_servers_group should be a list of server IDs (and validate it)
    if not is_locked:
        await db_session.execute(
            """
            UPDATE domains
            SET is_locked = FALSE
            WHERE domain_name = $1
            """,
            domain_name
        )
        return  # No need to update locked_servers_group if unlocking

    # Locking the domain
    if locked_servers_group is None or not isinstance(locked_servers_group, list):
        raise All_Exceptions(
            message="locked_servers_group must be a list of server IDs when locking the domain",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # All the server IDs in the locked_servers_group should be valid server IDs (validate quota also)
    row = await db_session.fetchrow(
        """
        SELECT 
            SUM(quota_allocated - quota_utilized) AS total_available_space,
            COUNT(*) AS found_servers
        FROM servers
        WHERE server_id = ANY($1) AND is_active = TRUE
        """,
        locked_servers_group
    )

    if row["found_servers"] != len(locked_servers_group):
        raise All_Exceptions(
            message="One or more servers do not exist or are not active",
            status_code=status.HTTP_404_NOT_FOUND
        )

    total_available_space = float(row["total_available_space"] or 0.0)
    if total_available_space <= 0:
        raise All_Exceptions(
            message="No available space in the locked servers group",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )
    
    row = await db_session.fetchrow(
        """
        SELECT 
            (SELECT SUM(quota_allocated) FROM mailboxes WHERE domain_name = $1) AS total_mailbox_quota
        """,
        domain_name
    )
    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # TODO: Add more services (like chat, file) in the above query to get the total allocated quota for the domain
    # across all services to compare it with the total available space in the locked servers group before locking the domain

    total_mailbox_quota = float(row["total_mailbox_quota"] or 0.0)
    if total_mailbox_quota >= total_available_space:
        raise All_Exceptions(
            message=f"Domain {domain_name} quota {total_mailbox_quota} exceeds the total available space in the locked servers group {total_available_space}",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )

    # If there are any mailboxes under the domain, they should be mapped only to those servers
    row = await db_session.fetchrow(
        """
        WITH invalid_mailboxes AS (
            SELECT COUNT(*) AS invalid_mailboxes
            FROM mailboxes
            WHERE domain_name = $1
            AND is_enabled = TRUE
            AND NOT (server_id = ANY($2))
        ),
        in_progress_migrations AS (
            SELECT COUNT(*) AS migrating_mailboxes
            FROM mailbox_migrations
            WHERE email IN (
                SELECT email FROM mailboxes WHERE domain_name = $1
            )
            AND migration_status IN ('INITIALIZING', 'IN_PROGRESS')
        )
        SELECT
            $2 AS allowed_servers,
            (SELECT invalid_mailboxes FROM invalid_mailboxes) AS invalid_mailboxes,
            (SELECT migrating_mailboxes FROM in_progress_migrations) AS migrating_mailboxes;
        """,
        domain_name,
        locked_servers_group
    )

    if row["invalid_mailboxes"] > 0:
        raise All_Exceptions(
            message="Some mailboxes are mapped to servers outside the allowed list",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )

    if row["migrating_mailboxes"] > 0:
        raise All_Exceptions(
            message="There are mailbox migrations in progress for this domain",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )
    
    # Update the domain's lock status and locked servers group
    await db_session.execute(
        """
        UPDATE domains
        SET is_locked = TRUE,
            locked_servers_group = $1
        WHERE domain_name = $2
        """,
        locked_servers_group,
        domain_name
    )


async def get_domain_lock_status(db_session: PgSession, domain_name: str) -> dict:
    """
    Get the lock status of a domain
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    row = await db_session.fetchrow(
        "SELECT is_locked, locked_servers_group FROM domains WHERE domain_name = $1",
        domain_name
    )
    
    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return {
        "is_locked": row["is_locked"],
        "locked_servers_group": [str(server_id) for server_id in row["locked_servers_group"]] if row["locked_servers_group"] else []
    }


async def check_if_any_migration_in_progress_of_domain(db_session: PgSession, domain_name: str) -> dict:
    """
    Check if there are any mailbox migrations in progress for the domain
    """
    row = await db_session.fetchrow(
        """
        SELECT COUNT(*) AS migration_count
        FROM mailbox_migrations
        WHERE email IN (
            SELECT email FROM mailboxes WHERE domain_name = $1
        )
        AND migration_status IN ('INITIALIZING', 'IN_PROGRESS')
        """,
        domain_name
    )

    if not row:
        raise All_Exceptions(
            message=f"Domain {domain_name} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return {
        "migration_in_progress": row["migration_count"] > 0,
        "migration_count": row["migration_count"],
        "domain_name": domain_name
    }


async def get_all_domains_under_organization(db_session: PgSession, organization_id: str) -> list[str]:
    """
    Get all domains under an organization
    """
    rows = await db_session.fetch(
        "SELECT domain_name FROM domains WHERE managed_by = $1",
        organization_id
    )

    if not rows:
        return []

    return [str(row["domain_name"]) for row in rows]


async def get_domains_stats(db_session: PgSession, organization_id: str) -> dict:
    """
    Get the total active and inactive domains under an organization
    """
    row = await db_session.fetchrow(
        """
        SELECT 
            COUNT(*) FILTER (WHERE is_active = TRUE) AS active_domains,
            COUNT(*) FILTER (WHERE is_active = FALSE) AS inactive_domains
        FROM domains
        WHERE managed_by = $1
        """,
        organization_id
    )

    if not row:
        raise All_Exceptions(
            message=f"No domains found for organization {organization_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return {
        "organization_id": organization_id,
        "active_domains": int(row["active_domains"]),
        "inactive_domains": int(row["inactive_domains"]),
        "total_domains": int(row["active_domains"]) + int(row["inactive_domains"])
    }


async def update_domain_txt_verification_status(db_session: PgSession, domain_name: str, is_verified: bool) -> None:
    """
    Update the DNS TXT verification status of a domain (If its not verified, then also disable the domain from being active until its verified)
    """
    # Check if the domain exists
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    try:
        # Update the DNS TXT verification status of the domain and also disable the domain from being active if its not verified
        await db_session.execute(
            """
            UPDATE domains
            SET
                is_dns_txt_verified = $1,
                is_active = is_active AND $1
            WHERE domain_name = $2;
            """,
            is_verified,
            domain_name
        )

    except Exception as e:
        logging.error(f"Error updating DNS TXT verification status for domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error updating DNS TXT verification status for domain {domain_name}: {e}",
            status_code=status.HTTP_410_GONE
        )


async def check_if_domain_has_associated_identities(db_session: PgSession, domain_name: str) -> bool:
    """
    Check if the domain has any associated identities linked to it
    """
    await _raise_check_domain_exists(
        db_session=db_session,
        domain_name=domain_name,
        raise_exception_if_exists=False,
        exception_message=f"Domain {domain_name} does not exist"
    )

    try:
        count = await db_session.fetchval(
            "SELECT COUNT(*) FROM email_identities WHERE domain_name = $1",
            domain_name
        )
        return count > 0

    except Exception as e:
        logging.error(f"Error checking associated identities for domain {domain_name}: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Error checking associated identities for domain {domain_name}: {e}",
            status_code=status.HTTP_410_GONE
        )
