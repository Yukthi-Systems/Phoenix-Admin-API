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


def shorten_api_key(api_key: str) -> str:
    """
    Docstring for shorten_api_key
    
    :param api_key: The full API key string (UUID V4 format)
    :type api_key: str
    :return: A shortened version of the API key for display purposes
    :rtype: str
    """
    return f"{api_key[:7]}...{api_key[-3:]}"


async def _raise_check_organization_exists(db_session: PgSession, exception_message: str, organization_name: str = None, organization_id: str = None, raise_exception_if_exists: bool = False) -> None:
    """
    Check if the organization already exists in the database
    Use either organization_name or organization_id to check for existence
    """
    if organization_name:
        row = await db_session.fetchrow(
            "SELECT 1 FROM organizations WHERE organization_name = $1", organization_name
        )
    elif organization_id:
        row = await db_session.fetchrow(
            "SELECT 1 FROM organizations WHERE organization_id = $1", organization_id
        )
    else:
        raise All_Exceptions(
            message="Either organization_name or organization_id must be provided",
            status_code=status.HTTP_400_BAD_REQUEST
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


async def validate_organization_quota(db_session: PgSession, organization_id: str, required_storage_quota: float, required_email_identities: int) -> None:
    """
    Validate if the organization has enough quota
    """
    # Storage Quota check
    row = await db_session.fetchrow(
        "SELECT quota_allocated, quota_utilized, allocated_email_identities, utilized_email_identities FROM organizations WHERE organization_id = $1 AND is_active = TRUE",
        organization_id
    )
    if not row:
        raise All_Exceptions(
            message=f"Organization with ID {organization_id} does not exist or is inactive",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Storage Quota check
    quota_allocated, quota_utilized = float(row["quota_allocated"]), float(row["quota_utilized"])
    if quota_utilized + required_storage_quota > quota_allocated:
        raise All_Exceptions(
            message=f"Not enough space available. Required: {required_storage_quota - (quota_allocated - quota_utilized)}, Available: {quota_allocated - quota_utilized}, Requested: {required_storage_quota}",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )

    # Email Identities check
    allocated_email_identities, utilized_email_identities = int(row["allocated_email_identities"]), int(row["utilized_email_identities"])
    if allocated_email_identities != -1 and utilized_email_identities + required_email_identities > allocated_email_identities:
        raise All_Exceptions(
            message=f"Not enough email identities available. Required: {required_email_identities - (allocated_email_identities - utilized_email_identities)}, Available: {allocated_email_identities - utilized_email_identities}, Requested: {required_email_identities}",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )


async def get_organization_details(db_session: PgSession, organization_id: str) -> dict:
    """
    Get organization details by ID
    """
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        row = await db_session.fetchrow(
            """
            SELECT
                organization_name, organization_info, is_active, email_service_enabled,
                chat_service_enabled, quota_allocated, quota_utilized, parent_organization_id,
                hierarchy_path, file_service_enabled, allocated_email_identities, utilized_email_identities
            FROM organizations WHERE organization_id = $1
            """,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message=f"Organization with ID {organization_id} does not exist or is inactive",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "organization_id": organization_id,
            "organization_name": row["organization_name"],
            "details": orjson.loads(row["organization_info"]),
            "is_active": row["is_active"],
            "email_service_enabled": row["email_service_enabled"],
            "chat_service_enabled": row["chat_service_enabled"],
            "file_service_enabled": row["file_service_enabled"],
            "quota_allocated": float(row["quota_allocated"]),
            "quota_utilized": float(row["quota_utilized"]),
            "allocated_email_identities": int(row["allocated_email_identities"]),
            "utilized_email_identities": int(row["utilized_email_identities"]),
            "parent_organization_id": str(row["parent_organization_id"]),
            "hierarchy_path": row["hierarchy_path"]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch organization details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_new_organization(
    db_session: PgSession,
    organization_name: str,
    organization_info: dict,
    is_active: bool,
    email_service_enabled: bool,
    chat_service_enabled: bool,
    file_service_enabled: bool,
    quota_allocated: float,
    quota_utilized: float,
    allocated_email_identities: int,
    utilized_email_identities: int,
    parent_organization_id: str,
    hierarchy_path: list[str]
) -> None:
    """
    Create a new organization in the database
    """
    # Check if the organization already exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_name=organization_name,
        raise_exception_if_exists=True,
        exception_message=f"Organization with name {organization_name} already exists"
    )

    # Check if the parent organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=parent_organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Parent organization with ID {parent_organization_id} does not exist"
    )

    # Validate the quota for the organization
    await validate_organization_quota(
        db_session=db_session,
        organization_id=parent_organization_id,
        required_storage_quota=quota_allocated,
        required_email_identities=allocated_email_identities
    )

    try:
        # Generate a unique organization ID
        organization_id = str(uuid.uuid4())
        hierarchy_path.append(organization_id)

        # Create a new organization
        await db_session.execute(
            """
            INSERT INTO organizations (organization_id, organization_name, organization_info,
            is_active, email_service_enabled, chat_service_enabled, file_service_enabled, quota_allocated, quota_utilized,
            allocated_email_identities, utilized_email_identities, parent_organization_id, hierarchy_path)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            organization_id,
            organization_name,
            orjson.dumps(organization_info).decode("utf-8"),
            is_active,
            email_service_enabled,
            chat_service_enabled,
            file_service_enabled,
            quota_allocated,
            quota_utilized,
            allocated_email_identities,
            utilized_email_identities,
            parent_organization_id,
            hierarchy_path
        )

        # Reduse the parent organization's quota
        await db_session.execute(
            """
            UPDATE organizations
            SET quota_utilized = quota_utilized + $1,
                utilized_email_identities = utilized_email_identities + $2
            WHERE organization_id = $3 AND is_active = TRUE
            """,
            quota_allocated,
            allocated_email_identities,
            parent_organization_id
        )

    except Exception as e:
        logging.error(f"Error creating new organization: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new organization: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_organizations_list(db_session: PgSession, parent_organization_id: str, page: int = 1, limit: int = 10) -> dict:
    """
    Get a list of organizations under a specific parent organization
    """
    if page < 1 or limit < 1 or limit > 50:
        raise All_Exceptions(
            message="Page and limit must be positive integers, and limit cannot exceed 50",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if the parent organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=parent_organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Parent organization with ID {parent_organization_id} does not exist"
    )

    try:
        # Get all the organizations where the parent organization ID is satisfied
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM organizations
            WHERE parent_organization_id = $1
            """,
            parent_organization_id
        )
        if total_count == 0:
            return {"total_count": 0, "organizations": [], "current_page": page, "total_pages": 0}

        offset = (page - 1) * limit
        rows = await db_session.fetch(
            """
            SELECT organization_id, organization_name, is_active, utilized_email_identities,
            email_service_enabled, chat_service_enabled, file_service_enabled,
            quota_allocated, quota_utilized, created_at, allocated_email_identities
            FROM organizations WHERE parent_organization_id = $1
            ORDER BY organization_name LIMIT $2 OFFSET $3
            """,
            parent_organization_id,
            limit,
            offset
        )
        organizations = [
            {
                "organization_id": str(row["organization_id"]),
                "organization_name": row["organization_name"],
                "is_active": row["is_active"],
                "email_service_enabled": row["email_service_enabled"],
                "chat_service_enabled": row["chat_service_enabled"],
                "file_service_enabled": row["file_service_enabled"],
                "quota_allocated": float(row["quota_allocated"]),
                "quota_utilized": float(row["quota_utilized"]),
                "allocated_email_identities": int(row["allocated_email_identities"]),
                "utilized_email_identities": int(row["utilized_email_identities"]),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            for row in rows
        ]
        return {
            "organizations": organizations,
            "current_page": page,
            "total_pages": (total_count + limit - 1) // limit,
            "total_count": total_count
        }

    except Exception as e:
        logging.error(f"Error fetching organizations list: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch organizations list: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def edit_organization_details(
    db_session: PgSession,
    organization_id: str,
    organization_info: dict,
    email_service_enabled: bool,
    chat_service_enabled: bool,
    file_service_enabled: bool
) -> None:
    """
    Edit organization details
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        await db_session.execute(
            """
            UPDATE organizations
            SET organization_info = $1, email_service_enabled = $2, chat_service_enabled = $3, file_service_enabled = $4
            WHERE organization_id = $5
            """,
            orjson.dumps(organization_info).decode("utf-8"),
            email_service_enabled,
            chat_service_enabled,
            file_service_enabled,
            organization_id
        )

    except Exception as e:
        logging.error(f"Error editing organization details: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to edit organization details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_organization_activation_status(db_session: PgSession, organization_id: str, is_active: bool) -> None:
    """
    Enable or disable an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    # Check if all the parent organizations of the given organization are active before activating the organization
    all_are_active = await db_session.fetchval(
        # Just by taking a look at hierarchy_path column (list of UUID's) is enough
        """
        SELECT bool_and(is_active)
        FROM organizations
        WHERE organization_id = ANY (
            ARRAY(
                SELECT unnest(hierarchy_path)::uuid
                FROM organizations
                WHERE organization_id = $1
            )
        )
        AND organization_id <> $1;
        """,
        organization_id
    )
    if not all_are_active:
        raise All_Exceptions(
            message="Cannot activate organization because one or more parent organizations are inactive",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )

    try:
        # If activating the organization, then no need to enable all the child organizations
        if is_active:
            await db_session.execute(
                """
                UPDATE organizations
                SET is_active = $1
                WHERE organization_id = $2
                """,
                is_active,
                organization_id
            )

        # If deactivating the organization, then we need to disable all the child organizations as well
        else:
            # Fetch all the child organizations of the given organization to update their activation status as well
            # Avoid infinite loop by checking if organization_id is not the same as parent_organization_id in the recursive query
            recursive_rows = await db_session.fetch(
                """
                WITH RECURSIVE org_tree AS (
                    SELECT organization_id
                    FROM organizations
                    WHERE organization_id = $1 AND organization_id != parent_organization_id
                    UNION ALL
                    SELECT o.organization_id
                    FROM organizations o
                    INNER JOIN org_tree ot ON o.parent_organization_id = ot.organization_id
                )
                SELECT organization_id FROM org_tree
                """,
                organization_id
            )
            organization_ids_to_update = [str(row["organization_id"]) for row in recursive_rows]

            await db_session.execute(
                """
                UPDATE organizations
                SET is_active = $1
                WHERE organization_id = ANY($2::uuid[])
                """,
                is_active,
                organization_ids_to_update
            )

    except Exception as e:
        logging.error(f"Error updating organization activation status: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update organization activation status: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_organization_quota(db_session: PgSession, organization_id: str, new_quota: float) -> None:
    """
    Update organization quota
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    # Get the current quota and utilized quota of the organization
    # Also fetch the parent organization ID to update its quota
    row = await db_session.fetchrow(
        "SELECT quota_allocated, quota_utilized, parent_organization_id FROM organizations WHERE organization_id = $1",
        organization_id
    )
    if not row:
        raise All_Exceptions(
            message=f"Organization with ID {organization_id} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    current_quota = float(row["quota_allocated"])
    utilized_space = float(row["quota_utilized"])
    parent_organization_id = str(row["parent_organization_id"])

    # Check if the new quota is less than the utilized space
    if new_quota < utilized_space:
        raise All_Exceptions(
            message=f"New quota {new_quota} is less than the utilized space {utilized_space} for organization {organization_id}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if the new quota is same as the utilized space
    if new_quota == utilized_space:
        raise All_Exceptions(
            message=f"New quota {new_quota} is the same as the utilized space {utilized_space} for organization {organization_id}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if the new quota is the same as the current quota
    if new_quota == current_quota:
        raise All_Exceptions(
            message=f"New quota {new_quota} is the same as the current quota for organization {organization_id}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Calculate the required quota for the parent organization
    # There are only two cases:
    # 1. If the new quota is greater than the current quota, we need to increase the parent organization's quota
    # 2. If the new quota is less than the current quota, we need to decrease the parent organization's quota
    if (new_quota > current_quota) and (organization_id != parent_organization_id): # Case 1
        required_quota = new_quota - current_quota
        # Check the space for the parent organization
        # Validate the new quota against the parent organization's quota
        await validate_organization_quota(
            db_session=db_session,
            organization_id=parent_organization_id,
            required_storage_quota=required_quota,
            required_email_identities=-1
        )
    else:   # Case 2
        # No need to validate parent organization quota if the new quota is less than the current quota
        # That means we are just reducing the quota for the domain, not increasing it
        # But there is one case where the organization is its own parent organization (that is the initial organization)
        # In that case, we do not need to check the parent organization's quota
        pass

    try:
        # Update the organization quota
        await db_session.execute(
            """
            UPDATE organizations
            SET quota_allocated = $1
            WHERE organization_id = $2
            """,
            new_quota,
            organization_id
        )

        # Update the parent organization's quota if the new quota is greater than the current quota
        if (new_quota > current_quota) and (organization_id != parent_organization_id):
            await db_session.execute(
                """
                UPDATE organizations
                SET quota_utilized = quota_utilized + $1
                WHERE organization_id = $2 AND is_active = TRUE
                """,
                new_quota - current_quota,
                parent_organization_id
            )
        elif (new_quota < current_quota) and (organization_id != parent_organization_id):
            await db_session.execute(
                """
                UPDATE organizations
                SET quota_utilized = quota_utilized - $1
                WHERE organization_id = $2 AND is_active = TRUE
                """,
                current_quota - new_quota,
                parent_organization_id
            )
        else:
            # This casse is not expected as we have already checked that the new quota is not same as the current quota
            # But there is one case where the organization is its own parent organization (that is the initial organization)
            # In that case, we do not need to update the parent organization's quota (safe warning, not an error)
            logging.warning(f"Organization {organization_id} is its own parent organization, no need to update parent organization's quota")

    except Exception as e:
        logging.error(f"Error updating organization quota: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update organization quota: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_organization_identity_quota(db_session: PgSession, organization_id: str, new_quota: int) -> None:
    """
    Update organization identity quota
    """
    if new_quota == 0 or new_quota < -1:
        raise All_Exceptions(
            message=f"New allocated email identities quota {new_quota} is not valid for organization {organization_id}. It must be either -1 (for unlimited) or a positive integer.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    # Get the current allocated email identities and utilized email identities of the organization
    # Also fetch the parent organization ID to update its quota
    row = await db_session.fetchrow(
        "SELECT allocated_email_identities, utilized_email_identities, parent_organization_id FROM organizations WHERE organization_id = $1 AND is_active = TRUE",
        organization_id
    )
    if not row:
        raise All_Exceptions(
            message=f"Organization with ID {organization_id} does not exist or is inactive",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    current_allocated_email_identities = int(row["allocated_email_identities"])
    current_utilized_email_identities = int(row["utilized_email_identities"])
    parent_organization_id = str(row["parent_organization_id"])

    row_parent = await db_session.fetchrow(
        "SELECT allocated_email_identities, utilized_email_identities FROM organizations WHERE organization_id = $1 AND is_active = TRUE",
        parent_organization_id
    )
    if not row_parent:
        raise All_Exceptions(
            message=f"Parent organization with ID {parent_organization_id} does not exist or is inactive",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    parent_allocated_email_identities = int(row_parent["allocated_email_identities"])
    parent_utilized_email_identities = int(row_parent["utilized_email_identities"])

    # Two High level cases: (User will set Quota as either -1 (unlimited) or any positive integer)
    if new_quota == -1:
        # Check if the parent organization has unlimited email identities, if not then we cannot set the quota to unlimited for the child organization
        if parent_allocated_email_identities != -1:
            raise All_Exceptions(
                message=f"Cannot set allocated email identities to unlimited for organization {organization_id} because parent organization {parent_organization_id} does not have unlimited allocated email identities",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    # Case where user will set a positive integer as the new allocated email identities quota
    else:
        # If user is moving from unlimited to limited quota, then we need to check if the new quota is greater than the currently utilized email identities
        if (current_allocated_email_identities == -1) and (current_utilized_email_identities > new_quota):
            raise All_Exceptions(
                message=f"New allocated email identities quota {new_quota} cannot be set for organization {organization_id} because it is less than the currently utilized email identities {current_utilized_email_identities}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # If user is moving from one limited quota to another limited quota, then we need to check if the new quota is supported by the parent organization's remaining quota
        if (current_allocated_email_identities != -1) and (new_quota > current_allocated_email_identities):
            required_additional_email_identities = new_quota - current_allocated_email_identities
            if parent_allocated_email_identities == -1:
                # Parent organization has unlimited email identities, so we can allow the increase in quota
                pass
            else:
                # Parent organization has limited email identities, so we need to check if the increase in quota is supported by the parent organization's remaining quota
                if parent_utilized_email_identities + required_additional_email_identities > parent_allocated_email_identities:
                    raise All_Exceptions(
                        message=f"New allocated email identities quota {new_quota} cannot be set for organization {organization_id} because parent organization {parent_organization_id} does not have enough remaining allocated email identities to support this increase. Required additional email identities: {required_additional_email_identities}, Parent organization's remaining allocated email identities: {parent_allocated_email_identities - parent_utilized_email_identities}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

    try:
        # Update the organization allocated email identities quota
        await db_session.execute(
            """
            UPDATE organizations
            SET allocated_email_identities = $1
            WHERE organization_id = $2
            """,
            new_quota,
            organization_id
        )

        # Update the parent organization's utilized email identities if the new quota is greater than the current quota
        if new_quota > current_allocated_email_identities:
            additional_email_identities = new_quota - current_allocated_email_identities
            await db_session.execute(
                """
                UPDATE organizations
                SET utilized_email_identities = utilized_email_identities + $1
                WHERE organization_id = $2 AND is_active = TRUE
                """,
                additional_email_identities,
                parent_organization_id
            )
        elif new_quota < current_allocated_email_identities:
            reduced_email_identities = current_allocated_email_identities - new_quota
            await db_session.execute(
                """
                UPDATE organizations
                SET utilized_email_identities = utilized_email_identities - $1
                WHERE organization_id = $2 AND is_active = TRUE
                """,
                reduced_email_identities,
                parent_organization_id
            )
        else:
            # This case is not expected as we have already checked that the new quota is not same as the current quota
            logging.warning(f"New allocated email identities quota {new_quota} is the same as the current allocated email identities quota for organization {organization_id}, no need to update parent organization's utilized email identities")

    except Exception as e:
        logging.error(f"Error updating organization allocated email identities quota: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update organization allocated email identities quota: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_organization(db_session: PgSession, organization_id: str) -> None:
    """
    Delete an organization and all its associated data including users, domains, mailboxes, etc.
    Also update the parent organization's quota accordingly
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    # Get the parent organization ID and current quota utilized
    row = await db_session.fetchrow(
        "SELECT parent_organization_id, quota_allocated, allocated_email_identities FROM organizations WHERE organization_id = $1",
        organization_id
    )
    if not row:
        raise All_Exceptions(
            message=f"Organization with ID {organization_id} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    parent_organization_id = str(row["parent_organization_id"])
    quota_allocated = float(row["quota_allocated"])
    allocated_email_identities = int(row["allocated_email_identities"])

    try:
        # Delete the organization and all its associated data (automatically cascaded)
        await db_session.execute(
            "DELETE FROM organizations WHERE organization_id = $1",
            organization_id
        )

        # Update the parent organization's quota
        await db_session.execute(
            """
            UPDATE organizations
            SET quota_utilized = quota_utilized - $1,
                utilized_email_identities = utilized_email_identities - $3
            WHERE organization_id = $2 AND is_active = TRUE
            """,
            quota_allocated,
            parent_organization_id,
            allocated_email_identities
        )

    except Exception as e:
        logging.error(f"Error deleting organization: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to delete organization: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_org_space_metrics(organization_id: str, db: PgSession) -> dict:
    """
    Get organization space metrics
    """
    try:
        row = await db.fetchrow(
            """
            SELECT quota_allocated, quota_utilized
            FROM organizations WHERE organization_id = $1
            """,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message=f"Organization with ID {organization_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "quota_allocated": float(row["quota_allocated"]),
            "quota_utilized": float(row["quota_utilized"])
        }

    except Exception as e:
        logging.error(f"Error fetching organization space metrics: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch organization space metrics: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_total_users_under_organization(organization_id: str, db: PgSession) -> int:
    """
    Get total users under the organization
    """
    try:
        row = await db.fetchrow(
            "SELECT COUNT(*) FROM users WHERE organization_id = $1",
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message=f"Organization with ID {organization_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return row["count"]

    except Exception as e:
        logging.error(f"Error fetching total users under organization: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch total users under organization: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def edit_organization_name(db_session: PgSession, organization_id: str, new_organization_name: str) -> None:
    """
    Edit organization name
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    # Check if the new organization name already exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_name=new_organization_name,
        raise_exception_if_exists=True,
        exception_message=f"Organization with name {new_organization_name} already exists"
    )

    try:
        await db_session.execute(
            """
            UPDATE organizations
            SET organization_name = $1
            WHERE organization_id = $2
            """,
            new_organization_name,
            organization_id
        )

    except Exception as e:
        logging.error(f"Error editing organization name: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to edit organization name: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_api_keys_by_organization(db_session: PgSession, organization_id: str, page: int, limit: int) -> dict:
    """
    Get API keys for a specific organization with pagination
    """
    if page < 1 or limit < 1 or limit > 50:
        raise All_Exceptions(
            message="Page and limit must be positive integers, and limit cannot exceed 50",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        total_count = await db_session.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE organization_id = $1",
            organization_id
        )
        if total_count == 0:
            return {"total_count": 0, "api_keys": [], "current_page": page, "total_pages": 0}

        offset = (page - 1) * limit
        rows = await db_session.fetch(
            """
            SELECT key_id, api_key, key_name, permissions, is_active, created_at, updated_at
            FROM api_keys
            WHERE organization_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            limit,
            offset
        )
        api_keys = [
            {
                "key_id": row["key_id"],
                "api_key": shorten_api_key(str(row["api_key"])),
                "key_name": row["key_name"],
                "permissions": row["permissions"],
                "is_active": row["is_active"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat()
            }
            for row in rows
        ]
        return {
            "api_keys": api_keys,
            "current_page": page,
            "total_pages": (total_count + limit - 1) // limit,
            "total_count": total_count
        }

    except Exception as e:
        logging.error(f"Error fetching API keys for organization: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch API keys for organization: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_api_key_details(db_session: PgSession, api_key_id: int, organization_id: str) -> dict:
    """
    Get API key details by API key and organization ID
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        row = await db_session.fetchrow(
            """
            SELECT key_id, api_key, key_name, permissions, details, is_active, created_at, updated_at
            FROM api_keys
            WHERE key_id = $1 AND organization_id = $2
            """,
            api_key_id,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message=f"API key {api_key_id} does not exist for organization ID {organization_id}",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "key_id": row["key_id"],
            "api_key": shorten_api_key(str(row["api_key"])),
            "key_name": row["key_name"],
            "permissions": row["permissions"],
            "details": orjson.loads(row["details"]),
            "is_active": row["is_active"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat()
        }
    
    except Exception as e:
        logging.error(f"Error fetching API key details: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch API key details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_api_key(db_session: PgSession, api_key_id: int, organization_id: str) -> None:
    """
    Delete an API key by API key and organization ID
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        result = await db_session.execute(
            "DELETE FROM api_keys WHERE key_id = $1 AND organization_id = $2",
            api_key_id,
            organization_id
        )
        if result == "DELETE 0":
            raise All_Exceptions(
                message=f"API key {api_key_id} does not exist for organization ID {organization_id}",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error deleting API key: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to delete API key: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_api_key_info(
    db_session: PgSession,
    api_key_id: int,
    organization_id: str,
    new_key_name: str,
    new_permissions: list[str],
    new_details: dict,
    is_active: bool
) -> None:
    """
    Update API key information
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        result = await db_session.execute(
            """
            UPDATE api_keys
            SET key_name = $1, permissions = $2, details = $3, is_active = $4
            WHERE key_id = $5 AND organization_id = $6
            """,
            new_key_name,
            new_permissions,
            orjson.dumps(new_details).decode("utf-8"),
            is_active,
            api_key_id,
            organization_id
        )
        if result == "UPDATE 0":
            raise All_Exceptions(
                message=f"API key {api_key_id} does not exist for organization ID {organization_id}",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error updating API key information: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update API key information: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_api_key(
    db_session: PgSession,
    organization_id: str,
    key_name: str,
    permissions: list[str],
    details: dict
) -> str:
    """
    Create a new API key for an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )
    # Generate a unique API key
    api_key = str(uuid.uuid4())

    try:
        await db_session.execute(
            """
            INSERT INTO api_keys (api_key, organization_id, key_name, permissions, details, is_active)
            VALUES ($1, $2, $3, $4, $5, TRUE)
            """,
            api_key,
            organization_id,
            key_name,
            permissions,
            orjson.dumps(details).decode("utf-8")
        )

        return api_key

    except Exception as e:
        logging.error(f"Error creating new API key: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create new API key: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_or_update_chat_config(
    db_session: PgSession,
    organization_id: str,
    enable_file_sharing: bool,
    file_size_limit_mb: int,
    enable_group_chat: bool,
    enable_direct_chat: bool
) -> None:
    """
    Create or update chat configuration for an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        # Check if the chat configuration already exists for the organization
        existing_config = await db_session.fetchrow(
            "SELECT 1 FROM chat_settings WHERE organization_id = $1",
            organization_id
        )

        if existing_config:
            # Update existing chat configuration
            await db_session.execute(
                """
                UPDATE chat_settings
                SET enable_file_sharing = $1,
                    file_size_limit_mb = $2,
                    enable_group_chat = $3,
                    enable_direct_chat = $4,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = $5
                """,
                enable_file_sharing,
                file_size_limit_mb,
                enable_group_chat,
                enable_direct_chat,
                organization_id
            )

        else:
            # Create new chat configuration
            await db_session.execute(
                """
                INSERT INTO chat_settings (organization_id, enable_file_sharing, file_size_limit_mb,
                enable_group_chat, enable_direct_chat, quota_allocated, quota_utilized)
                VALUES ($1, $2, $3, $4, $5, 0, 0)
                """,
                organization_id,
                enable_file_sharing,
                file_size_limit_mb,
                enable_group_chat,
                enable_direct_chat
            )

    except Exception as e:
        logging.error(f"Error creating/updating chat configuration: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create/update chat configuration: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_chat_quota(db_session: PgSession, organization_id: str, new_quota: float) -> None:
    """
    Update chat service quota for an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    # Check if the chat configuration exists for the organization
    existing_config = await db_session.fetchrow(
        "SELECT quota_allocated, quota_utilized FROM chat_settings WHERE organization_id = $1",
        organization_id
    )
    if not existing_config:
        raise All_Exceptions(
            message=f"Chat configuration for organization ID {organization_id} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    existing_quota_allocated = float(existing_config["quota_allocated"])
    existing_quota_utilized = float(existing_config["quota_utilized"])

    # Check if the new quota is less than the utilized quota
    if new_quota < existing_quota_utilized:
        raise All_Exceptions(
            message=f"New chat quota {new_quota} is less than the utilized quota {existing_quota_utilized} for organization ID {organization_id}",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if the new quota is the same as the current quota
    if new_quota == existing_quota_allocated:
        raise All_Exceptions(
            message=f"New chat quota {new_quota} is the same as the current quota for organization ID {organization_id}",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # See if the new quota is greater than the current quota, if yes then validate the new quota against the organization's quota
    if new_quota > existing_quota_allocated:
        await validate_organization_quota(
            db_session=db_session,
            organization_id=organization_id,
            required_storage_quota=new_quota - existing_quota_allocated,
            required_email_identities=-1
        )

    # Two cases now:
    # 1. If the user added more quota for chat service, then we need to increase the utilized quota for the organization
    # 2. If the user reduced the quota for chat service, then we need to decrease the utilized quota for the organization
    try:
        await db_session.execute(
            """
            UPDATE chat_settings
            SET quota_allocated = $1, updated_at = CURRENT_TIMESTAMP
            WHERE organization_id = $2
            """,
            new_quota,
            organization_id
        )

        if new_quota > existing_quota_allocated:
            await db_session.execute(
                """
                UPDATE organizations
                SET quota_utilized = quota_utilized + $1
                WHERE organization_id = $2
                """,
                new_quota - existing_quota_allocated,
                organization_id
            )
        elif new_quota < existing_quota_allocated:
            await db_session.execute(
                """
                UPDATE organizations
                SET quota_utilized = quota_utilized - $1
                WHERE organization_id = $2
                """,
                existing_quota_allocated - new_quota,
                organization_id
            )

    except Exception as e:
        logging.error(f"Error updating chat quota: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to update chat quota: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_chat_config_for_organization(db_session: PgSession, organization_id: str) -> dict:
    """
    Get chat configuration for an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        row = await db_session.fetchrow(
            """
            SELECT
                enable_file_sharing,
                file_size_limit_mb,
                enable_group_chat,
                enable_direct_chat,
                quota_allocated,
                quota_utilized,
                updated_at
            FROM chat_settings
            WHERE organization_id = $1
            """,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message=f"Chat configuration for organization ID {organization_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "organization_id": organization_id,
            "enable_file_sharing": row["enable_file_sharing"],
            "file_size_limit_mb": row["file_size_limit_mb"],
            "enable_group_chat": row["enable_group_chat"],
            "enable_direct_chat": row["enable_direct_chat"],
            "quota_allocated": float(row["quota_allocated"]),
            "quota_utilized": float(row["quota_utilized"]),
            "updated_at": row["updated_at"].isoformat()
        }

    except Exception as e:
        logging.error(f"Error fetching chat configuration: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch chat configuration: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def check_if_org_has_children_or_domains(db_session: PgSession, organization_id: str) -> dict:
    """
    Check if the organization has any child organizations or domains associated with it
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        # Check for child organizations
        child_org_count = await db_session.fetchval(
            "SELECT COUNT(*) FROM organizations WHERE parent_organization_id = $1",
            organization_id
        )

        # Check for associated domains
        domain_count = await db_session.fetchval(
            "SELECT COUNT(*) FROM domains WHERE managed_by = $1",
            organization_id
        )

        return {
            "has_child_organizations": child_org_count > 0,
            "has_associated_domains": domain_count > 0
        }

    except Exception as e:
        logging.error(f"Error checking for child organizations or domains: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to check for child organizations or domains: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_create_files_settings(
    db_session: PgSession,
    organization_id: str,
    enable_file_sharing: bool,
    enable_file_versioning: bool
) -> None:
    """
    Update or create file service settings for an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        # Check if the file service settings already exist for the organization
        existing_settings = await db_session.fetchrow(
            "SELECT 1 FROM file_settings WHERE organization_id = $1",
            organization_id
        )
        if existing_settings:
            # Update existing file service settings
            await db_session.execute(
                """
                UPDATE file_settings
                SET is_sharing_enabled = $1,
                    is_file_versioning_enabled = $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = $3
                """,
                enable_file_sharing,
                enable_file_versioning,
                organization_id
            )
        else:
            # Create new file service settings
            await db_session.execute(
                """
                INSERT INTO file_settings (organization_id, is_sharing_enabled, is_file_versioning_enabled)
                VALUES ($1, $2, $3)
                """,
                organization_id,
                enable_file_sharing,
                enable_file_versioning
            )

    except Exception as e:
        logging.error(f"Error creating/updating file service settings: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to create/update file service settings: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_file_settings_for_organization(db_session: PgSession, organization_id: str) -> dict:
    """
    Get file service settings for an organization
    """
    # Check if the organization exists
    await _raise_check_organization_exists(
        db_session=db_session,
        organization_id=organization_id,
        raise_exception_if_exists=False,
        exception_message=f"Organization with ID {organization_id} does not exist"
    )

    try:
        row = await db_session.fetchrow(
            """
            SELECT is_sharing_enabled, is_file_versioning_enabled, updated_at
            FROM file_settings
            WHERE organization_id = $1
            """,
            organization_id
        )
        if not row:
            raise All_Exceptions(
                message=f"File service settings for organization ID {organization_id} do not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "organization_id": organization_id,
            "is_sharing_enabled": row["is_sharing_enabled"],
            "is_file_versioning_enabled": row["is_file_versioning_enabled"],
            "updated_at": row["updated_at"].isoformat()
        }

    except Exception as e:
        logging.error(f"Error fetching file service settings: {e}", exc_info=True)
        raise All_Exceptions(
            message=f"Failed to fetch file service settings: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
