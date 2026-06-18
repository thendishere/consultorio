from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.catalogo import Medico, Especialidad, Disponibilidad
from ..auth import get_current_user
from datetime import time
from typing import List

router = APIRouter(prefix="/admin/medicos", tags=["medicos"])

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _require_superadmin(request, db):
    user = get_current_user(request, db)
    if user.role != "superadmin":
        raise HTTPException(status_code=403)
    return user


def _usuarios_sin_perfil(db: Session, excluir_id: int = None):
    """Usuarios con rol médico que aún no tienen perfil de médico."""
    query = db.query(User).filter(User.role == "medico")
    medicos_con_perfil = db.query(Medico.user_id)
    if excluir_id:
        medicos_con_perfil = medicos_con_perfil.filter(Medico.id != excluir_id)
    return query.filter(~User.id.in_(medicos_con_perfil)).all()


@router.get("", response_class=HTMLResponse)
async def listar(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    medicos = db.query(Medico).join(User).order_by(User.full_name).all()
    return templates.TemplateResponse(request, "admin/medicos/lista.html", {
        "user": user, "medicos": medicos,
        "saved": request.query_params.get("saved"),
    })


@router.get("/crear", response_class=HTMLResponse)
async def crear_page(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    usuarios = _usuarios_sin_perfil(db)
    especialidades = db.query(Especialidad).filter(Especialidad.activa == True).order_by(Especialidad.nombre).all()
    return templates.TemplateResponse(request, "admin/medicos/form.html", {
        "user": user, "accion": "Crear",
        "usuarios": usuarios, "especialidades": especialidades, "dias": DIAS,
    })


@router.post("/crear", response_class=HTMLResponse)
async def crear(
    request: Request,
    user_id: int = Form(...),
    matricula: str = Form(""),
    es_ecografo: str = Form("no"),
    especialidad_ids: List[int] = Form([]),
    db: Session = Depends(get_db),
):
    admin = _require_superadmin(request, db)
    usuarios = _usuarios_sin_perfil(db)
    especialidades = db.query(Especialidad).filter(Especialidad.activa == True).order_by(Especialidad.nombre).all()

    errors = []
    u = db.query(User).filter(User.id == user_id, User.role == "medico").first()
    if not u:
        errors.append("Usuario inválido.")
    if not es_ecografo == "si" and not especialidad_ids:
        errors.append("Asigná al menos una especialidad, o marcá al médico como ecógrafo.")

    if errors:
        return templates.TemplateResponse(
            request, "admin/medicos/form.html",
            {"user": admin, "accion": "Crear", "usuarios": usuarios,
             "especialidades": especialidades, "dias": DIAS, "errors": errors},
            status_code=422,
        )

    esps = db.query(Especialidad).filter(Especialidad.id.in_(especialidad_ids)).all()
    medico = Medico(
        user_id=user_id,
        matricula=matricula.strip() or None,
        es_ecografo=(es_ecografo == "si"),
        especialidades=esps,
    )
    db.add(medico)
    db.commit()
    return RedirectResponse(url=f"/admin/medicos/{medico.id}/disponibilidad", status_code=302)


@router.get("/{mid}/editar", response_class=HTMLResponse)
async def editar_page(mid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    medico = db.query(Medico).filter(Medico.id == mid).first()
    if not medico:
        raise HTTPException(status_code=404)
    usuarios = _usuarios_sin_perfil(db, excluir_id=mid)
    usuarios.append(medico.user)
    especialidades = db.query(Especialidad).filter(Especialidad.activa == True).order_by(Especialidad.nombre).all()
    esp_ids = [e.id for e in medico.especialidades]
    return templates.TemplateResponse(request, "admin/medicos/form.html", {
        "user": user, "accion": "Editar", "medico": medico,
        "usuarios": usuarios, "especialidades": especialidades,
        "esp_ids": esp_ids, "dias": DIAS,
    })


@router.post("/{mid}/editar", response_class=HTMLResponse)
async def editar(
    mid: int,
    request: Request,
    matricula: str = Form(""),
    es_ecografo: str = Form("no"),
    especialidad_ids: List[int] = Form([]),
    db: Session = Depends(get_db),
):
    admin = _require_superadmin(request, db)
    medico = db.query(Medico).filter(Medico.id == mid).first()
    if not medico:
        raise HTTPException(status_code=404)

    especialidades_all = db.query(Especialidad).filter(Especialidad.activa == True).order_by(Especialidad.nombre).all()
    errors = []
    if es_ecografo != "si" and not especialidad_ids:
        errors.append("Asigná al menos una especialidad, o marcá al médico como ecógrafo.")
    if errors:
        return templates.TemplateResponse(
            request, "admin/medicos/form.html",
            {"user": admin, "accion": "Editar", "medico": medico,
             "usuarios": [medico.user], "especialidades": especialidades_all,
             "esp_ids": especialidad_ids, "dias": DIAS, "errors": errors},
            status_code=422,
        )

    medico.matricula = matricula.strip() or None
    medico.es_ecografo = (es_ecografo == "si")
    medico.especialidades = db.query(Especialidad).filter(Especialidad.id.in_(especialidad_ids)).all()
    db.commit()
    return RedirectResponse(url="/admin/medicos?saved=1", status_code=302)


@router.post("/{mid}/toggle-activo")
async def toggle_activo(mid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    medico = db.query(Medico).filter(Medico.id == mid).first()
    if not medico:
        raise HTTPException(status_code=404)
    medico.activo = not medico.activo
    db.commit()
    return RedirectResponse(url="/admin/medicos?saved=1", status_code=302)


# ── Disponibilidad ─────────────────────────────────────────────────────────────

@router.get("/{mid}/disponibilidad", response_class=HTMLResponse)
async def disponibilidad_page(mid: int, request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    medico = db.query(Medico).filter(Medico.id == mid).first()
    if not medico:
        raise HTTPException(status_code=404)
    disps = db.query(Disponibilidad).filter(Disponibilidad.medico_id == mid).order_by(
        Disponibilidad.dia_semana, Disponibilidad.hora_inicio
    ).all()
    return templates.TemplateResponse(request, "admin/medicos/disponibilidad.html", {
        "user": user, "medico": medico, "disps": disps, "dias": DIAS,
        "saved": request.query_params.get("saved"),
    })


@router.post("/{mid}/disponibilidad/agregar")
async def agregar_disponibilidad(
    mid: int,
    request: Request,
    especialidad_id: int = Form(...),
    dia_semana: int = Form(...),
    hora_inicio: str = Form(...),
    hora_fin: str = Form(...),
    db: Session = Depends(get_db),
):
    _require_superadmin(request, db)
    medico = db.query(Medico).filter(Medico.id == mid).first()
    if not medico:
        raise HTTPException(status_code=404)

    try:
        hi = time.fromisoformat(hora_inicio)
        hf = time.fromisoformat(hora_fin)
    except ValueError:
        raise HTTPException(status_code=422, detail="Hora inválida.")
    if hf <= hi:
        raise HTTPException(status_code=422, detail="La hora de fin debe ser posterior a la de inicio.")

    disp = Disponibilidad(
        medico_id=mid,
        especialidad_id=especialidad_id,
        dia_semana=dia_semana,
        hora_inicio=hi,
        hora_fin=hf,
    )
    db.add(disp)
    db.commit()
    return RedirectResponse(url=f"/admin/medicos/{mid}/disponibilidad?saved=1", status_code=302)


@router.post("/{mid}/disponibilidad/{did}/eliminar")
async def eliminar_disponibilidad(mid: int, did: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    disp = db.query(Disponibilidad).filter(Disponibilidad.id == did, Disponibilidad.medico_id == mid).first()
    if disp:
        db.delete(disp)
        db.commit()
    return RedirectResponse(url=f"/admin/medicos/{mid}/disponibilidad?saved=1", status_code=302)
