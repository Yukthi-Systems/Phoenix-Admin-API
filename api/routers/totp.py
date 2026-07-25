"""
This module provides TOTP related API endpoints
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
    status,
    orjson,
    pyotp
)
from src.database import (
    get_totp_entry_active_status,
    get_basic_user_details_by_id,
    disable_two_factor_totp,
    enable_two_factor_totp,
    list_all_totp_entries,
    create_new_totp_entry,
    delete_totp_entry,
    alter_totp_entry,
    get_totp_secrets,
    can_enable_totp,
    MemcachedDep,
    PostgresDep
)
from src.utils.base.constants import MAX_AGE_OF_CACHE, COOKIE_DOMAIN
from src.main import CurrentUser, validate_permissions
from src.utils.models import All_Exceptions


# Router
router = APIRouter()


# Time Based One Time Password (TOTP) - Two Factor User Authentication
@router.put("/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - TOTP"], summary="Enable/Disable Two Factor User Authentication")
async def user_enable_disable_totp(organization_id: str, user_id: str, enable: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Enable/Disable Two Factor User Authentication
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:2fa:totp:edit", "user:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    if enable:
        # Check if the user can enable TOTP
        if not await can_enable_totp(db_session=PgDB, user_id=user_id):
            raise All_Exceptions(
                message="You cannot enable TOTP for this user. At least one TOTP entry must be created first.",
                status_code=status.HTTP_412_PRECONDITION_FAILED
            )
        
        # Enable TOTP for the user
        await enable_two_factor_totp(db_session=PgDB, user_id=user_id, organization_id=organization_id)

    else:
        # Disable TOTP for the user
        await disable_two_factor_totp(db_session=PgDB, user_id=user_id, organization_id=organization_id)

    return JSONResponse(
        content={"message": f"Two Factor User Authentication {'enabled' if enable else 'disabled'} successfully for user {user_id} in organization {organization_id}"},
        status_code=status.HTTP_200_OK
    )


# Time Based One Time Password (TOTP) - Generate QR Code for Two Factor User Authentication
@router.post("/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - TOTP"], summary="Generate QR Code for Two Factor User Authentication")
async def user_generate_totp_qr_code(organization_id: str, user_id: str, totp_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Generate QR Code for Two Factor User Authentication
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:2fa:totp:edit", "user:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Generate a TOTP secret key
    totp_secret_key = pyotp.random_base32(length=32, chars=list("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"))
    totp_obj = pyotp.TOTP(totp_secret_key)
    totp_uri_to_scan = totp_obj.provisioning_uri(name=f"{user_id}@{organization_id}", issuer_name="Yukthi")

    await create_new_totp_entry(
        db_session=PgDB,
        user_id=user_id,
        totp_name=totp_name,
        totp_secret=totp_secret_key
    )

    return JSONResponse(
        content={
            "message": "TOTP QR Code generated successfully",
            "totp_uri": totp_uri_to_scan,
            "totp_secret_key": totp_secret_key  # Return the secret key for manual entry if QR code scanning fails
        },
        status_code=status.HTTP_200_OK
    )


# List TOTP entries for the user
@router.get("/{organization_id}/{user_id}", response_class=JSONResponse, tags=["2FA - TOTP"], summary="List TOTP entries for the user")
async def user_list_totp_entries(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List TOTP entries for the user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:2fa:totp:view", "user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    totp_entries = await list_all_totp_entries(db_session=PgDB, user_id=user_id)

    return JSONResponse(
        content={
            "message": "TOTP entries fetched successfully",
            "data": totp_entries,
            "total_entries": len(totp_entries)
        },
        status_code=status.HTTP_200_OK
    )


# Edit the TOTP entry (like name and activate/deactivate)
@router.patch("/{organization_id}/{user_id}/{totp_id}", response_class=JSONResponse, tags=["2FA - TOTP"], summary="Edit a TOTP entry")
async def user_edit_totp_entry(organization_id: str, user_id: str, totp_id: str, totp_name: str, is_active: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Edit a TOTP entry (like name and activate/deactivate)
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:2fa:totp:edit", "user:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    await alter_totp_entry(
        db_session=PgDB,
        user_id=user_id,
        totp_id=totp_id,
        totp_name=totp_name,
        is_active=is_active
    )

    return JSONResponse(
        content={"message": "TOTP entry updated successfully"},
        status_code=status.HTTP_200_OK
    )


# Delete the TOTP entry
@router.delete("/{organization_id}/{user_id}/{totp_id}", response_class=JSONResponse, tags=["2FA - TOTP"], summary="Delete a TOTP entry")
async def user_delete_totp_entry(organization_id: str, user_id: str, totp_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a TOTP entry
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:2fa:totp:edit", "user:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    totp_entry_details = await get_totp_entry_active_status(db_session=PgDB, user_id=user_id)   # {"id": bool, ...}
    if totp_id not in totp_entry_details:
        raise All_Exceptions(
            message=f"TOTP entry with ID {totp_id} does not exist for user {user_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # If user's TOTP is disabled, we can delete any TOTP entry enven if it is active or last one or whatever
    user_details = await get_basic_user_details_by_id(db_session=PgDB, user_id=user_id, organization_id=organization_id)
    if not user_details["is_totp_2fa_active"]:
        await delete_totp_entry(db_session=PgDB, user_id=user_id, totp_id=totp_id)
        return JSONResponse(
            content={"message": f"TOTP entry with ID {totp_id} deleted successfully for user {user_id}"},
            status_code=status.HTTP_200_OK
        )

    # If there is only one TOTP entry and it is active, we cannot delete it
    if len(totp_entry_details) == 1:
        if totp_entry_details[totp_id]:
            raise All_Exceptions(
                message="Cannot delete the only active TOTP entry. Please disable TOTP first.",
                status_code=status.HTTP_412_PRECONDITION_FAILED
            )
        else:
            await delete_totp_entry(db_session=PgDB, user_id=user_id, totp_id=totp_id)
            return JSONResponse(
                content={"message": f"TOTP entry with ID {totp_id} deleted successfully for user {user_id}"},
                status_code=status.HTTP_200_OK
            )

    if len(totp_entry_details) >= 2:
        if totp_entry_details[totp_id] and [ entry for entry in totp_entry_details if totp_entry_details[entry] ] == 1:
            raise All_Exceptions(
                message="Cannot delete the only active TOTP entry. Please disable TOTP first.",
                status_code=status.HTTP_412_PRECONDITION_FAILED
            )
        
        elif not totp_entry_details[totp_id]:
            await delete_totp_entry(db_session=PgDB, user_id=user_id, totp_id=totp_id)
            return JSONResponse(
                content={"message": f"TOTP entry with ID {totp_id} deleted successfully for user {user_id}"},
                status_code=status.HTTP_200_OK
            )
        
        elif totp_entry_details[totp_id] and len([ entry for entry in totp_entry_details if totp_entry_details[entry] ]) > 1:
            await delete_totp_entry(db_session=PgDB, user_id=user_id, totp_id=totp_id)
            return JSONResponse(
                content={"message": f"TOTP entry with ID {totp_id} deleted successfully for user {user_id}"},
                status_code=status.HTTP_200_OK
            )
        
    raise All_Exceptions(
        message="Unexpected error occurred while deleting TOTP entry",
        status_code=status.HTTP_410_GONE
    )


# Validate the TOTP code
@router.patch("/validate", response_class=JSONResponse, tags=["User Authentication", "2FA - TOTP"], summary="Validate the TOTP code")
async def user_validate_totp_code(request: Request, totp_code: str, PgDB: PostgresDep, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Validate the TOTP code
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

    available_totp_secrets: list[str] = await get_totp_secrets(db_session=PgDB, user_id=user_data["user_id"])

    # For each TOTP secret, verify the provided TOTP code
    for totp_secret in available_totp_secrets:
        # Create a TOTP object with the secret key
        totp = pyotp.TOTP(totp_secret)

        # Verify the TOTP code entered by the user
        if totp.verify(otp=totp_code, valid_window=1):
            # If the TOTP code is valid, update the cache to mark the user as authenticated
            user_data["authenticated"] = True
            await CacheDB.replace(
                key=session_id.encode("utf-8"),
                value=orjson.dumps(user_data),
                exptime=MAX_AGE_OF_CACHE
            )
            return JSONResponse(
                content={"message": "TOTP code validated successfully"},
                status_code=status.HTTP_200_OK
            )

    # If no valid TOTP code was found, return an error response
    await CacheDB.delete(session_id.encode("utf-8"))

    response = JSONResponse(
        content={"message": "Invalid TOTP code, please relogin to try again"},
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
