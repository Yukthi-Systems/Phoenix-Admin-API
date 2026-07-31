"""
This module provides API Basic Information related endpoints
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

# Router
router = APIRouter()


# Get API Version Information
@router.get("/version", response_class=JSONResponse, tags=["API Info"], summary="Get API Version Information")
async def get_api_version_info() -> JSONResponse:
    """
    Get API Version Information
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "api_name": "V3 - Mail Service Portal API",
            "version": "1.8.1",
            "version_full": "1.8.1-phoenix-release",
            "code_name": "Phoenix Release",
            "description": "V3 - Advanced Mail Service Portal for Enterprise Solutions",
            "updated_at": "2026-07-31T07:25:25.777777+05:30"
            # Run >>> from datetime import datetime; from zoneinfo import ZoneInfo; datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
         }
    )


# Get API Health Check
@router.get("/health", response_class=JSONResponse, tags=["API Info"], summary="Get API Health Check Status")
async def get_api_health_check() -> JSONResponse:
    """
    Get API Health Check Status
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "OK",
            "message": "API is running smoothly"
        }
    )


# Get Server Time
@router.get("/time", response_class=JSONResponse, tags=["API Info"], summary="Get Server Time (UTC and Local)")
async def get_server_time_full() -> JSONResponse:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "utc": datetime.now(ZoneInfo("UTC")).isoformat(),
            "ist": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        }
    )
