"""
This module provides Domain related API endpoints
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
    JSONResponse,
    APIRouter,
    status
)
from src.main import CurrentUser, validate_permissions, fetch_dns_records, new_domain_creation, delete_domain_process, generate_dns_txt_verification_key, validate_dns_txt_verification_key
from src.utils.models import CreateDomainForm, PatchDomainForm
from src.database import (
    check_if_domain_has_associated_identities,
    update_domain_txt_verification_status,
    migrate_domain_to_new_organization,
    update_domain_activation_status,
    get_all_domains_by_organization,
    delete_domain_and_update_quota,
    update_domain_info,
    get_domain_details,
    create_new_domain,
    PostgresDep
)


# Router
router = APIRouter()


# Create a new Domain
@router.post("/create", response_class=JSONResponse, tags=["Domain Management"], summary="Create a new Domain")
async def domain_create(data: CreateDomainForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:create", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    if data.enable_catch_all:
        if data.catch_all_forwarding_address is None or data.catch_all_forwarding_address.strip() == "":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Catch-all forwarding address is required when catch-all is enabled"}
            )

    if data.enable_hybrid_mode:
        if data.hybrid_connector_properties is None or not data.hybrid_connector_properties:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Hybrid connector properties are required when hybrid mode is enabled"}
            )

    # Create a 32-character random string for DNS TXT verification key
    dns_txt_verification_key: str = generate_dns_txt_verification_key()

    # Create a new domain
    await create_new_domain(
        db_session=PgDB,
        domain_name=data.domain_name.strip().lower(),
        organization_id=data.organization_id,
        is_active=data.activate,
        details=data.details,
        anti_phishing_secret_code=data.anti_phishing_secret_code,
        spam_destination=data.spam_destination,
        spam_destination_properties=data.spam_destination_properties,
        max_password_age=data.max_password_age,
        max_password_age_properties=data.max_password_age_properties,
        enable_catch_all=data.enable_catch_all,
        catch_all_forwarding_address=data.catch_all_forwarding_address,
        enable_hybrid_mode=data.enable_hybrid_mode,
        hybrid_connector_properties=data.hybrid_connector_properties,
        caution_id=data.caution_id,
        disclaimer_id=data.disclaimer_id,
        filter_policy_id=data.filter_policy_id,
        attachment_policy_id=data.attachment_policy_id,
        session_timeout=data.session_timeout,
        dns_txt_verification_key=dns_txt_verification_key
    )

    # Start the domain creation process
    new_domain_creation(domain_name=data.domain_name)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Domain created successfully",
            "domain_name": data.domain_name,
            "dns_txt_verification_key": f"ms25-domain-verification={dns_txt_verification_key}"
        } 
    )


# Get Domain DNS TXT Verification Key
@router.get("/dns-txt-verification-key/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Get Domain DNS TXT Verification Key")
async def get_domain_dns_txt_verification_key(domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get the DNS TXT verification key for a specific domain
    """
    domain_details_ = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_details_["managed_by"],
        user_id=None,
        db=PgDB
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Domain DNS TXT verification key fetched successfully",
            "dns_txt_verification_key": f"ms25-domain-verification={domain_details_['dns_txt_verification_key']}"
        }
    )


# Validate Domain DNS TXT Verification Key
@router.patch("/dns-txt-verification-key/validate/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Validate Domain DNS TXT Verification Key")
async def validate_domain_dns_txt_verification_key(domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Validate the DNS TXT verification key for a specific domain
    """
    domain_details_ = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_details_["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Validate the DNS TXT verification key
    is_valid = await validate_dns_txt_verification_key(
        domain_name=domain_name,
        txt_record=f"ms25-domain-verification={domain_details_['dns_txt_verification_key']}"
    )

    # Update the domain's DNS TXT verification status in the database
    await update_domain_txt_verification_status(
        db_session=PgDB,
        domain_name=domain_name,
        is_verified=is_valid
    )

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "DNS TXT verification key validation failed, please ensure the correct TXT record is set in your DNS settings"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain DNS TXT verification key validated successfully"}
    )


# Get Domain details
@router.get("/details/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Get Domain details")
async def domain_details(domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific domain
    """
    domain_details_ = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_details_["managed_by"],
        user_id=None,
        db=PgDB
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain details fetched successfully", "domain_details": domain_details_}
    )


# Get list of all domains
@router.get("/list/{organization_id}", response_class=JSONResponse, tags=["Domain Management"], summary="Get list of all Domains under an Organization")
async def domain_list(organization_id: str, query: str, user: CurrentUser, PgDB: PostgresDep, page: int = 1, limit: int = 10) -> JSONResponse:
    """
    Get a list of all domains under an organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Fetch the list of domains
    domains = await get_all_domains_by_organization(
        db_session=PgDB,
        organization_id=organization_id,
        search_query=query,
        page=page,
        page_size=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domains fetched successfully", "domains": domains}
    )


# Edit Domain details
@router.patch("/edit/info/{organization_id}/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Edit Domain details")
async def domain_edit_info(organization_id: str, domain_name: str, data: PatchDomainForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit details of a specific domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Hybrid mode and catch-all validation
    # Any one should be enabled, or both disabled. If one is enabled, the other should be disabled.
    if data.enable_catch_all and data.enable_hybrid_mode:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Both catch-all and hybrid mode cannot be enabled at the same time"}
        )

    # Edit all the domain details/info
    domains = await update_domain_info(
        db_session=PgDB,
        organization_id=organization_id,
        domain_name=domain_name,
        details=data.details,
        anti_phishing_secret_code=data.anti_phishing_secret_code,
        enable_catch_all=data.enable_catch_all,
        catch_all_forwarding_address=data.catch_all_forwarding_address,
        enable_hybrid_mode=data.enable_hybrid_mode,
        hybrid_connector_properties=data.hybrid_connector_properties,
        spam_destination=data.spam_destination,
        spam_destination_properties=data.spam_destination_properties,
        max_password_age=data.max_password_age,
        max_password_age_properties=data.max_password_age_properties,
        caution_id=data.caution_id,
        disclaimer_id=data.disclaimer_id,
        filter_policy_id=data.filter_policy_id,
        attachment_policy_id=data.attachment_policy_id,
        session_timeout=data.session_timeout
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domains fetched successfully", "domains": domains}
    )


# Edit Domain Activation Status
@router.put("/edit/activation/{organization_id}/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Edit Domain Activation Status")
async def domain_edit_activation(organization_id: str, domain_name: str, is_active: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit the activation status of a specific domain
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Update the activation status of the domain
    await update_domain_activation_status(
        db_session=PgDB,
        organization_id=organization_id,
        domain_name=domain_name,
        is_active=is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain activation status updated successfully"}
    )


# Delete Domain
@router.delete("/delete/{organization_id}/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Delete a Domain")
async def domain_delete(organization_id: str, domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a specific domain along with all its associated data (including mailboxes, policies, etc.)
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Check if the domain has any associated identities linked to it
    has_associated_identities = await check_if_domain_has_associated_identities(
        db_session=PgDB,
        domain_name=domain_name
    )
    if has_associated_identities:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Domain cannot be deleted as it has associated identities."}
        )

    # Fetch the domain details before deletion
    domain_details = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    # Delete the domain
    await delete_domain_and_update_quota(
        db_session=PgDB,
        organization_id=organization_id,
        domain_name=domain_name
    )

    # Do it if the domain was DNS TXT verified
    if domain_details["is_dns_txt_verified"]:
        # Start the domain deletion process
        delete_domain_process(domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Domain deleted successfully, along with all its associated policies and data"}
    )


# Migrate Domain to another Organization
@router.post("/migrate/{organization_id}/{domain_name}/to/{new_organization_id}", response_class=JSONResponse, tags=["Domain Management"], summary="Migrate Domain to another Organization")
async def domain_migrate(organization_id: str, domain_name: str, new_organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Migrate a specific domain to another organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:create", "domain:view", "organization:view", "domain:delete"],
        organization_level_permissions=["organization:edit", "organization:create"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    # Migrate the domain to the new organization
    await migrate_domain_to_new_organization(
        db_session=PgDB,
        organization_id=organization_id,
        domain_name=domain_name,
        new_organization_id=new_organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Domain migrated successfully, along with all its associated data",
            "domain_name": domain_name,
            "from_organization": organization_id,
            "to_organization": new_organization_id
        }
    )


# Get DNS Records
@router.get("/dns/{domain_name}", response_class=JSONResponse, tags=["Domain Management"], summary="Get list of all DNS Records under an Organization")
async def dns_list(domain_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get a list of all DNS Records under an organization
    """
    domain_details_ = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_details_["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Fetch the list of DNS records
    dns_records = fetch_dns_records(domain=domain_name)
    if not dns_records:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "No DNS records found, please recreate the Domain or contact support"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "DNS records fetched successfully", "dns_records": dns_records}
    )
