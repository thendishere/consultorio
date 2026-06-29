from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models.paciente import Paciente
from ..auth import get_current_user
from datetime import date, datetime
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
    v = valor.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


PER_PAGE = 25


@router.get("", response_class=HTMLResponse)
async def listar(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    q = request.query_params.get("q", "").strip()
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    query = db.query(Paciente)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Paciente.apellido.ilike(like) |
            Paciente.nombre.ilike(like) |
            Paciente.dni.ilike(like)
        )
    query = query.order_by(Paciente.apellido, Paciente.nombre)
    total = query.count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    pacientes = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return templates.TemplateResponse(request, "pacientes/lista.html", {
        "user": user, "pacientes": pacientes, "q": q,
        "saved": request.query_params.get("saved"),
        "page": page, "total_pages": total_pages, "total": total,
        "per_page": PER_PAGE,
    })


@router.get("/buscar")
async def buscar_json(request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    q = request.query_params.get("q", "").strip()
    if not q:
        return JSONResponse([])
    like = f"%{q}%"
    pacientes = (
        db.query(Paciente)
        .filter(Paciente.apellido.ilike(like) | Paciente.nombre.ilike(like) | Paciente.dni.ilike(like))
        .order_by(Paciente.apellido, Paciente.nombre)
        .limit(10)
        .all()
    )
    return JSONResponse([{"id": p.id, "nombre": p.nombre, "apellido": p.apellido, "dni": p.dni} for p in pacientes])


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
        "fecha_nacimiento": fecha_nacimiento,
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
