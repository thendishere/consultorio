from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models.catalogo import TipoEcografia
from ..auth import get_current_user
from decimal import Decimal, InvalidOperation

router = APIRouter(prefix="/admin/ecografias", tags=["ecografias"])


def _require_superadmin(request, db):
    user = get_current_user(request, db)
    if user.role != "superadmin":
        raise HTTPException(status_code=403)
    return user


def _parse_precio(valor: str):
    try:
        p = Decimal(valor.replace(",", ".").strip())
        if p < 0:
            return None, "El precio no puede ser negativo."
        return p, None
    except (InvalidOperation, AttributeError):
        return None, "El precio debe ser un número válido."


@router.get("", response_class=HTMLResponse)
async def listar(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    tipos = db.query(TipoEcografia).order_by(TipoEcografia.nombre).all()
    return templates.TemplateResponse(request, "admin/ecografias/lista.html", {
        "user": user, "tipos": tipos,
        "saved": request.query_params.get("saved"),
    })


@router.get("/crear", response_class=HTMLResponse)
async def crear_page(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    return templates.TemplateResponse(request, "admin/ecografias/form.html", {
        "user": user, "accion": "Crear",
    })


@router.post("/crear", response_class=HTMLResponse)
async def crear(
    request: Request,
    nombre: str = Form(""),
    precio_str: str = Form("", alias="precio"),
    db: Session = Depends(get_db),
):
    user = _require_superadmin(request, db)
    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    precio, err = _parse_precio(precio_str)
    if err:
        errors.append(err)

    if errors:
        return templates.TemplateResponse(
            request, "admin/ecografias/form.html",
            {"user": user, "accion": "Crear", "errors": errors,
             "form": {"nombre": nombre, "precio": precio_str}},
            status_code=422,
        )

    try:
        db.add(TipoEcografia(nombre=nombre.strip(), precio=precio))
        db.commit()
    except IntegrityError:
        db.rollback()
        errors.append("Ya existe un tipo de ecografía con ese nombre.")
        return templates.TemplateResponse(
            request, "admin/ecografias/form.html",
            {"user": user, "accion": "Crear", "errors": errors,
             "form": {"nombre": nombre, "precio": precio_str}},
            status_code=422,
        )
    return RedirectResponse(url="/admin/ecografias?saved=1", status_code=302)


@router.get("/{tid}/editar", response_class=HTMLResponse)
async def editar_page(tid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    tipo = db.query(TipoEcografia).filter(TipoEcografia.id == tid).first()
    if not tipo:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/ecografias/form.html", {
        "user": user, "accion": "Editar", "tipo": tipo,
    })


@router.post("/{tid}/editar", response_class=HTMLResponse)
async def editar(
    tid: int,
    request: Request,
    nombre: str = Form(""),
    precio_str: str = Form("", alias="precio"),
    db: Session = Depends(get_db),
):
    user = _require_superadmin(request, db)
    tipo = db.query(TipoEcografia).filter(TipoEcografia.id == tid).first()
    if not tipo:
        raise HTTPException(status_code=404)

    errors = []
    if not nombre.strip():
        errors.append("El nombre es obligatorio.")
    precio, err = _parse_precio(precio_str)
    if err:
        errors.append(err)
    if errors:
        return templates.TemplateResponse(
            request, "admin/ecografias/form.html",
            {"user": user, "accion": "Editar", "tipo": tipo, "errors": errors},
            status_code=422,
        )

    tipo.nombre = nombre.strip()
    tipo.precio = precio
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "admin/ecografias/form.html",
            {"user": user, "accion": "Editar", "tipo": tipo,
             "errors": ["Ya existe un tipo de ecografía con ese nombre."]},
            status_code=422,
        )
    return RedirectResponse(url="/admin/ecografias?saved=1", status_code=302)


@router.post("/{tid}/toggle-activo")
async def toggle_activo(tid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    tipo = db.query(TipoEcografia).filter(TipoEcografia.id == tid).first()
    if not tipo:
        raise HTTPException(status_code=404)
    tipo.activo = not tipo.activo
    db.commit()
    return RedirectResponse(url="/admin/ecografias?saved=1", status_code=302)


@router.post("/{tid}/eliminar")
async def eliminar(tid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    tipo = db.query(TipoEcografia).filter(TipoEcografia.id == tid).first()
    if not tipo:
        raise HTTPException(status_code=404)
    db.delete(tipo)
    db.commit()
    return RedirectResponse(url="/admin/ecografias?saved=1", status_code=302)
