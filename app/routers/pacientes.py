from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models.paciente import Paciente
from ..auth import get_current_user
from datetime import date
from typing import Optional

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


def _require_staff(request, db):
    user = get_current_user(request, db)
    if user.role not in ("superadmin", "secretario"):
        raise HTTPException(status_code=403)
    return user


def _parse_fecha(valor: str) -> Optional[date]:
    if not valor or not valor.strip():
        return None
    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        return None


@router.get("", response_class=HTMLResponse)
async def listar(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    q = request.query_params.get("q", "").strip()
    query = db.query(Paciente)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Paciente.apellido.ilike(like) |
            Paciente.nombre.ilike(like) |
            Paciente.dni.ilike(like)
        )
    pacientes = query.order_by(Paciente.apellido, Paciente.nombre).all()
    return templates.TemplateResponse(request, "pacientes/lista.html", {
        "user": user, "pacientes": pacientes, "q": q,
        "saved": request.query_params.get("saved"),
    })


@router.get("/crear", response_class=HTMLResponse)
async def crear_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    return templates.TemplateResponse(request, "pacientes/form.html", {
        "user": user, "accion": "Nuevo",
    })


@router.post("/crear", response_class=HTMLResponse)
async def crear(
    request: Request,
    nombre: str = Form(""),
    apellido: str = Form(""),
    dni: str = Form(""),
    fecha_nacimiento: str = Form(""),
    telefono: str = Form(""),
    whatsapp: str = Form(""),
    email: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    if not apellido.strip():
        errors.append("El apellido es obligatorio.")

    form_data = {
        "nombre": nombre, "apellido": apellido, "dni": dni,
        "fecha_nacimiento": fecha_nacimiento, "telefono": telefono,
        "whatsapp": whatsapp, "email": email, "notas": notas,
    }

    if errors:
        return templates.TemplateResponse(
            request, "pacientes/form.html",
            {"user": user, "accion": "Nuevo", "errors": errors, "form": form_data},
            status_code=422,
        )

    try:
        paciente = Paciente(
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            dni=dni.strip() or None,
            fecha_nacimiento=_parse_fecha(fecha_nacimiento),
            telefono=telefono.strip() or None,
            whatsapp=whatsapp.strip() or None,
            email=email.strip() or None,
            notas=notas.strip() or None,
        )
        db.add(paciente)
        db.commit()
    except IntegrityError:
        db.rollback()
        errors.append("Ya existe un paciente con ese DNI.")
        return templates.TemplateResponse(
            request, "pacientes/form.html",
            {"user": user, "accion": "Nuevo", "errors": errors, "form": form_data},
            status_code=422,
        )
    return RedirectResponse(url=f"/pacientes/{paciente.id}?saved=1", status_code=302)


@router.get("/{pid}", response_class=HTMLResponse)
async def ver(pid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    paciente = db.query(Paciente).filter(Paciente.id == pid).first()
    if not paciente:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "pacientes/detalle.html", {
        "user": user, "paciente": paciente,
        "saved": request.query_params.get("saved"),
    })


@router.get("/{pid}/editar", response_class=HTMLResponse)
async def editar_page(pid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    paciente = db.query(Paciente).filter(Paciente.id == pid).first()
    if not paciente:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "pacientes/form.html", {
        "user": user, "accion": "Editar", "paciente": paciente,
    })


@router.post("/{pid}/editar", response_class=HTMLResponse)
async def editar(
    pid: int,
    request: Request,
    nombre: str = Form(""),
    apellido: str = Form(""),
    dni: str = Form(""),
    fecha_nacimiento: str = Form(""),
    telefono: str = Form(""),
    whatsapp: str = Form(""),
    email: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    paciente = db.query(Paciente).filter(Paciente.id == pid).first()
    if not paciente:
        raise HTTPException(status_code=404)

    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    if not apellido.strip():
        errors.append("El apellido es obligatorio.")
    if errors:
        return templates.TemplateResponse(
            request, "pacientes/form.html",
            {"user": user, "accion": "Editar", "paciente": paciente, "errors": errors},
            status_code=422,
        )

    paciente.nombre = nombre.strip()
    paciente.apellido = apellido.strip()
    paciente.dni = dni.strip() or None
    paciente.fecha_nacimiento = _parse_fecha(fecha_nacimiento)
    paciente.telefono = telefono.strip() or None
    paciente.whatsapp = whatsapp.strip() or None
    paciente.email = email.strip() or None
    paciente.notas = notas.strip() or None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "pacientes/form.html",
            {"user": user, "accion": "Editar", "paciente": paciente,
             "errors": ["Ya existe un paciente con ese DNI."]},
            status_code=422,
        )
    return RedirectResponse(url=f"/pacientes/{pid}?saved=1", status_code=302)
