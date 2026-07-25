"""
Handles all the CRM related database operations
Tables: purchase_orders, services, service_assignments are handled here
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


from src.utils.base.libraries import aiomcache, asyncpg, TypeAlias, datetime, status, uuid, orjson
from src.utils.models import All_Exceptions

PgSession: TypeAlias = asyncpg.Connection
MemCacheSession: TypeAlias = aiomcache.Client


async def create_new_service(
    db_session: PgSession,
    service_code: str,
    service_name: str,
    service_description: str,
    service_info: dict,
    is_active: bool = True
) -> None:
    """
    Create a new service in the database
    """
    try:
        # Insert the new service into the database
        await db_session.execute(
            """
            INSERT INTO services (service_code, service_name, service_description, service_info, is_active)
            VALUES ($1, $2, $3, $4, $5)
            """,
            service_code,
            service_name,
            service_description,
            orjson.dumps(service_info).decode("utf-8"),
            is_active
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new service: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_all_services(db_session: PgSession) -> list[dict]:
    """
    Retrieve all services from the database
    """
    try:
        # Fetch all services from the database
        rows = await db_session.fetch(
            """
            SELECT service_code, service_name, is_active
            FROM services
            """
        )
        
        return [
            {
                "service_code": row["service_code"],
                "service_name": row["service_name"],
                "is_active": row["is_active"]
            }
            for row in rows
        ]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve services: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_service_details(db_session: PgSession, service_code: str) -> dict:
    """
    Retrieve details of a specific service by its code
    """
    try:
        # Fetch the service details from the database
        row = await db_session.fetchrow(
            """
            SELECT service_code, service_name, service_description, service_info, is_active
            FROM services
            WHERE service_code = $1
            """,
            service_code
        )

        if not row:
            raise All_Exceptions(
                message="Service not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "service_code": row["service_code"],
            "service_name": row["service_name"],
            "service_description": row["service_description"],
            "service_info": orjson.loads(row["service_info"]),
            "is_active": row["is_active"]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve service details: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_service_info(
    db_session: PgSession,
    service_code: str,
    service_name: str,
    service_description: str,
    service_info: dict,
    is_active: bool
) -> None:
    """
    Update the details of an existing service
    """
    try:
        # Update the service details in the database
        await db_session.execute(
            """
            UPDATE services
            SET service_name = $1,
                service_description = $2,
                service_info = $3,
                is_active = $4
            WHERE service_code = $5
            """,
            service_name,
            service_description,
            orjson.dumps(service_info).decode("utf-8"),
            is_active,
            service_code
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update service: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_service(db_session: PgSession, service_code: str) -> None:
    """
    Delete a service from the database
    """
    try:
        # Delete the service from the database
        await db_session.execute(
            """
            DELETE FROM services
            WHERE service_code = $1
            """,
            service_code
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete service: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_purchase_order(
    db_session: PgSession,
    organization_id: str,
    po_name: str,
    po_description: str,
    po_status: str,
    po_date: datetime,
    total_amount: float,
    details: dict
) -> str:
    """
    Create a new purchase order in the database
    """
    po_id = str(uuid.uuid4())  # Generate a new UUID for the purchase order
    try:
        # Insert the new purchase order into the database
        await db_session.execute(
            """
            INSERT INTO purchase_orders (po_id, organization_id, po_name, po_description, po_status, po_date, total_amount, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            po_id,
            organization_id,
            po_name,
            po_description,
            po_status,
            po_date,
            total_amount,
            orjson.dumps(details).decode("utf-8")
        )

        return po_id

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create purchase order with ID {po_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_service_link(
    db_session: PgSession,
    po_id: str,
    service_code: str,
    organization_id: str,
    notes: str,
    service_details: dict
) -> str:
    """
    Create a new service assignment for a purchase order
    """
    assignment_id = str(uuid.uuid4())  # Generate a new UUID for the assignment
    try:
        # Insert the new service assignment into the database
        await db_session.execute(
            """
            INSERT INTO service_assignments (assignment_id, po_id, service_code, organization_id, notes, service_details)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            assignment_id,
            po_id,
            service_code,
            organization_id,
            notes,
            orjson.dumps(service_details).decode("utf-8")
        )

        return assignment_id

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create service link with ID {assignment_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_purchase_order_with_services(db_session: PgSession, po_id: str, organization_id: str) -> dict:
    """
    Retrieve a specific Purchase Order along with its assigned services
    """
    try:
        rows = await db_session.fetch(
            """
            SELECT 
                po.po_id, po.po_name, po.po_description, po.po_status,
                po.po_date, po.total_amount, po.details AS po_details,
                sa.assignment_id, sa.notes, sa.service_details,
                s.service_code, s.service_name, s.service_description, s.service_info
            FROM purchase_orders po
            LEFT JOIN service_assignments sa ON po.po_id = sa.po_id
            LEFT JOIN services s ON sa.service_code = s.service_code
            WHERE po.po_id = $1 AND po.organization_id = $2
            """,
            po_id,
            organization_id
        )

        if not rows:
            raise All_Exceptions(
                message="Purchase Order not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Take the first row for PO-level details
        first = rows[0]

        services = []
        for row in rows:
            if row["service_code"]:  # skip if no services assigned
                services.append({
                    "assignment_id": str(row["assignment_id"]),
                    "service_code": row["service_code"],
                    "service_name": row["service_name"],
                    "service_description": row["service_description"],
                    "service_info": orjson.loads(row["service_info"]),
                    "notes": row["notes"],
                    "service_details": orjson.loads(row["service_details"]),
                })

        return {
            "po_id": str(first["po_id"]),
            "po_name": first["po_name"],
            "po_description": first["po_description"],
            "po_status": first["po_status"],
            "po_date": first["po_date"].isoformat(),  # Convert to ISO format string
            "total_amount": float(first["total_amount"]),
            "details": orjson.loads(first["po_details"]),
            "services": services
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve purchase order and services: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_all_purchase_orders(db_session: PgSession, organization_id: str, page: int = 1, limit: int = 10) -> dict:
    """
    Retrieve all purchase orders for an organization with pagination
    """
    try:
        offset = (page - 1) * limit
        rows = await db_session.fetch(
            """
            SELECT po_id, po_name, po_status, po_date, total_amount
            FROM purchase_orders
            WHERE organization_id = $1
            ORDER BY po_date DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            limit,
            offset
        )

        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*)
            FROM purchase_orders
            WHERE organization_id = $1
            """,
            organization_id
        )

        return {
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit,  # Calculate total pages
            "has_next": (page * limit) < total_count,
            "has_prev": page > 1,
            "purchase_orders": [
                {
                    "po_id": str(row["po_id"]),
                    "po_name": row["po_name"],
                    "po_status": row["po_status"],
                    "po_date": row["po_date"].isoformat(),  # Convert to ISO format string
                    "total_amount": float(row["total_amount"])
                }
                for row in rows
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to retrieve purchase orders: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def export_purchase_orders(db_session: PgSession, organization_id: str, page: int, limit: int) -> list[dict]:
    """
    Export purchase orders for an organization with pagination
    """
    try:
        offset = (page - 1) * limit
        rows = await db_session.fetch(
            """
            SELECT po_id, po_name, po_description, po_status, po_date, total_amount, details
            FROM purchase_orders
            WHERE organization_id = $1
            ORDER BY po_date DESC
            LIMIT $2 OFFSET $3
            """,
            organization_id,
            limit,
            offset
        )

        return [
            {
                "po_id": str(row["po_id"]),
                "po_name": row["po_name"],
                "po_description": row["po_description"],
                "po_status": row["po_status"],
                "po_date": row["po_date"].isoformat(),  # Convert to ISO format string
                "total_amount": float(row["total_amount"]),
                "details": orjson.loads(row["details"])
            }
            for row in rows
        ]

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to export purchase orders: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_purchase_order(db_session: PgSession, po_id: str, organization_id: str) -> None:
    """
    Delete a purchase order from the database
    """
    try:
        # Delete the purchase order from the database
        await db_session.execute(
            """
            DELETE FROM purchase_orders
            WHERE po_id = $1 AND organization_id = $2
            """,
            po_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete purchase order with ID {po_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def delete_service_link(db_session: PgSession, assignment_id: str, organization_id: str, po_id: str) -> None:
    """
    Delete a service assignment from a purchase order
    """
    try:
        # Delete the service assignment from the database
        await db_session.execute(
            """
            DELETE FROM service_assignments
            WHERE assignment_id = $1 AND organization_id = $2 AND po_id = $3
            """,
            assignment_id,
            organization_id,
            po_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to delete service link with ID {assignment_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_service_link(
    db_session: PgSession,
    assignment_id: str,
    po_id: str,
    service_code: str,
    organization_id: str,
    notes: str,
    service_details: dict
) -> None:
    """
    Update an existing service assignment for a purchase order
    """
    try:
        # Update the service assignment in the database
        await db_session.execute(
            """
            UPDATE service_assignments
            SET service_code = $1, notes = $2, service_details = $3
            WHERE assignment_id = $4 AND organization_id = $5 AND po_id = $6
            """,
            service_code,
            notes,
            orjson.dumps(service_details).decode("utf-8"),
            assignment_id,
            organization_id,
            po_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update service link with ID {assignment_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def update_purchase_order(
    db_session: PgSession,
    po_id: str,
    organization_id: str,
    po_name: str,
    po_description: str,
    po_status: str,
    po_date: datetime,
    total_amount: float,
    details: dict
) -> None:
    """
    Update an existing purchase order in the database
    """
    try:
        # Update the purchase order in the database
        await db_session.execute(
            """
            UPDATE purchase_orders
            SET po_name = $1, po_description = $2, po_status = $3, po_date = $4, total_amount = $5, details = $6
            WHERE po_id = $7 AND organization_id = $8
            """,
            po_name,
            po_description,
            po_status,
            po_date,
            total_amount,
            orjson.dumps(details).decode("utf-8"),
            po_id,
            organization_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update purchase order with ID {po_id}: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
