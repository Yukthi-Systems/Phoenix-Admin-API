"""
This is the main app file which contains all the endpoints of the API
This file is used to run the API
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
    CORSMiddleware,
    JSONResponse,
    FastAPI,
    Request,
    logging
)
from src.utils.base.constants import ALLOWED_ORIGINS
from src.utils.models import All_Exceptions
from src.database import lifespan
from .routers import *


# Initialization
app = FastAPI(
    title="V3 - Mail Service Portal API",
    description="Admin panel API for the V3 Mail Service Portal",
    version="1.9.0-phoenix-release",
    # docs_url=None,
    # redoc_url=None,
    docs_url="/docs",
    redoc_url="/redoc",
    include_in_schema=True,
    lifespan=lifespan
)

# Add CROCS middle ware to allow cross origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Exception handler for wrong input
@app.exception_handler(All_Exceptions)
async def input_data_exception_handler(request: Request, exc: All_Exceptions):
    logging.error(
        msg=f"API Exception occurred: {exc.status_code} - {exc.message}",
        extra={
            "traceback_id": exc.traceback_id,
            "request_details": request.headers,
            "client_ip": request.client.host,
            "endpoint": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": f"Oops! {exc.message}", "traceback_id": exc.traceback_id}
    )


#    Endpoints    #
app.include_router(router=crm_router, prefix="/crm")
app.include_router(router=api_router, prefix="/api")
app.include_router(router=user_router, prefix="/user")
app.include_router(router=logs_router, prefix="/logs")
app.include_router(router=chat_router, prefix="/chat")
app.include_router(router=totp_router, prefix="/2fa/totp")
app.include_router(router=server_router, prefix="/server")
app.include_router(router=domain_router, prefix="/domain")
app.include_router(router=mailbox_router, prefix="/mailbox")
app.include_router(router=caution_router, prefix="/caution")
app.include_router(router=files_conf_router, prefix="/files")
app.include_router(router=imap_sync_router, prefix="/imap-sync")
app.include_router(router=dashboard_router, prefix="/dashboard")
app.include_router(router=phone_auth_router, prefix="/2fa/phone")
app.include_router(router=email_auth_router, prefix="/2fa/email")
app.include_router(router=disclaimer_router, prefix="/disclaimer")
app.include_router(router=department_router, prefix="/department")
app.include_router(router=backup_code_router, prefix="/2fa/backup")
app.include_router(router=maintenance_router, prefix="/maintenance")
app.include_router(router=ticketing_router, prefix="/support/tickets")
app.include_router(router=organization_router, prefix="/organization")
app.include_router(router=email_identity_router, prefix="/identities")
app.include_router(router=general_policy_router, prefix="/policy/general")
app.include_router(router=filters_policy_router, prefix="/policy/filters")
app.include_router(router=forwarding_policy_router, prefix="/policy/forwarding")
app.include_router(router=attachment_policy_router, prefix="/policy/attachments")
app.include_router(router=restriction_policy_router, prefix="/policy/restrictions")
app.include_router(router=distribution_policy_router, prefix="/policy/distribution")
