"""Text input and PNG responses; QR content is never written to disk."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from starlette.concurrency import run_in_threadpool

from suite.qr.generation import MAX_CAPTION_LENGTH, MAX_TEXT_BYTES
from suite.services.documents import ServiceError
from suite.services.qr_codes import QrCodeService


def qr_router(templates):
    router = APIRouter()
    service = QrCodeService()

    @router.get("/qr-code", response_class=HTMLResponse)
    async def qr_page(request: Request):
        return templates.TemplateResponse(request=request, name="qr-code.html", context={
            "max_text_bytes": MAX_TEXT_BYTES, "max_caption_length": MAX_CAPTION_LENGTH,
        })

    schema = {"requestBody": {"required": True, "content": {"application/json": {"schema": {
        "type": "object", "required": ["text"], "additionalProperties": False, "properties": {
            "text": {"type": "string", "description": f"Até {MAX_TEXT_BYTES} bytes em UTF-8."},
            "caption": {"type": "string", "maxLength": MAX_CAPTION_LENGTH, "default": ""},
        }
    }}}}}

    @router.post("/api/qr-code", tags=["Tools"], summary="Gerar QR Code estático em PNG", openapi_extra=schema,
                 response_class=Response, responses={200: {"content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}}})
    async def create_qr_code(request: Request):
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            raise ServiceError("Envie o conteúdo como JSON.", 415)
        try:
            data = await request.json()
        except (ValueError, RecursionError) as exc:
            raise ServiceError("O conteúdo JSON é inválido.") from exc
        if not isinstance(data, dict) or set(data) - {"text", "caption"}:
            raise ServiceError("Envie apenas os campos text e caption.")
        png = await run_in_threadpool(service.generate, data.get("text"), data.get("caption", ""))
        return Response(png, media_type="image/png", headers={
            "Content-Disposition": 'attachment; filename="qr-code.png"',
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        })

    return router
