"""FastAPI assembly; one process owns the local queue and its temporary session."""

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.middleware.trustedhost import TrustedHostMiddleware

from suite.conversion import LibreOfficeConverter
from suite.services.documents import DocumentService, ServiceError
from suite.settings import Settings


WEB_ROOT = Path(__file__).resolve().parent


class BodyTooLarge(Exception):
    pass


class SameOriginMiddleware:
    """Reject browser writes originating from another site in the local application."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in {"POST", "DELETE"}:
            headers = dict(scope["headers"])
            origin = headers.get(b"origin")
            host = headers.get(b"host", b"")
            expected = scope["scheme"].encode() + b"://" + host
            if origin is not None and origin != expected:
                return await JSONResponse({"detail": "Origem da solicitação não permitida."}, 403)(scope, receive, send)
        await self.app(scope, receive, send)


class UploadLimitMiddleware:
    """Limit the entire request before multipart spooling, including chunked uploads."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            declared = int(headers.get(b"content-length", b"0"))
            if declared < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"detail": "Tamanho da requisição inválido."}, 400)(scope, receive, send)
        if declared > self.max_bytes:
            return await self.reject(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                raise BodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except BodyTooLarge:
            await self.reject(scope, receive, send)

    async def reject(self, scope, receive, send):
        await JSONResponse({"detail": "O envio excede o limite total permitido."}, 413)(scope, receive, send)


class JobFileResponse(Response):
    """Keep a download lease until transmission ends, including on disconnect."""

    def __init__(self, service: DocumentService, job_id: str, file_index: int | None):
        super().__init__()
        self.service = service
        self.job_id = job_id
        self.file_index = file_index

    async def __call__(self, scope, receive, send):
        with self.service.download(self.job_id, self.file_index) as (path, filename):
            media_type = "application/pdf" if self.file_index is not None else "application/zip"
            await FileResponse(path, filename=filename, media_type=media_type,
                               headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})(scope, receive, send)


def create_app(settings: Settings | None = None, converter: LibreOfficeConverter | None = None) -> FastAPI:
    settings = settings or Settings.local()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = converter or LibreOfficeConverter(settings.libreoffice_path, timeout=settings.conversion_timeout)
        service = DocumentService(settings, engine)
        app.state.documents = service

        async def sweep():
            while True:
                await asyncio.sleep(60)
                await run_in_threadpool(service.cleanup)

        cleaner = asyncio.create_task(sweep())
        try:
            yield
        finally:
            cleaner.cancel()
            with suppress(asyncio.CancelledError):
                await cleaner
            await run_in_threadpool(service.close)

    app = FastAPI(title="Document Suite", lifespan=lifespan)
    app.add_middleware(UploadLimitMiddleware, max_bytes=settings.max_total_bytes + 1024 * 1024)
    app.add_middleware(SameOriginMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=WEB_ROOT / "templates")

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code, headers={"Cache-Control": "no-store"})

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/word-to-pdf", response_class=HTMLResponse)
    async def word_to_pdf(request: Request):
        return templates.TemplateResponse(request=request, name="word-to-pdf.html", context={"settings": settings})

    @app.get("/api/status")
    async def status(request: Request):
        return {"ok": True, "conversion_available": request.app.state.documents.converter.executable is not None,
                "limits": {"max_files": settings.max_files, "max_file_bytes": settings.max_file_bytes,
                           "max_total_bytes": settings.max_total_bytes, "retention_seconds": settings.retention_seconds,
                           "max_pdf_pages": settings.max_pdf_pages}}

    async def accept_job(request: Request, operation: str):
        service = request.app.state.documents
        # Count and part limits apply before any conversion task is created.
        async with request.form(max_files=settings.max_files, max_fields=0) as form:
            uploads = form.getlist("files")
            if not uploads or len(uploads) != len(form.multi_items()) or any(not isinstance(item, UploadFile) for item in uploads):
                raise ServiceError("Selecione documentos no campo de arquivos.")
            job = service.create(operation)
            try:
                filenames = await run_in_threadpool(service.save_sources, job, [(item.filename, item.file) for item in uploads])
                snapshot = await run_in_threadpool(service.submit, job, filenames)
            except BaseException:
                # An interrupted upload must not leave a slot or documents behind.
                if job.state == "uploading":
                    service.discard_upload(job)
                raise
        return JSONResponse(snapshot, status_code=202, headers={"Cache-Control": "no-store"})

    upload_schema = {"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["files"], "properties": {"files": {"type": "array", "items": {"type": "string", "format": "binary"}}}
    }}}}}

    @app.post("/api/jobs/word-to-pdf", status_code=202, openapi_extra=upload_schema,
              summary="Converter DOCX em PDFs individuais", tags=["Tools"])
    async def create_word_job(request: Request):
        return await accept_job(request, "word-to-pdf")

    @app.post("/api/jobs/merge-pdfs", status_code=202, openapi_extra=upload_schema,
              summary="Juntar PDFs na ordem enviada", tags=["Tools"])
    async def create_merge_job(request: Request):
        return await accept_job(request, "merge-pdfs")

    @app.post("/api/jobs/convert-and-merge", status_code=202, openapi_extra=upload_schema,
              summary="Converter DOCX e juntar com PDFs na ordem enviada", tags=["Tools"])
    async def create_combined_job(request: Request):
        return await accept_job(request, "convert-and-merge")

    @app.get("/api/jobs/{job_id}")
    def job_status(request: Request, job_id: str):
        return JSONResponse(request.app.state.documents.snapshot(job_id), headers={"Cache-Control": "no-store"})

    @app.get("/api/jobs/{job_id}/files/{file_index}")
    def download_file(request: Request, job_id: str, file_index: int):
        return JobFileResponse(request.app.state.documents, job_id, file_index)

    @app.get("/api/jobs/{job_id}/archive")
    def download_archive(request: Request, job_id: str):
        return JobFileResponse(request.app.state.documents, job_id, None)

    @app.delete("/api/jobs/{job_id}", status_code=204)
    def delete_job(request: Request, job_id: str):
        request.app.state.documents.delete(job_id)
        return Response(status_code=204)

    return app
