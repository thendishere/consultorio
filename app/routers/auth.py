from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import authenticate_user, create_access_token, get_current_user_optional

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/", status_code=302)
    next_url = request.query_params.get("next", "/")
    return templates.TemplateResponse(request, "auth/login.html", {"next": next_url, "hide_footer": True})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    password = password.strip()
    if not email.strip() or not password:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Completá el correo y la contraseña.", "next": next, "form": {"email": email}, "hide_footer": True},
            status_code=422,
        )

    user = authenticate_user(db, email.strip().lower(), password)
    if not user:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Email o contraseña incorrectos.", "next": next, "form": {"email": email}, "hide_footer": True},
            status_code=401,
        )
    if not user.is_active:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Tu cuenta está desactivada. Contactá al administrador.", "next": next, "hide_footer": True},
            status_code=401,
        )

    token = create_access_token(data={"sub": user.username})

    # Redirigir según rol
    if next and next != "/":
        redirect_to = next
    elif user.role == "superadmin":
        redirect_to = "/admin"
    elif user.role == "secretario":
        redirect_to = "/secretario"
    else:
        redirect_to = "/medico"

    response = RedirectResponse(url=redirect_to, status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
