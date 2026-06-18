from ..templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..auth import get_current_user, hash_password
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_superadmin(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return user


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    stats = {
        "medicos":     db.query(func.count(User.id)).filter(User.role == "medico").scalar(),
        "secretarios": db.query(func.count(User.id)).filter(User.role == "secretario").scalar(),
        "activos":     db.query(func.count(User.id)).filter(User.is_active == True).scalar(),
        "inactivos":   db.query(func.count(User.id)).filter(User.is_active == False).scalar(),
    }
    usuarios_recientes = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "user": user, "stats": stats, "usuarios_recientes": usuarios_recientes,
    })


# ── Usuarios ───────────────────────────────────────────────────────────────────

@router.get("/usuarios", response_class=HTMLResponse)
async def usuarios(request: Request, q: str = "", rol: str = "", db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    query = db.query(User).filter(User.role != "superadmin")
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(User.full_name.ilike(like) | User.email.ilike(like))
    if rol in ("medico", "secretario"):
        query = query.filter(User.role == rol)
    users = query.order_by(User.role, User.full_name).all()
    return templates.TemplateResponse(request, "admin/usuarios.html", {
        "user": user, "users": users, "q": q, "rol": rol,
        "saved": request.query_params.get("saved"),
    })


@router.get("/usuarios/crear", response_class=HTMLResponse)
async def crear_usuario_page(request: Request, db: Session = Depends(get_db)):
    user = _require_superadmin(request, db)
    return templates.TemplateResponse(request, "admin/crear_usuario.html", {"user": user})


@router.post("/usuarios/crear", response_class=HTMLResponse)
async def crear_usuario(
    request: Request,
    full_name: str = Form(""),
    email: str = Form(""),
    username: str = Form(""),
    whatsapp: str = Form(""),
    role: str = Form("secretario"),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = _require_superadmin(request, db)
    errors = []

    if not full_name.strip():
        errors.append("El nombre completo es obligatorio.")
    if not email.strip():
        errors.append("El correo es obligatorio.")
    if not username.strip() or len(username.strip()) < 3:
        errors.append("El usuario debe tener al menos 3 caracteres.")
    if role not in ("secretario", "medico"):
        errors.append("Rol inválido.")
    if not password or len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")

    form_data = {
        "full_name": full_name, "email": email,
        "username": username, "whatsapp": whatsapp, "role": role,
    }

    if errors:
        return templates.TemplateResponse(
            request, "admin/crear_usuario.html",
            {"user": admin, "errors": errors, "form": form_data},
            status_code=422,
        )

    nuevo = User(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        username=username.strip().lower(),
        whatsapp=whatsapp.strip() or None,
        role=role,
        hashed_password=hash_password(password),
    )
    try:
        db.add(nuevo)
        db.commit()
    except IntegrityError:
        db.rollback()
        errors.append("El nombre de usuario o email ya está en uso.")
        return templates.TemplateResponse(
            request, "admin/crear_usuario.html",
            {"user": admin, "errors": errors, "form": form_data},
            status_code=422,
        )

    return RedirectResponse(url="/admin/usuarios?saved=1", status_code=302)


@router.get("/usuarios/{uid}/editar", response_class=HTMLResponse)
async def editar_usuario_page(uid: int, request: Request, db: Session = Depends(get_db)):
    admin = _require_superadmin(request, db)
    u = db.query(User).filter(User.id == uid).first()
    if not u or u.role == "superadmin":
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "admin/editar_usuario.html", {"user": admin, "u": u})


@router.post("/usuarios/{uid}/editar", response_class=HTMLResponse)
async def editar_usuario(
    uid: int,
    request: Request,
    full_name: str = Form(""),
    email: str = Form(""),
    username: str = Form(""),
    whatsapp: str = Form(""),
    role: str = Form("secretario"),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    admin = _require_superadmin(request, db)
    u = db.query(User).filter(User.id == uid).first()
    if not u or u.role == "superadmin":
        raise HTTPException(status_code=404)

    errors = []
    if not full_name.strip():
        errors.append("El nombre completo es obligatorio.")
    if not email.strip():
        errors.append("El correo es obligatorio.")
    if not username.strip() or len(username.strip()) < 3:
        errors.append("El usuario debe tener al menos 3 caracteres.")
    if role not in ("secretario", "medico"):
        errors.append("Rol inválido.")
    if password and len(password) < 8:
        errors.append("La nueva contraseña debe tener al menos 8 caracteres.")

    if errors:
        return templates.TemplateResponse(
            request, "admin/editar_usuario.html",
            {"user": admin, "u": u, "errors": errors},
            status_code=422,
        )

    u.full_name = full_name.strip()
    u.email = email.strip().lower()
    u.username = username.strip().lower()
    u.whatsapp = whatsapp.strip() or None
    u.role = role
    if password:
        u.hashed_password = hash_password(password)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors.append("El nombre de usuario o email ya está en uso por otro usuario.")
        return templates.TemplateResponse(
            request, "admin/editar_usuario.html",
            {"user": admin, "u": u, "errors": errors},
            status_code=422,
        )

    return RedirectResponse(url="/admin/usuarios?saved=1", status_code=302)


@router.post("/usuarios/{uid}/toggle-activo")
async def toggle_activo(uid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    u = db.query(User).filter(User.id == uid).first()
    if not u or u.role == "superadmin":
        raise HTTPException(status_code=404)
    u.is_active = not u.is_active
    db.commit()
    return RedirectResponse(url="/admin/usuarios?saved=1", status_code=302)


@router.post("/usuarios/{uid}/eliminar")
async def eliminar_usuario(uid: int, request: Request, db: Session = Depends(get_db)):
    _require_superadmin(request, db)
    u = db.query(User).filter(User.id == uid).first()
    if not u or u.role == "superadmin":
        raise HTTPException(status_code=404)
    db.delete(u)
    db.commit()
    return RedirectResponse(url="/admin/usuarios?saved=1", status_code=302)
