"""
This module provides CRM related API endpoints
Note: CRM is a separate entity from the main application and is used to manage basically core features
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


from src.main import CurrentUser, validate_permissions, put_s3_file, get_s3_file
from src.utils.base.libraries import JSONResponse, APIRouter, status, UploadFile, StreamingResponse, BytesIO
from src.utils.models import CreateCRMService, CreatePurchaseOrder, CreatePOServiceLink, CreateInvoice, CreateRevisedInvoice
from src.database import (
    get_all_invoices_for_all_organization,
    get_all_invoices_for_organization,
    get_purchase_order_with_services,
    get_invoice_and_its_revisions,
    initial_invoice_update_data,
    get_all_purchase_orders,
    create_invoice_revision,
    export_purchase_orders,
    get_latest_invoice_id,
    check_revision_exists,
    create_purchase_order,
    delete_purchase_order,
    update_purchase_order,
    get_service_details,
    update_service_info,
    create_service_link,
    delete_service_link,
    update_service_link,
    create_new_invoice,
    create_new_service,
    get_all_services,
    delete_service,
    PostgresDep
)

# Router
router = APIRouter()


@router.post("/service", response_class=JSONResponse, tags=["CRM Service"], description="Create a new service")
async def create_crm_service(data: CreateCRMService, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new service in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:service:create", "crm:service:view"],
        organization_level_permissions=None,
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new service entry in the database
    await create_new_service(
        db_session=PgDB,
        service_code=data.code,
        service_name=data.name,
        service_description=data.description,
        service_info=data.info,
        is_active=data.activate
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Service created successfully", "service_name": data.name}
    )


@router.get("/services", response_class=JSONResponse, tags=["CRM Service"], description="Get all services")
async def get_all_crm_services(user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all services in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:service:view"],
        organization_level_permissions=None,
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all services from the database
    services = await get_all_services(db_session=PgDB)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Services fetched successfully", "services": services, "count": len(services) if services else 0}
    )


@router.get("/service/{service_code}", response_class=JSONResponse, tags=["CRM Service"], description="Get service details")
async def get_crm_service_details(service_code: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific service in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:service:view"],
        organization_level_permissions=None,
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch service details from the database
    service_details = await get_service_details(db_session=PgDB, service_code=service_code)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Service details fetched successfully", "data": service_details}
    )


@router.put("/service/{service_code}", response_class=JSONResponse, tags=["CRM Service"], description="Update service details")
async def update_crm_service_details(service_code: str, data: CreateCRMService, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update details of a specific service in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:service:edit", "crm:service:view"],
        organization_level_permissions=None,
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Update service details in the database
    await update_service_info(
        db_session=PgDB,
        service_code=service_code,
        service_name=data.name,
        service_description=data.description,
        service_info=data.info,
        is_active=data.activate
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Service updated successfully", "service_name": data.name}
    )


@router.delete("/service/{service_code}", response_class=JSONResponse, tags=["CRM Service"], description="Delete a service")
async def delete_crm_service(service_code: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a specific service in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:service:delete", "crm:service:view"],
        organization_level_permissions=None,
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the service from the database
    await delete_service(db_session=PgDB, service_code=service_code)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Service deleted successfully"}
    )


@router.post("/purchase-order", response_class=JSONResponse, tags=["Purchase Order"], description="Create a new purchase order")
async def create_purchase_order_endpoint(data: CreatePurchaseOrder, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new purchase order in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:create", "crm:purchase_order:view", "organization:view"],
        organization_level_permissions=["organization:edit", "organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new purchase order entry in the database
    purchase_order = await create_purchase_order(
        db_session=PgDB,
        organization_id=data.associated_organization_id,
        po_name=data.name,
        po_description=data.description,
        po_status=data.status,
        po_date=data.date,
        total_amount=data.total_amount,
        details=data.details
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Purchase order created successfully", "po_id": purchase_order}
    )


@router.post("/link/{organization_id}/{po_id}/{service_code}", response_class=JSONResponse, tags=["Purchase Order", "CRM Service"], description="Link a service to a purchase order")
async def link_service_to_purchase_order(organization_id: str, po_id: str, service_code: str, data: CreatePOServiceLink, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Link a service to a purchase order in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:edit", "crm:purchase_order:view", "crm:service:view"],
        organization_level_permissions=["organization:edit", "organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new service link entry in the database
    assignment_id = await create_service_link(
        db_session=PgDB,
        po_id=po_id,
        service_code=service_code,
        organization_id=organization_id,
        notes=data.notes,
        service_details=data.details
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Service linked to purchase order successfully", "assignment_id": assignment_id, "po_id": po_id, "service_code": service_code}
    )


@router.get("/purchase-order/{organization_id}/{po_id}", response_class=JSONResponse, tags=["Purchase Order"], description="Get purchase order details along with linked services")
async def get_purchase_order_details(organization_id: str, po_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific purchase order along with linked services in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:view", "crm:service:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch purchase order details along with linked services from the database
    purchase_order = await get_purchase_order_with_services(
        db_session=PgDB,
        po_id=po_id,
        organization_id=organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Purchase order details fetched successfully", "data": purchase_order}
    )


@router.get("/purchase-orders/{organization_id}/{page}/{limit}", response_class=JSONResponse, tags=["Purchase Order"], description="Get all purchase orders for an organization")
async def get_purchase_orders(organization_id: str, page: int, limit: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all purchase orders for a specific organization in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:view", "organization:view", "crm:service:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all purchase orders for the organization from the database
    purchase_orders = await get_all_purchase_orders(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        limit=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Purchase orders fetched successfully", "data": purchase_orders}
    )


@router.get("/export/purchase-orders/{organization_id}/{page}/{limit}", response_class=JSONResponse, tags=["Purchase Order"], description="Export all purchase orders for an organization")
async def export_all_purchase_orders(organization_id: str, page: int, limit: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Export all purchase orders for a specific organization in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:view", "organization:view", "crm:service:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all purchase orders for the organization from the database
    purchase_orders = await export_purchase_orders(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        limit=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Purchase orders fetched successfully", "data": purchase_orders}
    )


@router.delete("/purchase-order/{organization_id}/{po_id}", response_class=JSONResponse, tags=["Purchase Order"], description="Delete a purchase order")
async def delete_purchase_order_along_with_links(organization_id: str, po_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a specific purchase order in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:delete", "crm:purchase_order:view", "crm:service:delete", "crm:service:view"],
        organization_level_permissions=["organization:edit", "organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the purchase order from the database
    await delete_purchase_order(db_session=PgDB, po_id=po_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Purchase order deleted successfully"}
    )


@router.delete("/link/{organization_id}/{po_id}/{assignment_id}", response_class=JSONResponse, tags=["Purchase Order", "CRM Service"], description="Delete a service link from a purchase order")
async def delete_service_link_from_purchase_order(organization_id: str, po_id: str, assignment_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a service link from a purchase order in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:edit", "crm:purchase_order:view", "crm:purchase_order:delete", "crm:service:view", "organization:view"],
        organization_level_permissions=["organization:edit", "organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete the service link from the database
    await delete_service_link(
        db_session=PgDB,
        assignment_id=assignment_id,
        po_id=po_id,
        organization_id=organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Service link deleted successfully"}
    )


@router.put("/link/{organization_id}/{po_id}/{service_code}/{assignment_id}", response_class=JSONResponse, tags=["Purchase Order", "CRM Service"], description="Update a service link in a purchase order")
async def update_service_link_in_purchase_order(organization_id: str, po_id: str, service_code: str, assignment_id: str, data: CreatePOServiceLink, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update a service link in a purchase order in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:edit", "crm:purchase_order:view", "crm:service:edit", "crm:service:view", "organization:view"],
        organization_level_permissions=["organization:edit", "organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the service link in the database
    await update_service_link(
        db_session=PgDB,
        assignment_id=assignment_id,
        po_id=po_id,
        organization_id=organization_id,
        service_code=service_code,
        notes=data.notes,
        service_details=data.details
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Service link updated successfully", "assignment_id": assignment_id}
    )


@router.put("/purchase-order/{po_id}", response_class=JSONResponse, tags=["Purchase Order"], description="Update a purchase order")
async def update_purchase_order_endpoint(po_id: str, data: CreatePurchaseOrder, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update a specific purchase order in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:purchase_order:edit", "crm:purchase_order:view", "organization:view", "crm:service:view"],
        organization_level_permissions=["organization:edit", "organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.associated_organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the purchase order in the database
    await update_purchase_order(
        db_session=PgDB,
        po_id=po_id,
        organization_id=data.associated_organization_id,
        po_name=data.name,
        po_description=data.description,
        po_status=data.status,
        po_date=data.date,
        total_amount=data.total_amount,
        details=data.details
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Purchase order updated successfully", "po_id": po_id, "po_name": data.name}
    )


@router.post("/invoice/initial/{organization_id}", response_class=JSONResponse, tags=["Invoice"], description="Create a new invoice")
async def create_new_initial_invoice(
    organization_id: str,
    initial_data: CreateInvoice,
    invoice_data: CreateRevisedInvoice,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Create a new invoice in the CRM (First time creation)
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:create", "crm:invoice:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new invoice entry in the database
    await create_new_invoice(
        db_session=PgDB,
        invoice_id=initial_data.invoice_id,
        organization_id=organization_id,
        invoice_date=initial_data.invoice_date,
        is_paid=initial_data.is_paid,
        alerts=initial_data.alerts,
        due_date=initial_data.due_date
    )

    # Create a new invoice revision entry in the database (First revision)
    revision_id = await create_invoice_revision(
        db_session=PgDB,
        invoice_id=initial_data.invoice_id,
        revision_number=1,
        revision_date=initial_data.invoice_date,
        revision_details=invoice_data.basic_details,
        invoice_details=invoice_data.invoice_details
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "New Invoice created successfully", "invoice_id": initial_data.invoice_id, "revision_id": revision_id}
    )


@router.put("/invoice/revision/{organization_id}", response_class=JSONResponse, tags=["Invoice"], description="Create a new invoice revision")
async def create_invoice_revision_endpoint(organization_id: str, revision_data: CreateRevisedInvoice, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new revision for an existing invoice in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:edit", "crm:invoice:view", "crm:invoice:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Create a new invoice revision entry in the database
    revision_id = await create_invoice_revision(
        db_session=PgDB,
        invoice_id=revision_data.invoice_id,
        revision_number=revision_data.revision_number,
        revision_date=revision_data.revision_date,
        revision_details=revision_data.basic_details,
        invoice_details=revision_data.invoice_details
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Invoice revision created successfully", "invoice_id": revision_data.invoice_id, "revision_id": revision_id}
    )


@router.get("/invoice/list/{organization_id}", response_class=JSONResponse, tags=["Invoice"], description="Get all invoices for an organization")
async def get_all_invoices_for_organization_endpoint(organization_id: str, query: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all invoices for a specific organization in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:view", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all invoices for the organization from the database
    invoices = await get_all_invoices_for_organization(
        db_session=PgDB,
        organization_id=organization_id,
        search_query=query,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Invoices fetched successfully", "data": invoices, "count": len(invoices) if invoices else 0}
    )


@router.get("/invoice/fetch/{organization_id}", response_class=JSONResponse, tags=["Invoice"], description="Get invoice and its revisions")
async def get_invoice_and_revisions_endpoint(organization_id: str, invoice_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get a specific invoice and its revisions in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:view", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the invoice and its revisions from the database
    invoice_and_revisions = await get_invoice_and_its_revisions(
        db_session=PgDB,
        invoice_id=invoice_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Invoice and its revisions fetched successfully",
            "data": invoice_and_revisions
        }
    )


@router.get("/invoice/latest-id", response_class=JSONResponse, tags=["Invoice"], description="Get the latest invoice ID")
async def get_latest_invoice_id_endpoint(user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get the latest invoice ID in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:create", "crm:invoice:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the latest invoice ID from the database
    latest_invoice_id = await get_latest_invoice_id(db_session=PgDB)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Latest invoice ID fetched successfully",
            "latest_invoice_id": latest_invoice_id
        }
    )


@router.get("/invoice/download/{organization_id}/{revision_id}", response_class=JSONResponse, tags=["Invoice"], description="Download an invoice revision")
async def download_invoice_revision(organization_id: str, revision_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Download a specific invoice revision in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:view", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the invoice file from S3
    file_data: bytes = get_s3_file(
        file_name=f"invoices/{revision_id}.pdf",
        organization_id=organization_id
    )

    return StreamingResponse(
        content=BytesIO(file_data),
        media_type="application/pdf",
        status_code=status.HTTP_200_OK,
        headers={"Content-Disposition": f"attachment; filename=invoice_{revision_id}.pdf"}
    )


@router.post("/invoice/upload/{organization_id}/{revision_id}", response_class=JSONResponse, tags=["Invoice"], description="Upload a new invoice revision")
async def upload_invoice_revision(organization_id: str, revision_id: str, invoice: UploadFile, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Upload a new invoice revision in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:edit", "crm:invoice:view", "crm:invoice:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Validate the invoice file
    if not invoice or invoice.content_type != "application/pdf":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid invoice file. Please upload a PDF file."}
        )

    # File Content
    file_content = await invoice.read()

    # Check if the revision ID exists or not (Upload only if it exists)
    revision_id_exists = await check_revision_exists(db_session=PgDB, revision_id=revision_id)
    if not revision_id_exists:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Revision ID does not exist. Please create a revision first."}
        )

    # Upload the revised invoice file to the S3
    put_s3_file(
        file_name=f"invoices/{revision_id}.pdf",
        file_content=file_content,
        file_type="application/pdf",
        organization_id=organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Invoice revision uploaded successfully", "revision_id": revision_id}
    )


@router.patch("/invoice/initial/{organization_id}", response_class=JSONResponse, tags=["Invoice"], description="Update an initial invoice, like alerts and due date")
async def update_initial_invoice(
    organization_id: str,
    initial_data: CreateInvoice,
    user: CurrentUser,
    PgDB: PostgresDep
) -> JSONResponse:
    """
    Update an initial invoice in the CRM (like alerts and due date)
    Note: Only updates the is_paid, alerts, and due_date fields of the initial invoice
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:edit", "crm:invoice:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the initial invoice entry in the database
    await initial_invoice_update_data(
        db_session=PgDB,
        invoice_id=initial_data.invoice_id,
        is_paid=initial_data.is_paid,
        alerts=initial_data.alerts,
        due_date=initial_data.due_date
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Initial Invoice updated successfully", "invoice_id": initial_data.invoice_id}
    )


@router.get("/invoice/list-all", response_class=JSONResponse, tags=["Invoice"], description="Get all invoices irrespective of organization")
async def get_all_invoices_for_all_organization_endpoint(query: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get all invoices for all organizations in the CRM
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["crm:invoice:view", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=user.organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all invoices for all organizations from the database
    invoices = await get_all_invoices_for_all_organization(
        db_session=PgDB,
        search_query=query,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Invoices fetched successfully", "data": invoices, "count": len(invoices) if invoices else 0}
    )
