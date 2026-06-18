from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models.catalogo import Especialidad
from ..auth import get_current_user

router = APIRouter(prefix="/admin/especialidades", tags=["especialidades"])


def _require_superadmin(request, db):
    user = get_current_user(request, db)
    if user.role != "superadmin":
        raise HTTPException(status_code=403)
    return user


@router.get("", response_class=HTMLResponse)
async def listar(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    especialidades = db.query(Especialidad).order_by(Especialidad.nombre).all()
    return templates.TemplateResponse(request, "admin/especialidades/lista.html", {
        "user": user,
        "especialidades": especialidades,
        "saved": request.query_params.get("saved"),
    })


@router.get("/crear", response_class=HTMLResponse)
async def crear_page(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    return templates.TemplateResponse(request, "admin/especialidades/form.html", {
        "user": user, "accion": "Crear",
    })


@router.post("/crear", response_class=HTMLResponse)
async def crear(
    request: Request,
    nombre: str = Form(""),
    duracion_turno: int = Form(20),
    db: Session = Depends(get_db),
):
    user = _require_superadmin(request, db)
    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    if duracion_turno <= 0:
        errors.append("La duración debe ser mayor a 0 minutos.")

    if errors:
        return templates.TemplateResponse(
            request, "admin/especialidades/form.html",
            {"user": user, "accion": "Crear", "errors": errors,
             "form": {"nombre": nombre, "duracion_turno": duracion_turno}},
            status_code=422,
        )

    try:
        db.add(Especialidad(nombre=nombre.strip(), duracion_turno=duracion_turno))
        db.commit()
    except IntegrityError:
        db.rollback()
        errors.append("Ya existe una especialidad con ese nombre.")
        return templates.TemplateResponse(
            request, "admin/especialidades/form.html",
            {"user": user, "accion": "Crear", "errors": errors,
             "form": {"nombre": nombre, "duracion_turno": duracion_turno}},
            status_code=422,
        )
    return RedirectResponse(url="/admin/especialidades?saved=1", status_code=302)


@router.get("/{eid}/editar", response_class=HTMLResponse)
async def editar_page(eid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    esp = db.query(Especialidad).filter(Especialidad.id == eid).first()
    if not esp:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/especialidades/form.html", {
        "user": user, "accion": "Editar", "esp": esp,
    })


@router.post("/{eid}/editar", response_class=HTMLResponse)
async def editar(
    eid: int,
    request: Request,
    nombre: str = Form(""),
    duracion_turno: int = Form(20),
    db: Session = Depends(get_db),
):
    user = _require_superadmin(request, db)
    esp = db.query(Especialidad).filter(Especialidad.id == eid).first()
    if not esp:
        raise HTTPException(status_code=404)

    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    if duracion_turno <= 0:
        errors.append("La duración debe ser mayor a 0 minutos.")
    if errors:
        return templates.TemplateResponse(
            request, "admin/especialidades/form.html",
            {"user": user, "accion": "Editar", "esp": esp, "errors": errors},
            status_code=422,
        )

    esp.nombre = nombre.strip()
    esp.duracion_turno = duracion_turno
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "admin/especialidades/form.html",
            {"user": user, "accion": "Editar", "esp": esp,
             "errors": ["Ya existe una especialidad con ese nombre."]},
            status_code=422,
        )
    return RedirectResponse(url="/admin/especialidades?saved=1", status_code=302)


@router.post("/{eid}/toggle-activa")
async def toggle_activa(eid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    esp = db.query(Especialidad).filter(Especialidad.id == eid).first()
    if not esp:
        raise HTTPException(status_code=404)
    esp.activa = not esp.activa
    db.commit()
    return RedirectResponse(url="/admin/especialidades?saved=1", status_code=302)


@router.post("/{eid}/eliminar")
async def eliminar(eid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    esp = db.query(Especialidad).filter(Especialidad.id == eid).first()
    if not esp:
        raise HTTPException(status_code=404)
    db.delete(esp)
    db.commit()
    return RedirectResponse(url="/admin/especialidades?saved=1", status_code=302)
