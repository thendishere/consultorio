from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.catalogo import TipoProcedimiento, Especialidad
from ..auth import get_current_user
from decimal import Decimal, InvalidOperation

router = APIRouter(prefix="/admin/especialidades/{eid}/procedimientos", tags=["procedimientos"])


def _require_superadmin(request, db):
    user = get_current_user(request, db)
    if user.role != "superadmin":
        raise HTTPException(status_code=403)
    return user


def _get_esp(eid: int, db: Session):
    esp = db.query(Especialidad).filter(Especialidad.id == eid).first()
    if not esp:
        raise HTTPException(status_code=404)
    return esp


def _parse_precio(valor: str):
    try:
        p = Decimal(valor.replace(",", ".").strip())
        if p < 0:
            return None, "El precio no puede ser negativo."
        return p, None
    except (InvalidOperation, AttributeError):
        return None, "El precio debe ser un número válido."


@router.get("", response_class=HTMLResponse)
async def listar(eid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    esp = _get_esp(eid, db)
    procs = db.query(TipoProcedimiento).filter(
        TipoProcedimiento.especialidad_id == eid
    ).order_by(TipoProcedimiento.nombre).all()
    return templates.TemplateResponse(request, "admin/procedimientos/lista.html", {
        "user": user, "esp": esp, "procs": procs,
        "saved": request.query_params.get("saved"),
    })


@router.get("/crear", response_class=HTMLResponse)
async def crear_page(eid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    esp = _get_esp(eid, db)
    return templates.TemplateResponse(request, "admin/procedimientos/form.html", {
        "user": user, "esp": esp, "accion": "Agregar",
    })


@router.post("/crear", response_class=HTMLResponse)
async def crear(
    eid: int,
    request: Request,
    nombre: str = Form(""),
    precio_str: str = Form("", alias="precio"),
    db: Session = Depends(get_db),
):
    user = _require_superadmin(request, db)
    esp = _get_esp(eid, db)
    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    precio, err = _parse_precio(precio_str)
    if err:
        errors.append(err)
    if errors:
        return templates.TemplateResponse(
            request, "admin/procedimientos/form.html",
            {"user": user, "esp": esp, "accion": "Agregar", "errors": errors,
             "form": {"nombre": nombre, "precio": precio_str}},
            status_code=422,
        )
    db.add(TipoProcedimiento(nombre=nombre.strip().upper(), precio=precio, especialidad_id=eid))
    db.commit()
    return RedirectResponse(url=f"/admin/especialidades/{eid}/procedimientos?saved=1", status_code=302)


@router.get("/{pid}/editar", response_class=HTMLResponse)
async def editar_page(eid: int, pid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    esp = _get_esp(eid, db)
    proc = db.query(TipoProcedimiento).filter(TipoProcedimiento.id == pid, TipoProcedimiento.especialidad_id == eid).first()
    if not proc:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/procedimientos/form.html", {
        "user": user, "esp": esp, "accion": "Editar", "proc": proc,
    })


@router.post("/{pid}/editar", response_class=HTMLResponse)
async def editar(
    eid: int, pid: int,
    request: Request,
    nombre: str = Form(""),
    precio_str: str = Form("", alias="precio"),
    db: Session = Depends(get_db),
):
    user = _require_superadmin(request, db)
    esp = _get_esp(eid, db)
    proc = db.query(TipoProcedimiento).filter(TipoProcedimiento.id == pid, TipoProcedimiento.especialidad_id == eid).first()
    if not proc:
        raise HTTPException(status_code=404)
    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    precio, err = _parse_precio(precio_str)
    if err:
        errors.append(err)
    if errors:
        return templates.TemplateResponse(
            request, "admin/procedimientos/form.html",
            {"user": user, "esp": esp, "accion": "Editar", "proc": proc, "errors": errors},
            status_code=422,
        )
    proc.nombre = nombre.strip().upper()
    proc.precio = precio
    db.commit()
    return RedirectResponse(url=f"/admin/especialidades/{eid}/procedimientos?saved=1", status_code=302)


@router.post("/{pid}/toggle-activo")
async def toggle_activo(eid: int, pid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    proc = db.query(TipoProcedimiento).filter(TipoProcedimiento.id == pid, TipoProcedimiento.especialidad_id == eid).first()
    if not proc:
        raise HTTPException(status_code=404)
    proc.activo = not proc.activo
    db.commit()
    return RedirectResponse(url=f"/admin/especialidades/{eid}/procedimientos?saved=1", status_code=302)


@router.post("/{pid}/eliminar")
async def eliminar(eid: int, pid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    proc = db.query(TipoProcedimiento).filter(TipoProcedimiento.id == pid, TipoProcedimiento.especialidad_id == eid).first()
    if not proc:
        raise HTTPException(status_code=404)
    db.delete(proc)
    db.commit()
    return RedirectResponse(url=f"/admin/especialidades/{eid}/procedimientos?saved=1", status_code=302)
