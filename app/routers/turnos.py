from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.turno import Turno
from ..models.catalogo import Medico, Especialidad
from ..models.paciente import Paciente
from ..auth import get_current_user
from datetime import date, time
from typing import Optional

router = APIRouter(prefix="/turnos", tags=["turnos"])

ESTADOS = ["pendiente", "confirmado", "completado", "cancelado"]
PER_PAGE = 25


def _require_staff(request, db):
    user = get_current_user(request, db)
    if user.role not in ("superadmin", "secretario"):
        raise HTTPException(status_code=403)
    return user


def _parse_hora(valor: str) -> Optional[time]:
    if not valor or not valor.strip():
        return None
    try:
        parts = valor.strip().split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def _medicos_con_especialidades(db: Session):
    return db.query(Medico).filter(Medico.activo == True).join(Medico.user).order_by(Medico.id).all()


@router.get("", response_class=HTMLResponse)
async def listar(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    fecha_str = request.query_params.get("fecha", "")
    medico_id_str = request.query_params.get("medico_id", "")
    estado_filter = request.query_params.get("estado", "")
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    query = db.query(Turno)
    if fecha_str:
        try:
            query = query.filter(Turno.fecha == date.fromisoformat(fecha_str))
        except ValueError:
            pass
    if medico_id_str:
        try:
            query = query.filter(Turno.medico_id == int(medico_id_str))
        except ValueError:
            pass
    if estado_filter and estado_filter in ESTADOS:
        query = query.filter(Turno.estado == estado_filter)

    query = query.order_by(Turno.fecha.desc(), Turno.hora.desc())
    total = query.count()
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    turnos = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    medicos = _medicos_con_especialidades(db)

    return templates.TemplateResponse(request, "turnos/lista.html", {
        "user": user, "turnos": turnos, "medicos": medicos,
        "fecha_filter": fecha_str, "medico_id_filter": medico_id_str,
        "estado_filter": estado_filter, "estados": ESTADOS,
        "page": page, "total_pages": total_pages, "total": total,
        "saved": request.query_params.get("saved"),
    })


@router.get("/crear", response_class=HTMLResponse)
async def crear_page(request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    medicos = _medicos_con_especialidades(db)
    paciente_id = request.query_params.get("paciente_id", "")
    paciente = None
    if paciente_id:
        paciente = db.query(Paciente).filter(Paciente.id == int(paciente_id)).first()
    return templates.TemplateResponse(request, "turnos/form.html", {
        "user": user, "accion": "Nuevo", "medicos": medicos,
        "paciente_preselect": paciente, "estados": ESTADOS,
    })


@router.post("/crear", response_class=HTMLResponse)
async def crear(
    request: Request,
    paciente_id: str = Form(""),
    medico_id: str = Form(""),
    especialidad_id: str = Form(""),
    fecha: str = Form(""),
    hora: str = Form(""),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    medicos = _medicos_con_especialidades(db)
    errors = []

    if not paciente_id.strip():
        errors.append("Seleccioná un paciente.")
    if not medico_id.strip():
        errors.append("Seleccioná un médico.")
    if not fecha.strip():
        errors.append("La fecha es obligatoria.")
    if not hora.strip():
        errors.append("La hora es obligatoria.")

    hora_obj = _parse_hora(hora)
    if hora.strip() and not hora_obj:
        errors.append("Hora inválida.")

    fecha_obj = None
    if fecha.strip():
        try:
            fecha_obj = date.fromisoformat(fecha.strip())
        except ValueError:
            errors.append("Fecha inválida.")

    form_data = {
        "paciente_id": paciente_id, "medico_id": medico_id,
        "especialidad_id": especialidad_id, "fecha": fecha,
        "hora": hora, "notas": notas,
    }

    if errors:
        return templates.TemplateResponse(
            request, "turnos/form.html",
            {"user": user, "accion": "Nuevo", "medicos": medicos,
             "errors": errors, "form": form_data, "estados": ESTADOS},
            status_code=422,
        )

    paciente = db.query(Paciente).filter(Paciente.id == int(paciente_id)).first()
    if not paciente:
        errors.append("Paciente no encontrado.")
        return templates.TemplateResponse(
            request, "turnos/form.html",
            {"user": user, "accion": "Nuevo", "medicos": medicos,
             "errors": errors, "form": form_data, "estados": ESTADOS},
            status_code=422,
        )

    turno = Turno(
        paciente_id=int(paciente_id),
        medico_id=int(medico_id),
        especialidad_id=int(especialidad_id) if especialidad_id.strip() else None,
        fecha=fecha_obj,
        hora=hora_obj,
        estado="pendiente",
        notas=notas.strip() or None,
    )
    db.add(turno)
    db.commit()
    return RedirectResponse(url=f"/turnos/{turno.id}?saved=1", status_code=302)


@router.get("/{tid}", response_class=HTMLResponse)
async def ver(tid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "turnos/detalle.html", {
        "user": user, "turno": turno, "estados": ESTADOS,
        "saved": request.query_params.get("saved"),
    })


@router.post("/{tid}/estado", response_class=HTMLResponse)
async def cambiar_estado(
    tid: int,
    request: Request,
    estado: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    if estado in ESTADOS:
        turno.estado = estado
        db.commit()
    return RedirectResponse(url=f"/turnos/{tid}?saved=1", status_code=302)


@router.get("/{tid}/editar", response_class=HTMLResponse)
async def editar_page(tid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    medicos = _medicos_con_especialidades(db)
    return templates.TemplateResponse(request, "turnos/form.html", {
        "user": user, "accion": "Editar", "turno": turno,
        "medicos": medicos, "estados": ESTADOS,
    })


@router.post("/{tid}/editar", response_class=HTMLResponse)
async def editar(
    tid: int,
    request: Request,
    paciente_id: str = Form(""),
    medico_id: str = Form(""),
    especialidad_id: str = Form(""),
    fecha: str = Form(""),
    hora: str = Form(""),
    estado: str = Form("pendiente"),
    notas: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_staff(request, db)
    turno = db.query(Turno).filter(Turno.id == tid).first()
    if not turno:
        raise HTTPException(status_code=404)
    medicos = _medicos_con_especialidades(db)
    errors = []

    if not fecha.strip():
        errors.append("La fecha es obligatoria.")
    if not hora.strip():
        errors.append("La hora es obligatoria.")

    hora_obj = _parse_hora(hora)
    fecha_obj = None
    if fecha.strip():
        try:
            fecha_obj = date.fromisoformat(fecha.strip())
        except ValueError:
            errors.append("Fecha inválida.")

    if errors:
        return templates.TemplateResponse(
            request, "turnos/form.html",
            {"user": user, "accion": "Editar", "turno": turno,
             "medicos": medicos, "errors": errors, "estados": ESTADOS},
            status_code=422,
        )

    turno.paciente_id = int(paciente_id) if paciente_id.strip() else turno.paciente_id
    turno.medico_id = int(medico_id) if medico_id.strip() else turno.medico_id
    turno.especialidad_id = int(especialidad_id) if especialidad_id.strip() else None
    turno.fecha = fecha_obj
    turno.hora = hora_obj
    turno.estado = estado if estado in ESTADOS else turno.estado
    turno.notas = notas.strip() or None
    db.commit()
    return RedirectResponse(url=f"/turnos/{tid}?saved=1", status_code=302)
