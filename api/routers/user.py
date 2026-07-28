"""
This module provides User related API endpoints
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
    datetime,
    BytesIO,
    Request,
    logging,
    secrets,
    status,
    orjson,
    bcrypt,
    base64
)
from src.database import (
    replace_user_permissions_template,
    update_sso_session_active_status,
    get_user_template_permissions,
    get_basic_user_details_by_id,
    create_user_session_in_cache,
    delete_email_client_session,
    switch_email_client_session,
    check_backup_codes_for_user,
    get_email_client_sessions,
    get_organization_details,
    get_hierarchy_users_list,
    replace_user_permissions,
    check_user_name_exists,
    get_basic_user_details,
    replace_user_details,
    update_user_password,
    delete_app_session,
    delete_sso_session,
    get_domain_details,
    list_sso_sessions,
    get_app_sessions,
    replace_ui_info,
    create_new_user,
    delete_user,
    get_ui_info,
    MemcachedDep,
    PostgresDep
)
from src.main import (
    generate_notifications_jwt_token,
    clear_email_client_session_cache,
    has_required_permissions,
    retrieve_help_context,
    check_password_breach,
    validate_permissions,
    validate_recaptcha,
    send_notification,
    get_s3_file,
    put_s3_file,
    CurrentUser
)
from src.utils.models import All_Exceptions, AuthRequest, CreateUserForm, PasswdReset
from src.utils.base.constants import MAX_AGE_OF_CACHE, COOKIE_DOMAIN
from src.ai import open_ai_answer_user_query, deep_infra_generate_styling_by_text


# Router
router = APIRouter()

# OTP Constants
OTP_CODE_GENERATOR = lambda: ''.join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
OTP_EXPIRY_TIME = 60 * 2  # 2 minutes expiry for OTP


# Login to V3 Portal - Validate user credentials and Create a session
@router.post("/login", response_class=JSONResponse, tags=["User Authentication"], summary="Login to V3 Portal")
async def user_login_webmail(data: AuthRequest, CacheDB: MemcachedDep, PgDB: PostgresDep) -> JSONResponse:
    """
    Login to V3 Portal - Validate user credentials (Create a session)
    """
    if not validate_recaptcha(token=data.recaptcha_token):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Recaptcha validation failed - Are you a bot?"}
        )

    logging.info(f"User login attempt for {data.user_name}; Recaptcha validated successfully")

    # Get the user details from the database
    user_details = await get_basic_user_details(db_session=PgDB, user_name=data.user_name)
    logging.info(f"User details fetched from DB for {data.user_name}: {user_details}")

    # Check if organization is active
    users_org_details = await get_organization_details(
        db_session=PgDB,
        organization_id=user_details["organization_id"]
    )

    # Validate the password
    passwd_hash: str = user_details.pop("password_hash")
    if not bcrypt.checkpw(password=base64.b64decode(data.password), hashed_password=passwd_hash.encode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid credentials - Please check your password, its case sensitive"}
        )

    # Check if password is breached
    if check_password_breach(user_name=data.user_name, password=base64.b64decode(data.password).decode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "The password you are using has been exposed in a data breach, please change your password immediately to secure your account"}
        )

    # Generate Notifications JWT token for connections
    notifications_jwt_token: str = generate_notifications_jwt_token(
        organization_id=user_details["organization_id"],
        user_id=user_details["user_id"]
    )

    # Create a session in the cache
    session_id, csrf_token = await create_user_session_in_cache(
        cache_session=CacheDB,
        user_details={
            "user_id": user_details["user_id"],
            "display_name": user_details["display_name"],
            "primary_phone": user_details["primary_phone"],
            "user_email": user_details["user_email"],
            "user_name": user_details["user_name"],
            "organization_id": user_details["organization_id"],
            "permissions": user_details["permissions"],
            "organization_name": users_org_details["organization_name"],
            "parent_organization_id": users_org_details["parent_organization_id"],
            "organization_hierarchy_path": users_org_details["hierarchy_path"],
            "is_totp_2fa_active": user_details["is_totp_2fa_active"],
            "is_sms_2fa_active": user_details["is_sms_2fa_active"],
            "is_email_2fa_active": user_details["is_email_2fa_active"],
            "is_email_verified": user_details["is_email_verified"],
            "is_phone_verified": user_details["is_phone_verified"],
            # If any of the 2FA is active, then the user is not authenticated and 2FA(OTP) is required
            "authenticated": not (user_details["is_totp_2fa_active"] or user_details["is_sms_2fa_active"] or user_details["is_email_2fa_active"])
        }
    )

    # Backup Codes - If the user has backup codes, check if they have any valid codes left
    has_backup_codes, valid_backup_codes_count = await check_backup_codes_for_user(db_session=PgDB, user_id=user_details["user_id"])
    user_details["has_backup_codes"] = has_backup_codes
    user_details["valid_backup_codes_count"] = valid_backup_codes_count

    # Create a session as cookie and return the response
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Login successful", "details": user_details}
    )

    response.set_cookie(
        key="SESSION_ID",
        value=session_id,
        max_age=MAX_AGE_OF_CACHE,
        httponly=True,
        # Comment this following lines to test in local
        secure=True,
        samesite="strict",
        domain=COOKIE_DOMAIN
    )

    # Set the logged in status in the Cookie (for JS - to read)
    response.set_cookie(
        key="IS_SESSION_VALID",
        value="true",
        max_age=MAX_AGE_OF_CACHE,
        httponly=False,  # IMPORTANT: Let JS read it
        secure=True,
        samesite="strict",
        domain=COOKIE_DOMAIN
    )

    # Set the CSRF token and Notifications JWT token in the response header
    response.headers["X-CSRF-Token"] = csrf_token
    response.headers["X-Session-Expiry"] = str(MAX_AGE_OF_CACHE)
    response.headers["X-Notifications-Token"] = notifications_jwt_token
    # Allow Token and Expiry to be read by JS
    response.headers["Access-Control-Expose-Headers"] = "X-CSRF-Token, X-Session-Expiry, X-Notifications-Token"

    return response


# Logout from V3 Portal - Destroy the session and cookie
@router.delete("/logout", response_class=JSONResponse, tags=["User Authentication"], summary="Logout from V3 Portal")
async def user_logout_webmail(request: Request, CacheDB: MemcachedDep) -> JSONResponse:
    """
    Logout from V3 Portal - Destroy the session and cookie
    """
    session_id = request.cookies.get("SESSION_ID")
    if not session_id:
        raise All_Exceptions(message="Session ID not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    user_data_bytes = await CacheDB.get(session_id.encode("utf-8"))
    if user_data_bytes:
        user_details =  orjson.loads(user_data_bytes)
        if user_details["csrf_token"] != request.headers.get("X-CSRF-Token"):
            raise All_Exceptions(message="CSRF token mismatch", status_code=status.HTTP_401_UNAUTHORIZED)

    # Destroy the session in the cache
    await CacheDB.delete(key=session_id.encode("utf-8"))

    # Send response to delete the cookie
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Logout successful, session destroyed"}
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


# Validate the session
@router.get("/validate", response_class=JSONResponse, tags=["User Authentication"], summary="Validate the session ID")
async def user_validate_session(user: CurrentUser) -> JSONResponse:
    """
    Validate the session ID
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Session is valid",
            "user_name": user.user_name,
            "user_id": user.user_id,
            "organization_id": user.organization_id,
            "display_name": user.display_name,
            "permissions": user.permissions
        }
    )


# Check if user name is already taken
@router.get("/validate/user_name", response_class=JSONResponse, tags=["User Management"], summary="Check if user name is already taken")
async def user_check_user_name(user_name: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Check if user name is already taken
    """
    if not has_required_permissions(user_permissions=user.permissions, required_permissions=["user:create"]):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You do not have permission to check if the user name is available"}
        )

    does_user_exist: bool = await check_user_name_exists(db_session=PgDB, user_name=user_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "User name is taken, please choose a different user name" if does_user_exist else "User name is available for use",
            "user_name": user_name,
            "user_name_exists": does_user_exist
        }
    )


# Create a new user
@router.post("/create", response_class=JSONResponse, tags=["User Management"], summary="Create a new user")
async def user_create(data: CreateUserForm, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Create a new user
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:create"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=data.organization_id,
        user_id=None,
        db=PgDB
    )

    # Check if password is breached
    if check_password_breach(user_name=data.user_name, password=base64.b64decode(data.base64_password).decode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "The password you are trying to set for the new user has been exposed in a data breach, please choose a different password to secure the account"
            }
        )

    # Create a new user in the database
    await create_new_user(
        db_session=PgDB,
        user_name=data.user_name,
        display_name=data.display_name,
        user_email=data.user_email,
        primary_phone=data.primary_phone_number_with_country_code,
        password_hash=bcrypt.hashpw(base64.b64decode(data.base64_password), bcrypt.gensalt()).decode('utf-8'),
        user_details=data.user_details,
        is_active=data.activate,
        permissions_template=data.permissions_template,
        permissions=data.permissions,
        organization_id=data.organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": f"User created successfully, under the organization {data.organization_id}"}
    )


# Delete an existing user
@router.delete("/delete/{organization_id}", response_class=JSONResponse, tags=["User Management"], summary="Delete a user")
async def user_delete(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete a user - If the user is not the last one and is a parent of another user, then the user cannot be deleted
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:view", "user:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    await delete_user(db_session=PgDB, user_id=user_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "User deleted successfully"}
    )


# List all users associated with the organization
@router.get("/list/{organization_id}/{page}", response_class=JSONResponse, tags=["User Management"], summary="List all users under the organization")
async def users_list_all(page: int, limit: int, organization_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all users under the organization
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=None,
        db=PgDB
    )

    users_list_data, total_records_count = await get_hierarchy_users_list(
        db_session=PgDB,
        organization_id=organization_id,
        page=page,
        page_size=limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Users list fetched successfully",
            "users_list": users_list_data,
            "total_records_count": total_records_count,
            "page": page,
            "page_size": limit,
            "total_pages": (total_records_count // limit) + (1 if total_records_count % limit > 0 else 0)
        }
    )


# Replace the user details
@router.patch("/edit/{organization_id}", response_class=JSONResponse, tags=["User Management"], summary="Edit the user details")
async def replace_existing_user_details(
    is_mail_updated: bool, is_phone_updated: bool,
    organization_id: str, user_id: str, user_name: str,
    user_email: str, primary_phone: str, display_name: str,
    is_active: bool, user_details: dict, user: CurrentUser, PgDB: PostgresDep
) -> JSONResponse:
    """
    Replace the user details
    """
    if user.user_id != user_id:
        await validate_permissions(
            current_user_permissions=user.permissions,
            basic_permissions=["user:view", "user:edit"],
            organization_level_permissions=["organization:view"],
            current_user_organization_id=user.organization_id,
            accessed_organization_id=organization_id,
            user_id=user_id,
            db=PgDB
        )

    # Update the user details
    await replace_user_details(
        db_session=PgDB,
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        primary_phone=primary_phone,
        display_name=display_name,
        is_active=is_active,
        new_user_details=user_details,
        organization_id=organization_id,
        is_mail_updated=is_mail_updated,
        is_phone_updated=is_phone_updated
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "User details updated successfully"}
    )


# Change the user password (Direct password change, no 2FA)
@router.put("/password/{organization_id}", response_class=JSONResponse, tags=["User Security"], summary="Change the user password")
async def user_change_password(organization_id: str, data: PasswdReset, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Change the user password directly, for self password update, create a patch? or add in this same endpoint (Note: If self no need any permission)
    """
    if user.user_id != data.user_id:
        await validate_permissions(
            current_user_permissions=user.permissions,
            basic_permissions=["user:security:password:edit", "user:view"],
            organization_level_permissions=["organization:view"],
            current_user_organization_id=user.organization_id,
            accessed_organization_id=organization_id,
            user_id=data.user_id,
            db=PgDB
        )

    # Check if password is breached
    if check_password_breach(user_name=data.user_id, password=base64.b64decode(data.password).decode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "The password you are trying to set has been exposed in a data breach, please choose a different password to secure the account"}
        )

    # Change the password
    await update_user_password(
        db_session=PgDB,
        user_id=data.user_id,
        organization_id=organization_id,
        new_password_hash=bcrypt.hashpw(base64.b64decode(data.password), bcrypt.gensalt()).decode('utf-8')
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Password changed successfully"}
    )


# Change the user permissions
@router.put("/permissions/{organization_id}", response_class=JSONResponse, tags=["User Security"], summary="Change the user permissions")
async def user_change_permissions(organization_id: str, user_id: str, permissions: list[str], user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Change the user permissions
    """
    # If the user is trying to change their own permissions, then return a forbidden response
    if user.user_id == user_id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "You cannot change your own permissions, contact your administrator to update your permissions"}
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:permissions:edit", "user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Update the permissions
    await replace_user_permissions(
        db_session=PgDB,
        user_id=user_id,
        organization_id=organization_id,
        new_permissions=list(set(permissions))  # Ensure unique permissions
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "User permissions updated successfully"}
    )


# Update the user permissions template
@router.patch("/permissions/{organization_id}/template", response_class=JSONResponse, tags=["User Security"], summary="Update the user permissions template")
async def user_create_permissions_template(organization_id: str, user_id: str, permissions_template: dict, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Replace the user permissions templates with the new templates
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:permissions:template:edit", "user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Update the permissions template
    await replace_user_permissions_template(
        db_session=PgDB,
        user_id=user_id,
        organization_id=organization_id,
        new_permissions_template=permissions_template
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "User permissions template updated successfully"}
    )


# Get the user permissions template
@router.get("/permissions/{organization_id}/template", response_class=JSONResponse, tags=["User Security"], summary="Get the user permissions template")
async def user_get_permissions_template(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get the user permissions template
    """
    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:permissions:template:view", "user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Get the necessary details of the user for the permissions template from the database
    user_permissions_and_templates = await get_user_template_permissions(db_session=PgDB, user_id=user_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Requested user permissions template fetched successfully",
            "permissions_template": user_permissions_and_templates["permissions_template"]
        }
    )


# Get the user permissions
@router.get("/permissions/{organization_id}/all", response_class=JSONResponse, tags=["User Security"], summary="Get the user permissions")
async def user_get_permissions(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get the user permissions
    """
    if user.user_id == user_id:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Current user permissions fetched successfully",
                "permissions": user.permissions
            }
        )

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["user:security:permissions:view", "user:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=organization_id,
        user_id=user_id,
        db=PgDB
    )

    # Get the necessary details of the user for the permissions from the database
    user_permissions_and_templates = await get_user_template_permissions(db_session=PgDB, user_id=user_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Requested user permissions fetched successfully",
            "permissions": user_permissions_and_templates["permissions"]
        }
    )


# Get user details
@router.get("/details/{organization_id}/{user_id}", response_class=JSONResponse, tags=["User Management"], summary="Get user details")
async def user_get_details(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get user details by user ID
    """
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

    user_details = await get_basic_user_details_by_id(db_session=PgDB, user_id=user_id, organization_id=organization_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "User details fetched successfully",
            "user_details": user_details
        }
    )


# Update Profile Pic from S3
@router.post("/profile-photo/{organization_id}/{user_id}", response_class=JSONResponse, tags=["User Management"], summary="Update Profile Pic")
async def user_update_profile_pic(organization_id: str, file: UploadFile, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update the user profile picture
    """
    if user.user_id != user_id:
        await validate_permissions(
            current_user_permissions=user.permissions,
            basic_permissions=["user:view", "user:edit"],
            organization_level_permissions=["organization:view"],
            current_user_organization_id=user.organization_id,
            accessed_organization_id=organization_id,
            user_id=user_id,
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
        file_name=f"{user_id}/profile.png",
        file_type="image/png",
        file_content=file_data,
        organization_id=organization_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Profile picture updated successfully"}
    )


# Get the user profile pic from S3
@router.get("/profile-photo/{organization_id}/{user_id}", response_class=StreamingResponse, tags=["User Management"], summary="Get Profile Pic")
async def user_get_profile_pic(organization_id: str, user_id: str, user: CurrentUser, PgDB: PostgresDep) -> StreamingResponse:
    """
    Get the user profile picture
    """
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

    # Download the profile picture from S3
    file_data: bytes = get_s3_file(
        file_name=f"{user_id}/profile.png",
        organization_id=organization_id
    )

    return StreamingResponse(
        content=BytesIO(file_data),
        media_type="image/png",
        status_code=status.HTTP_200_OK,
        headers={"Content-Disposition": f"attachment; filename={user_id}_profile.png"}
    )


# Support from AI
@router.post("/support", response_class=JSONResponse, tags=["Support"], summary="Support from AI")
async def user_support_ai(data: dict, user: CurrentUser) -> JSONResponse:
    """
    Support from AI
    """
    if "query" not in data or not data["query"]:
        raise All_Exceptions(message="Query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST)

    query = str(data["query"]).strip()
    if len(query) < 30 or len(query) > 250:
        raise All_Exceptions(message="Query must be between 30 and 250 characters", status_code=status.HTTP_400_BAD_REQUEST)

    # Get the context for the user query
    context: str = retrieve_help_context(user_query=query)

    # Stream the response
    # return StreamingResponse(
    #     deep_infra_stream_user_query(
    #         query=query,
    #         context=context,
    #         user_name=user.display_name
    #     ),
    #     media_type="text/plain"
    # )

    ### Using OpenAI to answer the user query ###
    answer = open_ai_answer_user_query(context=context, query=query, user_name=user.display_name)

    ### Using DeepInfra to answer the user query ###
    # answer = deep_infra_answer_user_query(context=context, query=query, user_name=user.display_name)

    if not answer:
        raise All_Exceptions(
            message="Failed to get a response for the user query",
            status_code=status.HTTP_410_GONE
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "AI support response",
            "data": {
                "query": query,
                "user_name": user.display_name,
                "context": context,
                "answer": answer
            }
        }
    )


# UI Info - Store UI related data
@router.put("/ui/info", response_class=JSONResponse, tags=["User Management"], summary="Store UI related data")
async def user_store_ui_info(ui_info: dict, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Store UI related data for the user
    """
    if not ui_info or not isinstance(ui_info, dict):
        raise All_Exceptions(message="UI info must be a non-empty dictionary", status_code=status.HTTP_400_BAD_REQUEST)

    # Update the user UI info in the database
    await replace_ui_info(
        db_session=PgDB,
        user_id=user.user_id,
        ui_info=ui_info
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "UI info updated successfully"}
    )


# Get UI Info - Retrieve UI related data
@router.get("/ui/info", response_class=JSONResponse, tags=["User Management"], summary="Retrieve UI related data")
async def user_get_ui_info(user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Retrieve UI related data for the user
    """
    # Get the user UI info from the database
    ui_info = await get_ui_info(db_session=PgDB, user_id=user.user_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "UI info retrieved successfully",
            "ui_info": ui_info
        }
    )


# Get Email Client sessions
@router.get("/email/client/sessions/{domain_name}", response_class=JSONResponse, tags=["User Management"], summary="Get Email Client sessions")
async def user_get_email_client_sessions(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Get Email Client sessions for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    email_sessions = await get_email_client_sessions(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        size=size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Email sessions retrieved successfully",
            "email_sessions": email_sessions
        }
    )


# Switch Email Client session
@router.patch("/email/client/session/{domain_name}/{origin_ip}/{attempted_by}", response_class=JSONResponse, tags=["User Management"], summary="Switch Email Client session")
async def user_switch_email_client_session(domain_name: str, origin_ip: str, attempted_by: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Switch an Email Client session for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Clear the email client session cache if the session is being switched
    clear_email_client_session_cache(email_id=attempted_by, ip_address=origin_ip)

    # Switch the session
    await switch_email_client_session(db_session=PgDB, origin_ip=origin_ip, attempted_by=attempted_by, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Email Client session switched successfully"}
    )


# Delete the client session completely
@router.delete("/email/client/session/{domain_name}/{origin_ip}/{attempted_by}", response_class=JSONResponse, tags=["User Management"], summary="Delete Email Client session")
async def user_delete_email_client_session(domain_name: str, origin_ip: str, attempted_by: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an Email Client session for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Clear the email client session cache if the session is being denied
    clear_email_client_session_cache(email_id=attempted_by, ip_address=origin_ip)

    # Delete the session
    await delete_email_client_session(db_session=PgDB, origin_ip=origin_ip, attempted_by=attempted_by, domain_name=domain_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Email Client session deleted successfully"}
    )


# Generate HTML and CSS from user query
@router.post("/generate-style", response_class=JSONResponse, tags=["Support"], summary="Support from AI")
async def user_support_ai(data: dict, user: CurrentUser) -> JSONResponse:
    """
    Support from AI
    """
    if "query" not in data or not data["query"]:
        raise All_Exceptions(message="Query cannot be empty", status_code=status.HTTP_400_BAD_REQUEST)

    ### Using DeepInfra to answer the user query ###
    answer = deep_infra_generate_styling_by_text(query=data["query"])

    if not answer:
        raise All_Exceptions(
            message="Failed to get a response for the user query",
            status_code=status.HTTP_410_GONE
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "AI support response",
            "data": {
                "query": data["query"],
                "user_name": user.display_name,
                "answer": answer
            }
        }
    )


# List all App sessions
@router.get("/app/sessions/{domain_name}", response_class=JSONResponse, tags=["User Management"], summary="List all App sessions")
async def user_list_app_sessions(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all App sessions for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    app_sessions = await get_app_sessions(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        size=size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "App sessions retrieved successfully",
            "app_sessions": app_sessions
        }
    )


# Delete an App session
@router.delete("/app/session/{domain_name}/{session_id}", response_class=JSONResponse, tags=["User Management"], summary="Delete an App session")
async def user_delete_app_session(domain_name: str, session_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an App session for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Delete the session
    await delete_app_session(db_session=PgDB, domain_name=domain_name, session_id=session_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "App session deleted successfully"}
    )


# Start the Password Reset process
@router.post("/reset/password/{user_name}/init", response_class=JSONResponse, tags=["User Security"], summary="Start Password Reset process")
async def user_start_password_reset(user_name: str, verify_via: str, recaptcha_token: str, CacheDB: MemcachedDep, PgDB: PostgresDep) -> JSONResponse:
    """
    Start the Password Reset process by generating a reset token and sending it via email
    """
    # Validate reCAPTCHA token
    if not validate_recaptcha(token=recaptcha_token):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "reCAPTCHA validation failed, cannot initiate password reset"}
        )

    # Check if the user exists and is active along with verified email/phone based on the verification method
    user_details = await get_basic_user_details(db_session=PgDB, user_name=user_name)
    if not user_details["is_active"]:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "User is not active, cannot initiate password reset"}
        )
    
    if not user_details["is_email_verified"] and verify_via == "email":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User email is not verified, cannot initiate password reset via email"}
        )
    
    if not user_details["is_phone_verified"] and verify_via == "phone":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User phone is not verified, cannot initiate password reset via phone"}
        )

    otp: str = OTP_CODE_GENERATOR()

    # There are two ways to verify the user - email or phone
    match verify_via:
        # Initiate password reset via email
        case "email":
            send_notification(
                notification_type="email",
                to=user_details["user_email"],
                template_name="password_reset_otp",
                variables={
                    "name": user_details["display_name"],
                    "otp": otp,
                    "year": datetime.now().year
                }
            )

        # Initiate password reset via phone
        case "phone":
            send_notification(
                notification_type="sms",
                to=user_details["primary_phone"],
                template_name="password_reset_otp",
                variables={
                    "to": user_details["primary_phone"],
                    "otp": otp
                }
            )

        case _:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Invalid verification method, must be either 'email' or 'phone'"}
            )

    await CacheDB.set(
        key=f"password_reset:otp:{verify_via}:verify:{user_name}".encode("utf-8"),
        value=otp.encode("utf-8"),
        exptime=OTP_EXPIRY_TIME
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Password reset process initiated successfully, please check your {verify_via} for the OTP"}
    )


# Complete the Password Reset process
@router.post("/reset/password/{user_name}/complete", response_class=JSONResponse, tags=["User Security"], summary="Complete Password Reset process")
async def user_complete_password_reset(user_name: str, data: dict, CacheDB: MemcachedDep, PgDB: PostgresDep) -> JSONResponse:
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
    cached_otp_bytes = await CacheDB.get(f"password_reset:otp:{verify_via}:verify:{user_name}".encode("utf-8"))
    if not cached_otp_bytes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Password reset OTP has expired or not requested, please initiate the password reset process again"}
        )
    
    cached_otp: str = cached_otp_bytes.decode("utf-8")
    if entered_otp != cached_otp:
        await CacheDB.delete(f"password_reset:otp:{verify_via}:verify:{user_name}".encode("utf-8"))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid OTP provided, please try again"}
        )
    
    # Check if the new password is breached
    if check_password_breach(user_name=user_name, password=base64.b64decode(new_password_base64).decode("utf-8")):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "The new password you are trying to set has been exposed in a data breach, please choose a different password to secure the account"}
        )

    # Since OTP is valid, delete it from cache
    await CacheDB.delete(f"password_reset:otp:{verify_via}:verify:{user_name}".encode("utf-8"))

    # Update the password in the database
    user_details = await get_basic_user_details(db_session=PgDB, user_name=user_name)
    await update_user_password(
        db_session=PgDB,
        user_id=user_details["user_id"],
        organization_id=user_details["organization_id"],
        new_password_hash=bcrypt.hashpw(base64.b64decode(new_password_base64), bcrypt.gensalt()).decode('utf-8')
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Password has been reset successfully"}
    )


# List all SSO sessions
@router.get("/sso/sessions/{domain_name}", response_class=JSONResponse, tags=["User Management"], summary="List all SSO sessions")
async def user_list_sso_sessions(domain_name: str, page: int, size: int, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    List all SSO sessions for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:view"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    sso_sessions = await list_sso_sessions(
        db_session=PgDB,
        domain_name=domain_name,
        page=page,
        size=size
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "SSO sessions retrieved successfully",
            "sso_sessions": sso_sessions
        }
    )


# Delete an SSO session
@router.delete("/sso/session/{domain_name}/{session_id}", response_class=JSONResponse, tags=["User Management"], summary="Delete an SSO session")
async def user_delete_sso_session(domain_name: str, session_id: str, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Delete an SSO session for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:delete"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Delete the session
    await delete_sso_session(db_session=PgDB, domain_name=domain_name, session_id=session_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "SSO session deleted successfully"}
    )


# Update the SSO session status (active/inactive)
@router.patch("/sso/session/{domain_name}/{session_id}/status", response_class=JSONResponse, tags=["User Management"], summary="Update the SSO session status")
async def user_update_sso_session_status(domain_name: str, session_id: str, is_active: bool, user: CurrentUser, PgDB: PostgresDep) -> JSONResponse:
    """
    Update the SSO session status (active/inactive) for the user
    """
    domain_info = await get_domain_details(db_session=PgDB, domain_name=domain_name)

    await validate_permissions(
        current_user_permissions=user.permissions,
        basic_permissions=["session:edit"],
        organization_level_permissions=["organization:view"],
        current_user_organization_id=user.organization_id,
        accessed_organization_id=domain_info["managed_by"],
        user_id=None,
        db=PgDB
    )

    # Update the session status
    await update_sso_session_active_status(
        db_session=PgDB,
        domain_name=domain_name,
        session_id=session_id,
        is_active=is_active
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "SSO session status updated successfully"}
    )
