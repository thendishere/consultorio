from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.turno import Turno, GastoCaja
from ..models.catalogo import Medico
from ..auth import get_current_user
from datetime import date
from calendar import monthrange

router = APIRouter(prefix="/reportes", tags=["reportes"])


def _require_staff(request, db):
    user = get_current_user(request, db)
    if user.role not in ("superadmin", "secretario"):
        raise HTTPException(status_code=403)
    return user


@router.get("", response_class=HTMLResponse)
async def reportes_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    hoy = date.today()
    try:
        desde = date.fromisoformat(request.query_params.get("desde", ""))
    except ValueError:
        desde = date(hoy.year, hoy.month, 1)
    try:
        hasta = date.fromisoformat(request.query_params.get("hasta", ""))
    except ValueError:
        ultimo = monthrange(hoy.year, hoy.month)[1]
        hasta = date(hoy.year, hoy.month, ultimo)

    cobros = (
        db.query(Turno)
        .filter(
            Turno.fecha >= desde,
            Turno.fecha <= hasta,
            Turno.estado == "cobrado",
            Turno.monto_cobrado != None,
        )
        .all()
    )

    gastos = (
        db.query(GastoCaja)
        .filter(GastoCaja.fecha >= desde, GastoCaja.fecha <= hasta)
        .all()
    )

    medicos = db.query(Medico).filter(Medico.activo == True).join(Medico.user).all()

    # agrupar por médico
    por_medico = {}
    for m in medicos:
        por_medico[m.id] = {
            "nombre": m.user.full_name or m.user.username,
            "atendidos": 0,
            "facturado": 0,
        }
    for t in cobros:
        if t.medico_id in por_medico:
            por_medico[t.medico_id]["atendidos"] += 1
            por_medico[t.medico_id]["facturado"] += int(t.monto_cobrado)

    rows = [v for v in por_medico.values() if v["atendidos"] > 0]
    for r in rows:
        r["medico_70"] = round(r["facturado"] * 0.7)
        r["clinica_30"] = r["facturado"] - r["medico_70"]

    total_fact = sum(r["facturado"] for r in rows)
    total_med  = sum(r["medico_70"] for r in rows)
    total_cli  = sum(r["clinica_30"] for r in rows)
    total_pac  = sum(r["atendidos"] for r in rows)
    total_gastos = sum(int(g.monto) for g in gastos)
    queda_clinica = total_cli - total_gastos

    return templates.TemplateResponse(request, "reportes/index.html", {
        "user": user,
        "desde": desde, "hasta": hasta,
        "rows": rows,
        "total_fact": total_fact, "total_med": total_med,
        "total_cli": total_cli, "total_pac": total_pac,
        "total_gastos": total_gastos, "queda_clinica": queda_clinica,
    })
