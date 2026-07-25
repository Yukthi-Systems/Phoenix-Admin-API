"""
Handles all the CRM Invoices related database operations
Tables: invoices, invoice_revisions
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

# -- Invoice for Organization
# CREATE TABLE invoices (
#     invoice_id VARCHAR(20) PRIMARY KEY,  -- e.g., '2025-26/001'
#     organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

#     invoice_date TIMESTAMP NOT NULL,  -- Date of the invoice
#     is_paid BOOLEAN DEFAULT FALSE NOT NULL,  -- Is the invoice paid

#     alerts JSONB NOT NULL,  -- metadata, not indexed will have alerts like Reminder setups, whome to send, etc.
#     due_date TIMESTAMP NOT NULL,  -- Due date for the invoice payment

#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
# );

# -- Revision Version of the Invoice (First invoice will be the first revision)
# CREATE TABLE invoice_revisions (
#     revision_id UUID PRIMARY KEY,
#     invoice_id VARCHAR(20) NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,

#     revision_number INT NOT NULL CHECK (revision_number > 0),  -- e.g., 1, 2, 3, etc.
#     revision_date TIMESTAMP NOT NULL,  -- Date of the revision
#     revision_details JSONB NOT NULL,  -- Details of the revision (e.g., changes, description, etc.)

#     invoice_details JSONB NOT NULL,  -- Full details of the invoice at this revision (e.g., items, amounts, etc.)

#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
#     UNIQUE (invoice_id, revision_number)  -- Unique constraint on invoice_id and revision_number
# );


async def create_new_invoice(
    db_session: PgSession,
    invoice_id: str,
    organization_id: str,
    invoice_date: datetime,
    is_paid: bool,
    alerts: dict,
    due_date: datetime
) -> None:
    """
    Create a new invoice in the database
    """
    # If the invoice_id already exists, raise an exception
    existing_invoice = await db_session.fetchval(
        """
        SELECT invoice_id FROM invoices WHERE invoice_id = $1
        """,
        invoice_id
    )
    if existing_invoice:
        raise All_Exceptions(
            message=f"Invoice with ID {invoice_id} already exists",
            status_code=status.HTTP_409_CONFLICT
        )

    try:
        # Insert the new invoice into the database
        await db_session.execute(
            """
            INSERT INTO invoices (invoice_id, organization_id, invoice_date, is_paid, alerts, due_date)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            invoice_id,
            uuid.UUID(organization_id),
            invoice_date,
            is_paid,
            orjson.dumps(alerts).decode("utf-8"),
            due_date
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create new invoice: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def create_invoice_revision(
    db_session: PgSession,
    invoice_id: str,
    revision_number: int,
    revision_date: datetime,
    revision_details: dict,
    invoice_details: dict
) -> str:
    """
    Create a new revision for an existing invoice
    """
    # If the invoice_id does not exist, raise an exception
    existing_invoice = await db_session.fetchval(
        """
        SELECT invoice_id FROM invoices WHERE invoice_id = $1
        """,
        invoice_id
    )
    if not existing_invoice:
        raise All_Exceptions(
            message=f"Invoice with ID {invoice_id} does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Generate a new revision ID
    revision_id = str(uuid.uuid4())

    try:
        # Insert the new revision into the database
        await db_session.execute(
            """
            INSERT INTO invoice_revisions (revision_id, invoice_id, revision_number, revision_date, revision_details, invoice_details)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            revision_id,
            invoice_id,
            revision_number,
            revision_date,
            orjson.dumps(revision_details).decode("utf-8"),
            orjson.dumps(invoice_details).decode("utf-8")
        )

        # Update the updated_at field of the invoice
        await db_session.execute(
            """
            UPDATE invoices
            SET updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = $1
            """,
            invoice_id
        )

        return revision_id

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to create invoice revision: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_latest_invoice_id(db_session: PgSession) -> str:
    """
    Get the latest invoice ID from the database
    """
    try:
        result = await db_session.fetchval(
            """
            SELECT invoice_id FROM invoices
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        return result if result else None

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch latest invoice ID: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_invoice_and_its_revisions(db_session: PgSession, invoice_id: str) -> dict:
    """
    Get an invoice and its revisions from the database
    """
    try:
        # Fetch the invoice details
        invoice = await db_session.fetchrow(
            """
            SELECT * FROM invoices WHERE invoice_id = $1
            """,
            invoice_id
        )
        if not invoice:
            raise All_Exceptions(
                message="Invoice not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Fetch the revisions for the invoice
        revisions = await db_session.fetch(
            """
            SELECT * FROM invoice_revisions WHERE invoice_id = $1 ORDER BY revision_number DESC
            """,
            invoice_id
        )

        return {
            "invoice": {
                "invoice_id": str(invoice["invoice_id"]),
                "organization_id": str(invoice["organization_id"]),
                "invoice_date": invoice["invoice_date"].isoformat(),
                "is_paid": invoice["is_paid"],
                "alerts": orjson.loads(invoice["alerts"]),
                "due_date": invoice["due_date"].isoformat(),
                "created_at": invoice["created_at"].isoformat(),
                "updated_at": invoice["updated_at"].isoformat()
            },
            "revisions": [
                {
                    "revision_id": str(revision["revision_id"]),
                    "revision_number": int(revision["revision_number"]),
                    "revision_date": revision["revision_date"].isoformat(),
                    "revision_details": orjson.loads(revision["revision_details"]),
                    "invoice_details": orjson.loads(revision["invoice_details"]),
                    "created_at": revision["created_at"].isoformat()
                } for revision in revisions
            ]
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch invoice and its revisions: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_all_invoices_for_organization(db_session: PgSession, search_query: str, organization_id: str, page: int = 1, page_size: int = 10) -> dict:
    """
    Get all invoices for a specific organization with pagination
    """
    try:
        offset = (page - 1) * page_size

        # Fetch the count of invoices for the organization
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM invoices WHERE organization_id = $1 AND invoice_id ILIKE $2
            """,
            organization_id,
            f"%{search_query}%"
        )
        if total_count is None:
            return {
                "total_count": 0,
                "invoices": [],
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # Fetch the invoices for the organization with pagination
        invoices = await db_session.fetch(
            """
            SELECT invoice_id, invoice_date, is_paid, due_date, created_at, updated_at
            FROM invoices
            WHERE organization_id = $1 AND invoice_id ILIKE $2
            ORDER BY invoice_date DESC
            LIMIT $3 OFFSET $4
            """,
            organization_id,
            f"%{search_query}%",
            page_size,
            offset
        )
        invoice_list = [
            {
                "invoice_id": str(invoice["invoice_id"]),
                "invoice_date": invoice["invoice_date"].isoformat(),
                "is_paid": invoice["is_paid"],
                "due_date": invoice["due_date"].isoformat(),
                "created_at": invoice["created_at"].isoformat(),
                "updated_at": invoice["updated_at"].isoformat()
            } for invoice in invoices
        ]

        return {
            "total_count": total_count,
            "invoices": invoice_list,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size  # Calculate total pages
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch invoices for organization: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def check_revision_exists(db_session: PgSession, revision_id: str) -> bool:
    """
    Check if a revision exists in the database
    """
    try:
        result = await db_session.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM invoice_revisions WHERE revision_id = $1)
            """,
            revision_id
        )
        return result if result else False

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to check if revision exists: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def initial_invoice_update_data(
    db_session: PgSession,
    invoice_id: str,
    alerts: dict,
    due_date: datetime,
    is_paid: bool
) -> None:
    """
    Update the initial invoice data in the database like alerts, due date, and is_paid status
    """
    try:
        # Update the invoice with the new data
        await db_session.execute(
            """
            UPDATE invoices
            SET alerts = $1, due_date = $2, is_paid = $3, updated_at = CURRENT_TIMESTAMP
            WHERE invoice_id = $4
            """,
            orjson.dumps(alerts).decode("utf-8"),
            due_date,
            is_paid,
            invoice_id
        )

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to update initial invoice data: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )


async def get_all_invoices_for_all_organization(db_session: PgSession, search_query: str, page: int = 1, page_size: int = 10) -> dict:
    """
    Get all invoices for all organizations with pagination
    """
    try:
        offset = (page - 1) * page_size

        # Fetch the count of all invoices
        total_count = await db_session.fetchval(
            """
            SELECT COUNT(*) FROM invoices WHERE invoice_id ILIKE $1
            """,
            f"%{search_query}%"
        )
        if total_count is None:
            return {
                "total_count": 0,
                "invoices": [],
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # Fetch the invoices with pagination
        invoices = await db_session.fetch(
            """
            SELECT invoice_id, organization_id, invoice_date, is_paid, due_date, created_at, updated_at
            FROM invoices
            WHERE invoice_id ILIKE $1
            ORDER BY invoice_date DESC
            LIMIT $2 OFFSET $3
            """,
            f"%{search_query}%",
            page_size,
            offset
        )
        invoice_list = [
            {
                "invoice_id": str(invoice["invoice_id"]),
                "organization_id": str(invoice["organization_id"]),
                "invoice_date": invoice["invoice_date"].isoformat(),
                "is_paid": invoice["is_paid"],
                "due_date": invoice["due_date"].isoformat(),
                "created_at": invoice["created_at"].isoformat(),
                "updated_at": invoice["updated_at"].isoformat()
            } for invoice in invoices
        ]

        return {
            "total_count": total_count,
            "invoices": invoice_list,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size  # Calculate total pages
        }

    except Exception as e:
        raise All_Exceptions(
            message=f"Failed to fetch invoices for all organizations: {e}",
            status_code=status.HTTP_424_FAILED_DEPENDENCY
        )
