from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.turno import Turno, GastoCaja
from ..auth import get_current_user
from datetime import date, datetime
from decimal import Decimal

router = APIRouter(prefix="/caja", tags=["caja"])


def _require_staff(request, db):
    user = get_current_user(request, db)
    if user.role not in ("superadmin", "secretario"):
        raise HTTPException(status_code=403)
    return user


def _fecha_param(request: Request) -> date:
    val = request.query_params.get("fecha", "")
    try:
        return date.fromisoformat(val)
    except ValueError:
        return date.today()


@router.get("", response_class=HTMLResponse)
async def caja_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    fecha = _fecha_param(request)

    cobros = (
        db.query(Turno)
        .filter(Turno.fecha == fecha, Turno.estado == "cobrado", Turno.monto_cobrado != None)
        .order_by(Turno.hora)
        .all()
    )
    gastos = db.query(GastoCaja).filter(GastoCaja.fecha == fecha).order_by(GastoCaja.created_at).all()

    efectivo = sum(int(t.monto_cobrado) for t in cobros if t.medio_pago == "efectivo")
    transferencias = sum(int(t.monto_cobrado) for t in cobros if t.medio_pago == "transferencia")
    total_gastos = sum(int(g.monto) for g in gastos)
    efectivo_esperado = efectivo - total_gastos

    return templates.TemplateResponse(request, "caja/index.html", {
        "user": user,
        "fecha": fecha,
        "cobros": cobros,
        "gastos": gastos,
        "efectivo": efectivo,
        "transferencias": transferencias,
        "total_gastos": total_gastos,
        "efectivo_esperado": efectivo_esperado,
        "saved": request.query_params.get("saved"),
    })


@router.post("/gasto", response_class=HTMLResponse)
async def agregar_gasto(
    request: Request,
    descripcion: str = Form(""),
    monto: str = Form(""),
    fecha_str: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        fecha = date.today()
    try:
        monto_dec = Decimal(monto.replace(",", ".").replace(" ", ""))
    except Exception:
        monto_dec = Decimal("0")

    gasto = GastoCaja(
        descripcion=descripcion.strip() or "Gasto",
        monto=monto_dec,
        fecha=fecha,
        user_id=user.id,
    )
    db.add(gasto)
    db.commit()
    return RedirectResponse(url=f"/caja?fecha={fecha}&saved=1", status_code=302)


@router.post("/gasto/{gid}/eliminar")
async def eliminar_gasto(gid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    gasto = db.query(GastoCaja).filter(GastoCaja.id == gid).first()
    if not gasto:
        raise HTTPException(status_code=404)
    fecha = gasto.fecha
    db.delete(gasto)
    db.commit()
    return RedirectResponse(url=f"/caja?fecha={fecha}", status_code=302)
