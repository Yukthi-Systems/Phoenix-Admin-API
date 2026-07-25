"""
This file has all the necessary libraries for the project to run
any new library should be added here and imported in the respective files
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


# FastAPI libraries
from fastapi import FastAPI, Request, status, Response, Depends, APIRouter, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Object data modeling libraries
from pydantic import BaseModel, Field
from botocore.config import Config
from openai import OpenAI
from enum import Enum
import boto3

# DB libraries
from typing import Annotated, AsyncGenerator, Optional, TypeAlias, List
from contextlib import asynccontextmanager
import clickhouse_connect
import aiomcache
import requests
import asyncpg

# other libraries
from datetime import datetime, timezone, date, timedelta
from threading import Thread
from functools import wraps
from io import BytesIO
import hashlib
import secrets
import base64
import orjson
import bcrypt
import string
import pyotp
import time
import pika
import json
import uuid
import jwt
import re
import os

# Configure logging
from src.utils.base.constants import LOG_LEVEL, LOG_FILE_PATH
from src.utils.base.log_utils import configure_return_logger

logging = configure_return_logger(LOG_LEVEL=LOG_LEVEL, LOG_FILE_PATH=LOG_FILE_PATH)
