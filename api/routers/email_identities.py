"""
This module handles all the API endpoints related to E-Mail Identities
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


from src.main import CurrentUser, validate_permissions, check_password_breach, validate_recaptcha, send_notification
from src.utils.base.libraries import JSONResponse, APIRouter, status, base64, datetime, secrets
from src.utils.models import CreateIdentity
from src.database import (
    list_identities_under_domain,
    create_new_identity_entry,
    get_organization_details,
    update_identity_password,
    update_identity_details,
    get_domain_details,
    get_identity_info,
    delete_identity,
    MemcachedDep,
    PostgresDep
)

# Router
router = APIRouter()


# OTP Constants
OTP_CODE_GENERATOR = lambda: ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
OTP_EXPIRY_TIME = 60 * 2  # 2 minutes expiry for OTP


# Create a new E-Mail Identity under an Organization
@router.post("/create", response_class=JSONResponse, tags=["Identity Management"], description="Create a new E-Mail Identity")
async def create_email_identity(data: CreateIdentity, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new E-Mail Identity under an Organization
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=data.email_domain)

    # If the Domain is not verified, then we cannot create an identity under it
    if not domain_info["is_dns_txt_verified"]:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Cannot create an E-Mail Identity under an unverified domain, please verify the domain first"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:create", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    org_info = await get_organization_details(db_session=PgDB, organization_id=domain_info["managed_by"])

    # Check if the organization has reached its identity quota
    if org_info["allocated_email_identities"] != -1:  # -1 indicates unlimited
        allocated_email_identities = org_info["allocated_email_identities"]
        utilized_email_identities = org_info["utilized_email_identities"]
        if utilized_email_identities >= allocated_email_identities:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"message": "Organization has reached its email identity quota. Cannot create new email identity."}
            )

    # Check if password is breached
    if check_password_breach(user_name=f"{data.email_prefix}@{data.email_domain}".lower(), password=base64.b64decode(data.base64_password).decode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "The password you are trying to set for the new email identity has been exposed in a data breach, please choose a different password to secure the account"}
        )

    # Create a new E-Mail Identity entry in the database
    await create_new_identity_entry(
        db_session=PgDB,
        email=f"{data.email_prefix}@{data.email_domain}".lower(),
        domain_name=data.email_domain,
        first_name=data.first_name,
        last_name=data.last_name,
        primary_phone=data.primary_phone_number,
        secondary_email=data.secondary_email,
        base64_encoded_password=data.base64_password,
        is_app_2fa_enabled=data.is_app_2fa_enabled,
        is_sms_2fa_enabled=data.is_sms_2fa_enabled,
        is_email_2fa_enabled=data.is_email_2fa_enabled,
        restriction_policy_id=data.restriction_policy_id,
        department_id=data.department_id,
        is_enabled=data.is_enabled
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "E-Mail Identity created successfully", "email": f"{data.email_prefix}@{data.email_domain}".lower()}
    )


@router.get("/details/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["Identity Management"], description="Get details of a specific E-Mail Identity")
async def get_full_identity_details(domain_name: str, email_prefix: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get details of a specific E-Mail Identity
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Fetch the email identity details from the database
    identity_details = await get_identity_info(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}".lower()
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "E-Mail Identity details fetched successfully", "data": identity_details}
    )


@router.get("/list/{domain_name}/{page}/{page_size}", response_class=JSONResponse, tags=["Identity Management"], description="List/Export all E-Mail Identities under a Domain")
async def list_identities(domain_name: str, query: str, page: int, page_size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all E-Mail Identities under a Domain with pagination (Same for exporting the list of identities)
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Fetch the list of E-Mail Identities from the database
    identities = await list_identities_under_domain(
        db_session=PgDB,
        domain_name=domain_name,
        search_query=query,
        page=page,
        page_size=page_size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "E-Mail Identities listed successfully", "data": identities}
    )


@router.delete("/delete/{domain_name}/{email_prefix}", response_class=JSONResponse, tags=["Identity Management"], description="Delete an E-Mail Identity")
async def delete_identity_entry(domain_name: str, email_prefix: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an E-Mail Identity
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:view", "domain:view", "identity:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # TODO: Delete the MailBox first and RMQ call to delete

    # TODO: Delete the Chat User and make required API call for that too

    # TODO: Delete the Files User and its associated data and make required API call for that too

    # Delete the E-Mail Identity entry from the database
    await delete_identity(
        db_session=PgDB,
        email=f"{email_prefix}@{domain_name}".lower()
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "E-Mail Identity deleted successfully"}
    )


@router.put("/update", response_class=JSONResponse, tags=["Identity Management"], description="Update an E-Mail Identity")
async def update_identity(data: CreateIdentity, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update an E-Mail Identity
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=data.email_domain)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:edit", "identity:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Update the E-Mail Identity details in the database
    await update_identity_details(
        db_session=PgDB,
        email=f"{data.email_prefix}@{data.email_domain}".lower(),
        first_name=data.first_name,
        last_name=data.last_name,
        primary_phone=data.primary_phone_number,
        secondary_email=data.secondary_email,
        is_app_2fa_enabled=data.is_app_2fa_enabled,
        is_sms_2fa_enabled=data.is_sms_2fa_enabled,
        is_email_2fa_enabled=data.is_email_2fa_enabled,
        restriction_policy_id=data.restriction_policy_id,
        department_id=data.department_id,
        is_enabled=data.is_enabled
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "E-Mail Identity updated successfully", "email": f"{data.email_prefix}@{data.email_domain}".lower()}
    )


@router.patch("/update/password", response_class=JSONResponse, tags=["Identity Management"], description="Update the password of an E-Mail Identity")
async def update_password_for_identity(data: dict, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update the password of an E-Mail Identity
    """
    new_password = data.get("new_base64_password")
    domain_name = data.get("domain_name")
    email = data.get("email")

    if not new_password or not email or not domain_name:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Both 'new_base64_password', 'email', and 'domain_name' fields are required."}
        )

    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["identity:edit", "identity:view", "domain:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Update the E-Mail Identity password in the database
    await update_identity_password(
        db_session=PgDB,
        email=str(email).lower(),
        new_base64_password=str(new_password)
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "E-Mail Identity password updated successfully", "email": str(email).lower()}
    )


# Start the Password Reset process
@router.post("/reset/password/{email_id}/init", response_class=JSONResponse, tags=["Identity Management"], summary="Start Password Reset process")
async def mailbox_start_password_reset(email_id: str, verify_via: str, recaptcha_token: str, CacheDB: MemcachedDep, PgDB: PostgresDep) -> JSONResponse:
    """
    Start the Password Reset process by generating a reset token and sending it via email
    """
    # Validate reCAPTCHA token
    if not validate_recaptcha(token=recaptcha_token):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "reCAPTCHA validation failed, cannot initiate password reset"}
        )

    # Get Identity details to get the secondary email for sending OTP
    identity_info = await get_identity_info(db_session=PgDB, email=email_id)
    if not identity_info["is_enabled"]:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Associated email identity is not enabled, cannot initiate password reset"}
        )

    otp: str = OTP_CODE_GENERATOR()
    user_name: str = str(identity_info["last_name"] + " " + identity_info["first_name"]).strip()
    secondary_email: str = identity_info["secondary_email"]
    primary_phone: str = identity_info["primary_phone"]

    # There are two ways to verify the user - email or phone
    match verify_via:
        # Initiate password reset via email
        case "email":
            send_notification(
                notification_type="email",
                to=secondary_email,
                template_name="password_reset_otp",
                variables={
                    "name": user_name,
                    "otp": otp,
                    "year": datetime.now().year
                }
            )

        # Initiate password reset via phone
        case "phone":
            send_notification(
                notification_type="sms",
                to=primary_phone,
                template_name="password_reset_otp",
                variables={
                    "to": primary_phone,
                    "otp": otp
                }
            )

        case _:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Invalid verification method, must be either 'email' or 'phone'"}
            )

    await CacheDB.set(
        key=f"password_reset:otp:{verify_via}:verify:{email_id}".encode("utf-8"),
        value=otp.encode("utf-8"),
        exptime=OTP_EXPIRY_TIME
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Password reset process initiated successfully, please check your {verify_via} for the OTP"}
    )


# Complete the Password Reset process
@router.post("/reset/password/{email_id}/complete", response_class=JSONResponse, tags=["Identity Management"], summary="Complete Password Reset process")
async def mailbox_password_reset(email_id: str, data: dict, CacheDB: MemcachedDep, PgDB: PostgresDep) -> JSONResponse:
    """
    Complete the Password Reset process by verifying the reset token and updating the password
    """
    if "otp" not in data or not data["otp"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "OTP is required to complete the password reset process"}
        )

    if "new_password_base64" not in data or not data["new_password_base64"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "New password is required to complete the password reset process"}
        )

    if "verify_via" not in data or data["verify_via"] not in ["email", "phone"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Verification method is required to complete the password reset process and must be either 'email' or 'phone'"}
        )

    new_password_base64: str = data["new_password_base64"]
    entered_otp: str = data["otp"]
    verify_via: str = data["verify_via"]

    # Verify the reset token from cache
    cached_otp_bytes = await CacheDB.get(f"password_reset:otp:{verify_via}:verify:{email_id}".encode("utf-8"))
    if not cached_otp_bytes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Password reset OTP has expired or not requested, please initiate the password reset process again"}
        )

    cached_otp: str = cached_otp_bytes.decode("utf-8")
    if entered_otp != cached_otp:
        await CacheDB.delete(f"password_reset:otp:{verify_via}:verify:{email_id}".encode("utf-8"))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid OTP provided, please try again"}
        )

    # Since OTP is valid, delete it from cache
    await CacheDB.delete(f"password_reset:otp:{verify_via}:verify:{email_id}".encode("utf-8"))

    # Check if password is breached
    if check_password_breach(user_name=email_id, password=base64.b64decode(new_password_base64).decode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "The password you are trying to set has been exposed in a data breach, please choose a different password to secure the account"}
        )

    # Update the password in the database
    await update_identity_password(
        db_session=PgDB,
        email=email_id,
        new_base64_password=new_password_base64
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Password has been reset successfully"}
    )


# TODO: enable/disable identity
# TODO: 2FA management
# TODO: SSO based self service portal for identity management
# TODO: Edit E-Mail ID itself (prefix) - And all its associated services (mailbox, chat, files, etc.) should be updated accordingly
