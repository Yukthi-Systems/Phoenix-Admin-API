"""
This module provides Organization related API endpoints
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
    status
)
from src.main import CurrentUser, has_required_permissions, validate_permissions, put_s3_file, get_s3_file
from src.utils.models import CreateOrganizationForm, CreateAPIKeyForm, All_Exceptions
from src.database import (
    update_organization_activation_status,
    check_if_org_has_children_or_domains,
    update_organization_identity_quota,
    get_api_keys_by_organization,
    edit_organization_details,
    update_organization_quota,
    get_organization_details,
    create_new_organization,
    edit_organization_name,
    get_organizations_list,
    get_api_key_details,
    delete_organization,
    update_api_key_info,
    delete_api_key,
    create_api_key,
    PostgresDep
)


# Router
router = APIRouter()


# Create a new Organization
@router.post("/create", response_class=JSONResponse, tags=["Organization Management"], summary="Create a new Organization")
async def organization_create(data: CreateOrganizationForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new organization
    """
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["organization:create", "organization:view", "user:create"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to create a new organization"}
        )

    # Get current users organization details
    current_organization = await get_organization_details(
        db_session=PgDB,
        organization_id=user.organization_id
    )
    user_org_hierarchy_path: list[str] = current_organization["hierarchy_path"] # ["A", "B", "C"]

    # If current organization and parent organization are same, then no need to check for parent organization
    if user.organization_id != data.parent_organization_id:
        # Get the parent organization details
        requested_parent_organization = await get_organization_details(
            db_session=PgDB,
            organization_id=data.parent_organization_id
        )
        req_org_hierarchy_path: list[str] = requested_parent_organization["hierarchy_path"] # ["A", "B", "C", "D"] -> Success ; ["A", "B", "D"] -> Failure

        logic_check = req_org_hierarchy_path[:len(user_org_hierarchy_path)] == user_org_hierarchy_path and len(req_org_hierarchy_path) > len(user_org_hierarchy_path)
        if not logic_check:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Requested parent organization is not a child of current organization"}
            )
        user_org_hierarchy_path = req_org_hierarchy_path    # Update the hierarchy path to the requested parent organization

    # Check if the parent org has services enabled (If not enabled in parent org, then it cannot be enabled on child org)
    email_service_enabled = data.email_service_enabled if current_organization["email_service_enabled"] else False
    chat_service_enabled = data.chat_service_enabled if current_organization["chat_service_enabled"] else False
    file_service_enabled = data.file_service_enabled if current_organization["file_service_enabled"] else False

    # Create a new organization
    await create_new_organization(
        db_session=PgDB,
        organization_name=data.name,
        organization_info=data.details,
        is_active=data.activate,
        email_service_enabled=email_service_enabled,
        chat_service_enabled=chat_service_enabled,
        file_service_enabled=file_service_enabled,
        quota_allocated=data.allocated_quota,
        quota_utilized=0.0,
        allocated_email_identities=data.allocated_email_identities,
        utilized_email_identities=0,
        parent_organization_id=data.parent_organization_id,
        hierarchy_path=user_org_hierarchy_path
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Organization created successfully"}
    )


# Get Organization Details based on ID
@router.get("/details/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Get Organization Details")
async def organization_details(organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get organization details by ID
    """
    # Get requested organization details
    organization_details = await get_organization_details(
        db_session=PgDB,
        organization_id=organization_id
    )

    # We are checking if the requested organization is the same as the user's organization
    if organization_id == user.organization_id:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=organization_details
        )

    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["organization:view"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view organization details"}
        )

    # Validate organization_id (see if the user has access to the organization)
    # If the user is not requesting for their own organization
    # Check if they have access to the requested organization
    if user.organization_id not in organization_details["hierarchy_path"]:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to view this organization"}
        )

    if not organization_details:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Organization not found"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=organization_details
    )


@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Get All Organizations in Hierarchy Format")
async def organization_list_hierarchy(organization_id: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, limit: int = 10) -> JSONResponse:
    """
    Get all organizations in hierarchy format
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch all organizations in hierarchy format
    organizations_list = await get_organizations_list(
        db_session=PgDB,
        parent_organization_id=organization_id,
        page=page,
        limit=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=organizations_list
    )


# Edit Organization Information
@router.patch("/edit/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Edit Organization Information")
async def organization_edit(organization_id: str, organization_info: dict, email_service_enabled: bool, chat_service_enabled: bool, file_service_enabled: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit organization information
    """
    # If its user's own organization, then edit is not allowed
    if organization_id == user.organization_id:
        raise All_Exceptions(
            message="You cannot edit your own organization information, you can only edit child organizations information",
            status_code=status.HTTP_403_FORBIDDEN
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Get current users organization details
    current_organization = await get_organization_details(
        db_session=PgDB,
        organization_id=user.organization_id
    )

    # Check if the parent org has services enabled (If not enabled in parent org, then it cannot be enabled on child org)
    email_service_enabled = email_service_enabled if current_organization["email_service_enabled"] else False
    chat_service_enabled = chat_service_enabled if current_organization["chat_service_enabled"] else False
    file_service_enabled = file_service_enabled if current_organization["file_service_enabled"] else False

    # Update organization information
    await edit_organization_details(
        db_session=PgDB,
        organization_id=organization_id,
        organization_info=organization_info,
        email_service_enabled=email_service_enabled,
        chat_service_enabled=chat_service_enabled,
        file_service_enabled=file_service_enabled
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization information updated successfully"}
    )


# Edit Organization Name
@router.patch("/update/name/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Edit Organization Information")
async def organization_name_edit(organization_id: str, new_org_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit organization information
    """
    # If its user's own organization, then edit is not allowed
    if organization_id == user.organization_id:
        raise All_Exceptions(
            message="You cannot edit your own organization name, you can only edit child organizations name",
            status_code=status.HTTP_403_FORBIDDEN
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update organization information
    await edit_organization_name(
        db_session=PgDB,
        organization_id=organization_id,
        new_organization_name=new_org_name
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization information updated successfully"}
    )


# Enable/Disable Organization
@router.put("/activation/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Enable/Disable Organization")
async def organization_activation(organization_id: str, activate: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Enable or disable an organization
    """
    # If its user's own organization, then activation/deactivation is not allowed
    if organization_id == user.organization_id:
        raise All_Exceptions(
            message="You cannot activate/deactivate your own organization, you can only activate/deactivate child organizations",
            status_code=status.HTTP_403_FORBIDDEN
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update organization activation status
    await update_organization_activation_status(
        db_session=PgDB,
        organization_id=organization_id,
        is_active=activate
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Organization {'activated' if activate else 'deactivated'} successfully"}
    )


# Update Organization Identity Quota
@router.put("/quota/identity/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Update Organization Identity Quota")
async def organization_identity_quota_update(organization_id: str, new_allocated_quota: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update organization identity quota
    """
    # If its user's own organization, then quota update is not allowed
    if organization_id == user.organization_id:
        raise All_Exceptions(
            message="You cannot update quota for your own organization, you can only update quota for child organizations",
            status_code=status.HTTP_403_FORBIDDEN
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:edit", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update organization identity quota
    await update_organization_identity_quota(
        db_session=PgDB,
        organization_id=organization_id,
        new_quota=new_allocated_quota
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization identity quota updated successfully"}
    )


# Update Organization Storage Quota
@router.put("/quota/storage/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Update Organization Storage Quota")
async def organization_storage_quota_update(organization_id: str, new_allocated_quota: float, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update organization quota
    """
    # If its user's own organization, then quota update is not allowed
    if organization_id == user.organization_id:
        raise All_Exceptions(
            message="You cannot update quota for your own organization, you can only update quota for child organizations",
            status_code=status.HTTP_403_FORBIDDEN
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:edit", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update organization Storage quota
    await update_organization_quota(
        db_session=PgDB,
        organization_id=organization_id,
        new_quota=new_allocated_quota
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization storage quota updated successfully"}
    )


# Delete Organization
@router.delete("/delete/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Delete Organization")
async def organization_delete(organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an organization and all its associated data including users, domains, mailboxes, etc.
    """
    # If its user's own organization, then deletion is not allowed
    if organization_id == user.organization_id:
        raise All_Exceptions(
            message="You cannot delete your own organization, you can only delete child organizations",
            status_code=status.HTTP_403_FORBIDDEN
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["organization:delete", "organization:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Check if the organization has any child organizations
    # Check if the organization has any domains associated with it
    has_children_or_domains = await check_if_org_has_children_or_domains(
        db_session=PgDB,
        organization_id=organization_id
    )
    if has_children_or_domains["has_child_organizations"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Cannot delete organization with child organizations. Please delete child organizations first."}
        )
    if has_children_or_domains["has_associated_domains"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Cannot delete organization with associated domains. Please remove associated domains first."}
        )

    # Delete organization
    await delete_organization(
        db_session=PgDB,
        organization_id=organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization deleted successfully"}
    )


# Add Organization Logo
@router.put("/logo/{organization_id}", response_class=JSONResponse, tags=["Organization Management"], summary="Add Organization Logo")
async def organization_logo_upload(organization_id: str, file: UploadFile, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Generate a pre-signed URL for uploading an organization logo
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=[],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Accept only PNG files and of less than 5MB
    if file.content_type != "image/png":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Only PNG files are allowed"}
        )

    if file.size > 5 * 1024 * 1024:  # 5MB
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "File size exceeds 5MB limit"}
        )

    # File data
    file_data = await file.read()

    # Generate Pre-signed URL for S3 upload
    put_s3_file(
        file_name="organization_logo.png",
        file_type="image/png",
        file_content=file_data,
        organization_id=organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization logo uploaded successfully"}
    )


# Get Organization Logo
@router.get("/logo/{organization_id}", response_class=StreamingResponse, tags=["Organization Management"], summary="Get Organization Logo")
async def organization_logo_get(organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> StreamingResponse:
    """
    Generate a pre-signed URL for downloading an organization logo
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=[],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Download the organization logo from S3
    file_data: bytes = get_s3_file(
        file_name="organization_logo.png",
        organization_id=organization_id
    )

    return StreamingResponse(
        content=BytesIO(file_data),
        media_type="image/png",
        status_code=status.HTTP_200_OK,
        headers={"Content-Disposition": f"attachment; filename={organization_id}_logo.png"}
    )


# Get API Keys for an Organization
@router.get("/api-keys/{organization_id}", response_class=JSONResponse, tags=["API Key Management"], summary="Get API Keys for an Organization")
async def organization_api_keys_list(organization_id: str, user: CurrentUser, page: int, limit: int, PgDB: PostgresDep) -> JSONResponse:
    """
    Get API Keys for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["api_keys:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch API Keys for the organization
    api_keys_list = await get_api_keys_by_organization(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        limit=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=api_keys_list
    )


# Get one API Key details for an Organization
@router.get("/api-key/{organization_id}/{api_key_id}", response_class=JSONResponse, tags=["API Key Management"], summary="Get API Key Details for an Organization")
async def organization_api_key_details(organization_id: str, api_key_id: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get one API Key details for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["api_keys:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch API Key details
    api_key_details = await get_api_key_details(
        db_session=PgDB,
        organization_id=organization_id,
        api_key_id=api_key_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=api_key_details
    )


# Delete API Key for an Organization
@router.delete("/api-key/{organization_id}/{api_key_id}", response_class=JSONResponse, tags=["API Key Management"], summary="Delete API Key for an Organization")
async def organization_api_key_delete(organization_id: str, api_key_id: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an API Key for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["api_keys:delete", "api_keys:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Delete API Key
    await delete_api_key(
        db_session=PgDB,
        organization_id=organization_id,
        api_key_id=api_key_id
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "API Key deleted successfully"}
    )


# Create API Key for an Organization
@router.post("/api-key/{organization_id}", response_class=JSONResponse, tags=["API Key Management"], summary="Create API Key for an Organization")
async def organization_api_key_create(organization_id: str, data: CreateAPIKeyForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create an API Key for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["api_keys:create", "api_keys:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Create API Key
    new_api_key = await create_api_key(
        db_session=PgDB,
        organization_id=organization_id,
        key_name=data.key_name,
        permissions=data.permissions,
        details=data.details
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "API Key created successfully", "api_key": new_api_key}
    )


# Edit API Key for an Organization
@router.patch("/api-key/{organization_id}/{api_key_id}/{activate}", response_class=JSONResponse, tags=["API Key Management"], summary="Edit API Key for an Organization")
async def organization_api_key_edit(organization_id: str, api_key_id: int, activate: bool, data: CreateAPIKeyForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit an API Key for an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["api_keys:edit", "api_keys:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update API Key information
    await update_api_key_info(
        db_session=PgDB,
        organization_id=organization_id,
        api_key_id=api_key_id,
        new_key_name=data.key_name,
        new_permissions=data.permissions,
        new_details=data.details,
        is_active=activate
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "API Key updated successfully"}
    )
