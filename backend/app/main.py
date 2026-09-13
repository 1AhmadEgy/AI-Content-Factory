from __future__ import annotations

import hashlib
import hmac
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.jobs import build_router as build_job_router
from .api.projects import build_router as build_project_router
from .api.v1.assets import build_router as build_assets_router
from .api.v1.batches import build_router as build_batch_router
from .api.v1.best_take import build_router as build_best_take_router
