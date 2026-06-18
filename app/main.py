from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from .database import engine
from .routers import auth, main as main_router, admin, especialidades, medicos
from .auth import NotAuthenticatedException
from .csrf import set_csrf_cookie, validate_csrf
import secrets, re

_templates = Jinja2Templates(directory="app/templates")

app = FastAPI(
    title="Consultorio de la Amistad",
    version="1.0.0",
)

_CSRF_EXEMPT = {"/auth/login", "/auth/token"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path not in _CSRF_EXEMPT:
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive

            content_type = request.headers.get("content-type", "")
            form_token = ""
            if "application/x-www-form-urlencoded" in content_type:
                from urllib.parse import parse_qs
                parsed = parse_qs(body.decode("utf-8", errors="replace"))
                form_token = parsed.get("csrf_token", [""])[0]
            elif "multipart/form-data" in content_type:
                decoded = body.decode("utf-8", errors="replace")
                m = re.search(r'name="csrf_token"\r\n\r\n([^\r\n]+)', decoded)
                form_token = m.group(1) if m else ""

            try:
                validate_csrf(request, form_token)
            except HTTPException:
                return _templates.TemplateResponse(request, "403.html", {}, status_code=403)

        response = await call_next(request)
        if "csrf_token" not in request.cookies:
            token = secrets.token_hex(32)
            set_csrf_cookie(response, token)
        return response


app.add_middleware(CSRFMiddleware)


@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse(url=f"/auth/login?next={exc.next_url}", status_code=302)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return _templates.TemplateResponse(request, "404.html", {}, status_code=404)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(main_router.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(especialidades.router)
app.include_router(medicos.router)
