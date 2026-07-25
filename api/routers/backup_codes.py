"""
This module provides Backup Codes related API endpoints
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
    replace_backup_codes_for_user,
    check_backup_codes_for_user,
    use_one_backup_code,
    MemcachedDep,
    PostgresDep
)
from src.main import CurrentUser, validate_permissions
from src.utils.base.constants import MAX_AGE_OF_CACHE, COOKIE_DOMAIN
from src.utils.models import All_Exceptions


# Router
router = APIRouter()


# Backup Code - Generate or Reset/Replace/Regenerate
@router.post("/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - Backup Code"], summary="Generate or Reset/Replace/Regenerate Backup Codes")
async def user_replace_backup_codes(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Generate or Reset/Replace/Regenerate Backup Codes for a user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:backup_codes:edit", "user:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    generate_code = lambda: ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    codes = [generate_code() for _ in range(6)]

    await replace_backup_codes_for_user(
        db_session=PgDB,
        user_id=user_id,
        codes=codes
    )

    return JSONResponse(
        content={"message": "Backup codes replaced successfully", "codes": codes},
        status_code=status.HTTP_200_OK
    )


# Authenticate using Backup Code (instead of TOTP)
@router.patch("/validate", response_class=JSONResponse, tags=["User Authentication", "2FA - Backup Code"], summary="Login Using Backup Code")
async def user_authenticate_backup_code(request: Request, code: str, PgDB: PostgresDep, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Authenticate a user using Backup Code instead of TOTP
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

    validated = await use_one_backup_code(db_session=PgDB, user_id=user_data["user_id"], code=code)

    if validated:
        # If the backup code is valid, update the session data
        user_data["authenticated"] = True
        await CacheDB.replace(
            key=session_id.encode("utf-8"),
            value=orjson.dumps(user_data),
            exptime=MAX_AGE_OF_CACHE
        )
        return JSONResponse(
            content={"message": "Backup code validated successfully, you are now logged in"},
            status_code=status.HTTP_200_OK
        )

    # If the backup code is invalid, delete the session
    await CacheDB.delete(session_id.encode("utf-8"))

    response = JSONResponse(
        content={"message": "Invalid backup code, please try again or use TOTP"},
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


# Check if Backup Codes are generated and available for the user
@router.get("/check/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - Backup Code"], summary="Check if Backup Codes are generated")
async def user_check_backup_codes(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Check if Backup Codes are generated and available for the user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:backup_codes:view", "user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    has_backup_codes, valid_backup_codes_count = await check_backup_codes_for_user(db_session=PgDB, user_id=user_id)

    return JSONResponse(
        content={
            "message": f"Backup codes {'are' if has_backup_codes else 'are not'} available for the user",
            "has_backup_codes": has_backup_codes,
            "valid_backup_codes_count": valid_backup_codes_count
        },
        status_code=status.HTTP_200_OK
    )
