from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..database import get_db
from ..models.turno import Turno
from ..models.catalogo import Medico, Especialidad
from ..models.paciente import Paciente
from ..auth import get_current_user
from datetime import date, datetime
from decimal import Decimal
import json

router = APIRouter(prefix="/agenda", tags=["agenda"])

ESTADOS = ["agendado", "en_atencion", "cobrado", "sobreturno", "no_vino", "baja"]

ESTADO_LABEL = {
    "agendado":    "Agendado",
    "en_atencion": "En atención",
    "cobrado":     "Cobrado",
    "sobreturno":  "Sobreturno",
    "no_vino":     "No vino",
    "baja":        "Baja",
}


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


def _turno_dict(t: Turno) -> dict:
    return {
        "id": t.id,
        "hora": t.hora.strftime("%H:%M"),
        "paciente_id": t.paciente_id,
        "apellido": t.paciente.apellido,
        "nombre": t.paciente.nombre,
        "especialidad": t.especialidad.nombre if t.especialidad else None,
        "especialidad_id": t.especialidad_id,
        "estado": t.estado,
        "medio_pago": t.medio_pago,
        "monto_cobrado": int(t.monto_cobrado) if t.monto_cobrado is not None else None,
        "notas": t.notas or "",
        "orden": t.orden or 0,
    }


def _medico_dict(m: Medico) -> dict:
    return {
        "id": m.id,
        "nombre": m.user.full_name or m.user.username,
        "especialidades": [{"id": e.id, "nombre": e.nombre, "precio": int(e.precio) if e.precio else 0} for e in m.especialidades],
    }


@router.get("", response_class=HTMLResponse)
async def agenda_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    fecha = _fecha_param(request)
    medicos = db.query(Medico).filter(Medico.activo == True).join(Medico.user).order_by(Medico.id).all()
    medicos_json = json.dumps([_medico_dict(m) for m in medicos])
    return templates.TemplateResponse(request, "agenda/index.html", {
        "user": user,
        "fecha": fecha,
        "medicos_json": medicos_json,
        "estados": ESTADOS,
        "estado_label": ESTADO_LABEL,
    })


@router.get("/data")
async def agenda_data(request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    fecha = _fecha_param(request)
    turnos = (
        db.query(Turno)
        .filter(Turno.fecha == fecha)
        .order_by(Turno.medico_id, Turno.orden, Turno.hora)
        .all()
    )
    data = {}
    for t in turnos:
        mid = str(t.medico_id)
        if mid not in data:
            data[mid] = []
        data[mid].append(_turno_dict(t))
    return JSONResponse(data)


@router.post("/turno")
async def crear_turno(request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    body = await request.json()
    fecha_str = body.get("fecha", "")
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Fecha inválida")

    from datetime import time as dtime
    hora_str = body.get("hora", "")
    try:
        h, m = hora_str.split(":")
        hora = dtime(int(h), int(m))
    except Exception:
        raise HTTPException(status_code=422, detail="Hora inválida")

    paciente_id = body.get("paciente_id")
    medico_id = body.get("medico_id")
    if not paciente_id or not medico_id:
        raise HTTPException(status_code=422, detail="Paciente y médico requeridos")

    max_orden = db.query(Turno).filter(Turno.fecha == fecha, Turno.medico_id == medico_id).count()

    turno = Turno(
        paciente_id=int(paciente_id),
        medico_id=int(medico_id),
        especialidad_id=int(body["especialidad_id"]) if body.get("especialidad_id") else None,
        fecha=fecha,
        hora=hora,
        estado="agendado",
        orden=max_orden,
        notas=body.get("notas", "").strip() or None,
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return JSONResponse(_turno_dict(turno))


@router.patch("/turno/{tid}")
async def editar_turno(tid: int, request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    body = await request.json()

    if "hora" in body:
        from datetime import time as dtime
        try:
            h, m = body["hora"].split(":")
            turno.hora = dtime(int(h), int(m))
        except Exception:
            pass
    if "paciente_id" in body:
        turno.paciente_id = int(body["paciente_id"])
    if "especialidad_id" in body:
        turno.especialidad_id = int(body["especialidad_id"]) if body["especialidad_id"] else None
    if "notas" in body:
        turno.notas = body["notas"].strip() or None
    if "estado" in body and body["estado"] in ESTADOS:
        turno.estado = body["estado"]
    if "orden" in body:
        turno.orden = int(body["orden"])

    db.commit()
    db.refresh(turno)
    return JSONResponse(_turno_dict(turno))


@router.post("/turno/{tid}/cobrar")
async def cobrar_turno(tid: int, request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    body = await request.json()
    turno.estado = "cobrado"
    turno.medio_pago = body.get("medio_pago", "efectivo")
    monto = body.get("monto_cobrado")
    turno.monto_cobrado = Decimal(str(monto)) if monto is not None else None
    db.commit()
    db.refresh(turno)
    return JSONResponse(_turno_dict(turno))


@router.delete("/turno/{tid}")
async def eliminar_turno(tid: int, request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    db.delete(turno)
    db.commit()
    return JSONResponse({"ok": True})


@router.patch("/turno/{tid}/orden")
async def reordenar(tid: int, request: Request, db: Session = Depends(get_db)):
    _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    body = await request.json()
    turno.orden = int(body.get("orden", 0))
    db.commit()
    return JSONResponse({"ok": True})
