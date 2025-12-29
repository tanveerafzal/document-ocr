import time
import logging
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import get_db_session, RequestLog, init_db

logger = logging.getLogger(__name__)

# Max size for response body storage (to avoid storing large binary data)
MAX_RESPONSE_BODY_SIZE = 10000  # 10KB


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses to the database."""

    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.exclude_exact = ["/"]  # Exact match only
        self._db_initialized = False

    def _ensure_db(self):
        """Ensure database is initialized."""
        if not self._db_initialized:
            try:
                init_db()
                self._db_initialized = True
                logger.info("Database initialized for request logging")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths (prefix match)
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Skip logging for exact match paths
        if request.url.path in self.exclude_exact:
            return await call_next(request)

        # Generate request ID
        request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        start_time = time.time()

        # Capture request info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        query_params = str(request.query_params) if request.query_params else None

        # Get file info from multipart form data
        request_filename = None
        request_file_size_kb = None
        content_type = request.headers.get("content-type", "")

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Capture response body for JSON responses (not binary)
        response_body = None
        response_content_type = response.headers.get("content-type", "")

        if "application/json" in response_content_type:
            # Read and reconstruct response body
            body_parts = []
            async for chunk in response.body_iterator:
                body_parts.append(chunk)

            body_bytes = b"".join(body_parts)
            response_body_str = body_bytes.decode("utf-8", errors="replace")

            # Truncate if too large
            if len(response_body_str) <= MAX_RESPONSE_BODY_SIZE:
                response_body = response_body_str
            else:
                response_body = response_body_str[:MAX_RESPONSE_BODY_SIZE] + "... [truncated]"

            # Reconstruct response with the body
            response = Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        # Try to extract file info from form data
        if "multipart/form-data" in content_type:
            content_length = request.headers.get("content-length")
            if content_length:
                request_file_size_kb = int(content_length) / 1024

        # Write log entry to database (synchronous for Cloud Run compatibility)
        self._ensure_db()
        try:
            db = get_db_session()
            log_entry = RequestLog(
                request_id=request_id,
                timestamp=datetime.utcnow(),
                method=request.method,
                path=request.url.path,
                query_params=query_params,
                client_ip=client_ip,
                user_agent=user_agent[:500] if user_agent else None,
                request_content_type=content_type[:100] if content_type else None,
                request_filename=request_filename,
                request_file_size_kb=request_file_size_kb,
                status_code=response.status_code,
                response_body=response_body,
                processing_time_ms=round(processing_time_ms, 2)
            )
            db.add(log_entry)
            db.commit()
            db.close()
            logger.info(f"Logged: {request.method} {request.url.path} -> {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

        return response
