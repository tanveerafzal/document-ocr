import time
import logging
import threading
from datetime import datetime
from typing import Callable
from queue import Queue, Empty

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import get_db_session, RequestLog, init_db

logger = logging.getLogger(__name__)

# Max size for response body storage (to avoid storing large binary data)
MAX_RESPONSE_BODY_SIZE = 10000  # 10KB

# Background logging queue and worker
_log_queue: Queue = Queue()
_worker_started = False


def _db_worker():
    """Background worker that writes logs to database."""
    logger.info("DB worker thread started")
    while True:
        try:
            log_data = _log_queue.get(timeout=5)
            if log_data is None:  # Shutdown signal
                break

            try:
                db = get_db_session()
                log_entry = RequestLog(**log_data)
                db.add(log_entry)
                db.commit()
                db.close()
                logger.info(f"Logged request: {log_data['method']} {log_data['path']} -> {log_data['status_code']}")
            except Exception as e:
                logger.error(f"Failed to write log to database: {e}", exc_info=True)

        except Empty:
            continue  # No items in queue, keep waiting


def _start_worker():
    """Start the background worker thread."""
    global _worker_started
    if not _worker_started:
        logger.info("Starting DB logging worker thread...")
        thread = threading.Thread(target=_db_worker, daemon=True)
        thread.start()
        _worker_started = True
        logger.info("DB logging worker thread started")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses to the database (async/non-blocking)."""

    def __init__(self, app, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json", "/"]
        self._db_initialized = False

    def _ensure_db(self):
        """Ensure database is initialized and worker is running."""
        if not self._db_initialized:
            try:
                init_db()
                _start_worker()
                self._db_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
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

        # Queue log entry for background writing (non-blocking)
        self._ensure_db()
        log_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow(),
            "method": request.method,
            "path": request.url.path,
            "query_params": query_params,
            "client_ip": client_ip,
            "user_agent": user_agent[:500] if user_agent else None,
            "request_content_type": content_type[:100] if content_type else None,
            "request_filename": request_filename,
            "request_file_size_kb": request_file_size_kb,
            "status_code": response.status_code,
            "response_body": response_body,
            "processing_time_ms": round(processing_time_ms, 2)
        }
        _log_queue.put_nowait(log_data)
        logger.info(f"Queued log: {request.method} {request.url.path} (queue size: {_log_queue.qsize()})")

        return response
