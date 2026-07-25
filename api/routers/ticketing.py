"""
This module provides Ticketing related API endpoints
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


from src.utils.base.libraries import (
    StreamingResponse,
    JSONResponse,
    UploadFile,
    APIRouter,
    BytesIO,
    status,
    uuid
)
from src.main import (
    has_required_permissions,
    validate_permissions,
    delete_s3_file,
    get_s3_file,
    put_s3_file,
    CurrentUser
)
from src.database import (
    admin_fetch_all_support_tickets,
    fetch_support_ticket_by_id,
    create_new_support_ticket,
    fetch_all_support_tickets,
    admin_update_ticket_info,
    fetch_ticket_follow_ups,
    add_follow_up_to_ticket,
    delete_support_ticket,
    PostgresDep
)
from src.utils.models import CreateSupportTicketForm, AdminFilterSupportTicketsForm

# Router
router = APIRouter()


# Upload a file for ticket (Any authenticated user)
@router.put("/file/upload", response_class=JSONResponse, tags=["Tickets"], summary="Upload a File for Ticket")
async def upload_ticket_file(file: UploadFile, _: CurrentUser) -> JSONResponse:
    """
    Upload a file for ticket (Any authenticated user)
    """
    # Basic validation, check if user has permission to create support tickets any of the roles can create
    if not (has_required_permissions(user_permissions=_.permissions, required_permissions=["support_ticket:create"]) or
            has_required_permissions(user_permissions=_.permissions, required_permissions=["support_admin:create"])):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to create support tickets"}
        )

    # Accept only PNG files and of less than 5MB
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg", "application/pdf", "text/plain", "application/zip"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Only PNG, JPEG, JPG, PDF, TXT, and ZIP files are allowed"}
        )

    if file.size > 10 * 1024 * 1024:  # 10MB limit
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "File size exceeds 10MB limit"}
        )

    # File data
    file_data = await file.read()
    file_id = str(uuid.uuid4())

    # Upload the ticket file to S3
    put_s3_file(
        file_name=file_id,
        file_type=file.content_type,
        file_content=file_data,
        organization_id="ticket_files"
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Ticket file uploaded successfully",
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": file.size,
            "file_id": file_id
        }
    )


# Get a file for ticket
@router.get("/file/{file_id}", response_class=JSONResponse, tags=["Tickets"], summary="Get a File for Ticket by File ID")
async def get_ticket_file(file_id: str, user: CurrentUser) -> JSONResponse:
    """
    Get a file for ticket by file ID
    """
    # Basic permission checks
    if not (has_required_permissions(user_permissions=user.permissions, required_permissions=["support_ticket:view"]) or
            has_required_permissions(user_permissions=user.permissions, required_permissions=["support_admin:view"])):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view support tickets"}
        )

    # Download the ticket file from S3
    file_data: bytes = get_s3_file(
        file_name=file_id,
        organization_id="ticket_files"
    )

    return StreamingResponse(
        content=BytesIO(file_data),
        media_type="application/octet-stream",
        status_code=status.HTTP_200_OK,
        headers={"Content-Disposition": f"attachment; filename={file_id}"}
    )


# Delete a file for ticket (Ticket Admins only)
@router.delete("/file/{file_id}", response_class=JSONResponse, tags=["Tickets"], summary="Delete a File for Ticket by File ID")
async def delete_ticket_file(file_id: str, user: CurrentUser) -> JSONResponse:
    """
    Delete a file for ticket by file ID (Ticket Admins only)
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["support_admin:delete"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to delete support ticket files"}
        )

    # Delete the ticket file from S3
    delete_s3_file(
        file_name=file_id,
        organization_id="ticket_files"
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Ticket file deleted successfully",
            "file_id": file_id
        }
    )


# Create a support ticket
@router.post("/ticket", response_class=JSONResponse, tags=["Tickets"], summary="Create a Support Ticket")
async def create_support_ticket(data: CreateSupportTicketForm, user: CurrentUser, db: PostgresDep) -> JSONResponse:
    """
    Create a support ticket
    """
    # Basic permission checks
    if not (has_required_permissions(user_permissions=user.permissions, required_permissions=["support_ticket:create"]) or
            has_required_permissions(user_permissions=user.permissions, required_permissions=["support_admin:create"])):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to create support tickets"}
        )

    # Create the support ticket
    await create_new_support_ticket(
        db_session=db,
        organization_id=user.organization_id,
        ticket_title=data.title,
        ticket_description=data.description,
        details=data.details,
        created_by=user.user_name
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Support ticket created successfully"}
    )


# Do a ticket follow-up
@router.post("/follow-up/{organization_id}/{ticket_id}", response_class=JSONResponse, tags=["Tickets"], summary="Add a Follow-Up to a Support Ticket")
async def add_ticket_follow_up(organization_id: str, ticket_id: int, data: dict, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Add a follow-up to a support ticket
    """
    # Basic permission checks
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["support_ticket:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user.user_id,
        db=PgDB
    )

    # Add the follow-up to the support ticket
    await add_follow_up_to_ticket(
        db_session=PgDB,
        ticket_id=ticket_id,
        organization_id=organization_id,
        follow_up_text=data["message"],
        details=data["details"],
        created_by=user.user_name
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Follow-up added to support ticket successfully"}
    )


# List all of the support tickets
@router.get("/tickets/{organization_id}", response_class=JSONResponse, tags=["Tickets"], summary="List All Support Tickets")
async def list_support_tickets(organization_id: str, page: int, page_size: int, user: CurrentUser, db: PostgresDep, query: str = "") -> JSONResponse:
    """
    List all of the support tickets
    """
    # Basic permission checks
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["support_ticket:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user.user_id,
        db=db
    )

    # Fetch the support tickets from the database
    tickets = await fetch_all_support_tickets(
        db_session=db,
        organization_id=organization_id,
        page=page,
        page_size=page_size,
        query=query
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Support tickets fetched successfully",
            "data": tickets
        }
    )


# Get ticket by ID and organization
@router.get("/ticket/{organization_id}/{ticket_id}", response_class=JSONResponse, tags=["Tickets"], summary="Get Support Ticket by ID and Organization")
async def get_support_ticket_by_id(organization_id: str, ticket_id: int, user: CurrentUser, db: PostgresDep) -> JSONResponse:
    """
    Get a support ticket by ID and organization
    """
    # Basic permission checks
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["support_ticket:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user.user_id,
        db=db
    )

    # Fetch the support ticket from the database
    ticket = await fetch_support_ticket_by_id(
        db_session=db,
        organization_id=organization_id,
        ticket_id=ticket_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Support ticket fetched successfully",
            "data": ticket
        }
    )


# List all of the ticket follow-ups
@router.get("/follow-ups/{organization_id}/{ticket_id}", response_class=JSONResponse, tags=["Tickets"], summary="List All Follow-Ups for a Support Ticket")
async def list_ticket_follow_ups(organization_id: str, ticket_id: int, page: int, page_size: int, user: CurrentUser, db: PostgresDep) -> JSONResponse:
    """
    List all of the ticket follow-ups
    """
    # Basic permission checks
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["support_ticket:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user.user_id,
        db=db
    )

    # Fetch the ticket follow-ups from the database
    follow_ups = await fetch_ticket_follow_ups(
        db_session=db,
        organization_id=organization_id,
        ticket_id=ticket_id,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Ticket follow-ups fetched successfully",
            "data": follow_ups
        }
    )


# List Admin Support Tickets
@router.post("/admin/tickets/fetch", response_class=JSONResponse, tags=["Tickets"], summary="List Admin Support Tickets")
async def list_admin_support_tickets(data: AdminFilterSupportTicketsForm, page: int, page_size: int, user: CurrentUser, db: PostgresDep) -> JSONResponse:
    """
    List Admin Support Tickets
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["support_admin:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view admin support tickets"}
        )

    # Fetch the admin support tickets from the database
    tickets = await admin_fetch_all_support_tickets(
        db_session=db,
        organization_id=data.organization_id,
        ticket_status=data.ticket_status,
        ticket_id=data.ticket_id,
        title_search=data.title_search,
        created_by=data.created_by,
        assigned_to=data.assigned_to,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Admin support tickets fetched successfully",
            "data": tickets
        }
    )


# Update Support Ticket Status
@router.patch("/admin/ticket/{organization_id}/{ticket_id}", response_class=JSONResponse, tags=["Tickets"], summary="Update Support Ticket Status")
async def update_support_ticket_status(organization_id: str, ticket_id: int, data: dict, user: CurrentUser, db: PostgresDep) -> JSONResponse:
    """
    Update Support Ticket Status
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["support_admin:edit"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to update support ticket status"}
        )

    # Update the support ticket status in the database
    await admin_update_ticket_info(
        db_session=db,
        ticket_id=ticket_id,
        organization_id=organization_id,
        ticket_status=data["ticket_status"],
        assigned_to=data["assigned_to"]
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Support ticket status updated successfully"}
    )


# Delete a Support Ticket and its Follow-Ups
@router.delete("/admin/ticket/{organization_id}/{ticket_id}", response_class=JSONResponse, tags=["Tickets"], summary="Delete a Support Ticket and its Follow-Ups")
async def admin_delete_support_ticket(organization_id: str, ticket_id: int, user: CurrentUser, db: PostgresDep) -> JSONResponse:
    """
    Delete a Support Ticket and its Follow-Ups
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["support_admin:delete"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to delete support tickets"}
        )

    # Delete the support ticket and its follow-ups from the database
    await delete_support_ticket(
        db_session=db,
        organization_id=organization_id,
        ticket_id=ticket_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Support ticket and its follow-ups deleted successfully"}
    )
