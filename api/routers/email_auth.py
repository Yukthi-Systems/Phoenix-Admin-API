"""
This module provides E-Mail 2FA related API endpoints
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
    Request,
    secrets,
    status,
    orjson,
    time
)
from src.database import (
    get_basic_user_details_by_id,
    set_email_verified,
    manage_email_2fa,
    MemcachedDep,
    PostgresDep
)
from src.main import CurrentUser, validate_permissions, send_notification
from src.utils.base.constants import MAX_AGE_OF_CACHE, COOKIE_DOMAIN
from src.utils.models import All_Exceptions


# Router
router = APIRouter()

# OTP Constants
OTP_CODE_GENERATOR = lambda: ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
OTP_EXPIRY_TIME = 60 * 2  # 2 minutes expiry for OTP


# Send OTP to User's E-Mail for verification of e-mail address
@router.post("/verify/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - E-Mail Auth"], summary="Generate OTP for E-Mail Authentication")
async def user_email_auth_verify_email(organization_id: str, user_id: str, org_name: str, user: CurrentUser, PgDB: PostgresDep, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Generate OTP for E-Mail Authentication for a user
    """
    # If its self verification, then we don't need to check for permissions
    if user.user_id != user_id:
        await validate_permissions(
            current_user_permissions=user.permissions,
            basic_permissions=["user:view"],    # For verification, we don't need edit permissions
            organization_level_permissions=["organization:view"],
            current_user_organization_id=user.organization_id,
            accessed_organization_id=organization_id,
            user_id=user_id,
            db=PgDB
        )

    otp_code = OTP_CODE_GENERATOR()

    # Fetch user details
    user_details = await get_basic_user_details_by_id(
        db_session=PgDB,
        user_id=user_id,
        organization_id=organization_id
    )

    # Send Email with the OTP code
    send_notification(
        notification_type="email",
        to=user_details["user_email"],
        template_name="otp_verification",
        variables={
            "otp": otp_code,
            "organization_name": org_name,
            "name": user_details["display_name"],
            "year": time.strftime("%Y")
        }
    )

    # Save OTP code in cache for verification
    await CacheDB.set(
        key=f"email_auth:otp:verify:{organization_id}:{user_id}".encode("utf-8"),
        value=otp_code.encode("utf-8"),
        exptime=OTP_EXPIRY_TIME
    )

    return JSONResponse(
        content={"message": "OTP for E-Mail verification sent successfully"},
        status_code=status.HTTP_201_CREATED
    )


# Send OTP to User's E-Mail for login
@router.post("/send-otp", response_class=JSONResponse, tags=["User Authentication", "2FA - E-Mail Auth"], summary="Generate OTP for E-Mail Authentication for Login")
async def send_email_otp_for_login(request: Request, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Generate OTP for E-Mail Authentication for a user to login
    """
    session_id = request.cookies.get("SESSION_ID")
    if not session_id:
        raise All_Exceptions(message="Session ID not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise All_Exceptions(message="CSRF token not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    user_data_bytes = await CacheDB.get(session_id.encode("utf-8"))
    if not user_data_bytes:
        raise All_Exceptions(message="Session expired", status_code=status.HTTP_401_UNAUTHORIZED)

    user_data = orjson.loads(user_data_bytes)
    if user_data["csrf_token"] != csrf_token:
        raise All_Exceptions(message="CSRF token mismatch", status_code=status.HTTP_401_UNAUTHORIZED)

    otp_code = OTP_CODE_GENERATOR()
    organization_id = user_data["organization_id"]
    user_id = user_data["user_id"]
    user_email = user_data["user_email"]
    display_name = user_data["display_name"]
    organization_name = user_data["organization_name"]

    # Save OTP code in cache for verification
    await CacheDB.set(
        key=f"email_auth:otp:login:{organization_id}:{user_id}".encode("utf-8"),
        value=otp_code.encode("utf-8"),
        exptime=OTP_EXPIRY_TIME
    )

    # send email with the OTP code
    send_notification(
        notification_type="email",
        to=user_email,
        template_name="otp_login",
        variables={
            "otp": otp_code,
            "organization_name": organization_name,
            "name": display_name,
            "year": time.strftime("%Y")
        }
    )

    return JSONResponse(
        content={"message": "OTP Email sent successfully"},
        status_code=status.HTTP_201_CREATED
    )


# Validate OTP for E-Mail Authentication
@router.post("/validate-email/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - E-Mail Auth"], summary="Validate OTP for E-Mail Authentication")
async def validate_email_otp(organization_id: str, user_id: str, otp_code: str, user: CurrentUser, PgDB: PostgresDep, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Validate OTP for E-Mail Authentication for a user
    """
    # If its self verification, then we don't need to check for permissions
    if user.user_id != user_id:
        await validate_permissions(
            current_user_permissions=user.permissions,
            basic_permissions=["user:view"],
            organization_level_permissions=["organization:view"],
            current_user_organization_id=user.organization_id,
            accessed_organization_id=organization_id,
            user_id=user_id,
            db=PgDB
        )

    cached_otp = await CacheDB.get(f"email_auth:otp:verify:{organization_id}:{user_id}".encode("utf-8"))

    if not cached_otp:
        raise All_Exceptions(
            message="OTP not found or expired",
            status_code=status.HTTP_404_NOT_FOUND
        )

    if cached_otp.decode("utf-8") != otp_code:
        raise All_Exceptions(
            message="Invalid OTP code",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # If OTP is valid, remove it from cache
    await CacheDB.delete(f"email_auth:otp:verify:{organization_id}:{user_id}".encode("utf-8"))

    # Set the user's email as verified in the database
    await set_email_verified(db_session=PgDB, organization_id=organization_id, user_id=user_id, is_verified=True)

    return JSONResponse(
        content={"message": "E-Mail verified successfully"},
        status_code=status.HTTP_200_OK
    )


# Enable/Disable 2FA using E-Mail OTP
@router.post("/manage/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - E-Mail Auth"], summary="Enable/Disable E-Mail 2FA")
async def enable_or_disable_email_2fa(organization_id: str, user_id: str, enable: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Enable or Disable E-Mail 2FA for a user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=[],
        organization_level_permissions=["user:view", "organization:edit", "user:security:2fa:email:edit"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Manage E-Mail 2FA status
    await manage_email_2fa(db_session=PgDB, organization_id=organization_id, user_id=user_id, enable=enable)

    return JSONResponse(
        content={"message": "E-Mail 2FA status updated successfully"},
        status_code=status.HTTP_200_OK
    )


# Authenticate User using E-Mail OTP
@router.post("/validate", response_class=JSONResponse, tags=["User Authentication", "2FA - E-Mail Auth"], summary="Authenticate User using E-Mail OTP")
async def authenticate_user_with_email_otp(request: Request, otp_code: str, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Authenticate User using E-Mail OTP
    """
    session_id = request.cookies.get("SESSION_ID")
    if not session_id:
        raise All_Exceptions(message="Session ID not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise All_Exceptions(message="CSRF token not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    user_data_bytes = await CacheDB.get(session_id.encode("utf-8"))
    if not user_data_bytes:
        raise All_Exceptions(message="Session expired", status_code=status.HTTP_401_UNAUTHORIZED)

    user_data = orjson.loads(user_data_bytes)
    if user_data["csrf_token"] != csrf_token:
        raise All_Exceptions(message="CSRF token mismatch", status_code=status.HTTP_401_UNAUTHORIZED)
    
    organization_id = user_data["organization_id"]
    user_id = user_data["user_id"]

    cached_otp = await CacheDB.get(f"email_auth:otp:login:{organization_id}:{user_id}".encode("utf-8"))
    if cached_otp and cached_otp.decode("utf-8") == otp_code:
        user_data["authenticated"] = True
        await CacheDB.replace(
            key=session_id.encode("utf-8"),
            value=orjson.dumps(user_data),
            exptime=MAX_AGE_OF_CACHE
        )
        return JSONResponse(
            content={"message": "E-Mail OTP validated successfully"},
            status_code=status.HTTP_200_OK
        )

    # If no valid TOTP code was found, return an error response
    await CacheDB.delete(f"email_auth:otp:login:{organization_id}:{user_id}".encode("utf-8"))
    await CacheDB.delete(session_id.encode("utf-8"))

    response = JSONResponse(
        content={"message": "Invalid E-Mail OTP code, please relogin to try again"},
        status_code=status.HTTP_401_UNAUTHORIZED
    )

    response.delete_cookie(
        key="SESSION_ID",
        httponly=True,
        # Comment this following lines to test in local
        secure=True,
        samesite="strict",
        domain=COOKIE_DOMAIN
    )
    response.delete_cookie(
        key="IS_SESSION_VALID",
        httponly=False,
        # Comment this following lines to test in local
        secure=True,
        samesite="strict",
        domain=COOKIE_DOMAIN
    )

    return response
