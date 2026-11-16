"""Public project pages independent of document processing."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from suite.qr.generation import generate_png
from suite.services.documents import ServiceError


def site_router(templates, site_settings):
    router = APIRouter()
    payload = site_settings.pix_payload
    png = generate_png(payload) if payload else None

    @router.get("/support/pix.png", response_class=Response, include_in_schema=False)
    async def pix_image():
        if png is None:
            raise ServiceError("O QR Code de doação não está disponível.", 404)
        return Response(png, media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @router.get("/contact", response_class=HTMLResponse)
    async def contact(request: Request):
        return templates.TemplateResponse(request=request, name="contact.html", headers={"Cache-Control": "no-store"})

    @router.get("/support", response_class=HTMLResponse)
    async def support(request: Request):
        return templates.TemplateResponse(request=request, name="support.html", headers={"Cache-Control": "no-store"})

    return router
