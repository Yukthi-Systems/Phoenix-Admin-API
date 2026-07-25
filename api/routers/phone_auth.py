"""
This module provides API endpoints for managing SMS-based two-factor authentication (2FA) for user phone
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
    orjson
)
from src.database import (
    get_basic_user_details_by_id,
    set_phone_verified,
    manage_sms_2fa,
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


# Send OTP to User's SMS for verification to phone number
@router.post("/verify/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - SMS Auth"], summary="Generate OTP for verifying user's phone number")
async def user_sms_auth_verify_phone(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Generate OTP for verifying user's phone number
    """
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

    # Send SMS with the OTP code
    send_notification(
        notification_type="sms",
        to=user_details["primary_phone"],
        template_name="aio_otp",
        variables={
            "to": user_details["primary_phone"],
            "otp": otp_code
        }
    )

    # Save OTP code in cache for verification
    await CacheDB.set(
        key=f"sms_auth:otp:verify:{organization_id}:{user_id}".encode("utf-8"),
        value=otp_code.encode("utf-8"),
        exptime=OTP_EXPIRY_TIME
    )

    return JSONResponse(
        content={"message": "SMS based OTP for Phone Number verification sent successfully"},
        status_code=status.HTTP_201_CREATED
    )


# Send OTP to User's SMS for login
@router.post("/send-otp", response_class=JSONResponse, tags=["User Authentication", "2FA - SMS Auth"], summary="Generate OTP for SMS Authentication for Login")
async def send_sms_otp_for_login(request: Request, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Generate OTP for SMS Authentication for a user to login
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
    primary_phone = user_data["primary_phone"]

    # Save OTP code in cache for verification
    await CacheDB.set(
        key=f"sms_auth:otp:login:{organization_id}:{user_id}".encode("utf-8"),
        value=otp_code.encode("utf-8"),
        exptime=OTP_EXPIRY_TIME
    )

    # send sms with the OTP code
    send_notification(
        notification_type="sms",
        to=primary_phone,
        template_name="aio_otp",
        variables={
            "to": primary_phone,
            "otp": otp_code
        }
    )

    return JSONResponse(
        content={"message": "SMS based OTP for Login sent successfully"},
        status_code=status.HTTP_201_CREATED
    )


# Validate OTP for SMS Authentication
@router.post("/validate-phone/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - SMS Auth"], summary="Validate OTP for SMS Authentication")
async def validate_sms_otp(organization_id: str, user_id: str, otp_code: str, user: CurrentUser, PgDB: PostgresDep, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Validate OTP for SMS Authentication for a user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    cached_otp = await CacheDB.get(f"sms_auth:otp:verify:{organization_id}:{user_id}".encode("utf-8"))

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
    await CacheDB.delete(f"sms_auth:otp:verify:{organization_id}:{user_id}".encode("utf-8"))

    # Set the user's phone as verified in the database
    await set_phone_verified(db_session=PgDB, organization_id=organization_id, user_id=user_id, is_verified=True)

    return JSONResponse(
        content={"message": "Phone Number verified successfully"},
        status_code=status.HTTP_200_OK
    )


# Enable/Disable 2FA using SMS OTP
@router.post("/manage/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - SMS Auth"], summary="Enable/Disable SMS 2FA")
async def enable_or_disable_sms_2fa(organization_id: str, user_id: str, enable: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Enable or Disable SMS 2FA for a user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=[],
        organization_level_permissions=["user:view", "organization:edit", "user:security:2fa:sms_phone:edit"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Manage SMS 2FA status
    await manage_sms_2fa(db_session=PgDB, organization_id=organization_id, user_id=user_id, enable=enable)

    return JSONResponse(
        content={"message": "SMS 2FA status updated successfully"},
        status_code=status.HTTP_200_OK
    )


# Authenticate User using SMS OTP
@router.post("/validate", response_class=JSONResponse, tags=["User Authentication", "2FA - SMS Auth"], summary="Authenticate User using SMS OTP")
async def authenticate_user_with_sms_otp(request: Request, otp_code: str, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Authenticate User using SMS OTP
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

    cached_otp = await CacheDB.get(f"sms_auth:otp:login:{organization_id}:{user_id}".encode("utf-8"))
    if cached_otp and cached_otp.decode("utf-8") == otp_code:
        user_data["authenticated"] = True
        await CacheDB.replace(
            key=session_id.encode("utf-8"),
            value=orjson.dumps(user_data),
            exptime=MAX_AGE_OF_CACHE
        )
        return JSONResponse(
            content={"message": "SMS OTP validated successfully"},
            status_code=status.HTTP_200_OK
        )

    # If no valid TOTP code was found, return an error response
    await CacheDB.delete(f"sms_auth:otp:login:{organization_id}:{user_id}".encode("utf-8"))
    await CacheDB.delete(session_id.encode("utf-8"))

    response = JSONResponse(
        content={"message": "Invalid SMS OTP code, please relogin to try again"},
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
