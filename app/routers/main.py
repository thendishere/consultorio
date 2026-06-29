from ..templates_config import templates
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user_optional, get_current_user, NotAuthenticatedException

router = APIRouter(tags=["main"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    if user.role in ("superadmin", "secretario"):
        return RedirectResponse(url="/agenda", status_code=302)
    return RedirectResponse(url="/medico", status_code=302)


@router.get("/secretario", response_class=HTMLResponse)
async def secretario_home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role not in ("superadmin", "secretario"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "proximamente.html", {"user": user, "seccion": "Secretaría"})


@router.get("/medico", response_class=HTMLResponse)
async def medico_home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role not in ("superadmin", "medico"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "proximamente.html", {"user": user, "seccion": "Agenda Médica"})
