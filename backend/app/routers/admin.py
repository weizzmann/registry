import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User, RegistrationRequest, Department, DocumentType
from ..schemas import ApproveIn, UserOut, DepartmentIn, DepartmentOut, ChangeDeptIn
from ..security import hash_password
from ..deps import require_admin
from ..services.csv_sync import sync_from_csv

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/sync-external")
async def sync_external(db: AsyncSession = Depends(get_db),
                        _: User = Depends(require_admin)):
    return await sync_from_csv(db)


@router.get("/requests")
async def list_requests(status: str = "pending",
                        db: AsyncSession = Depends(get_db),
                        _: User = Depends(require_admin)):
    rows = (await db.execute(
        select(RegistrationRequest).where(RegistrationRequest.status == status)
        .order_by(RegistrationRequest.created_at)
    )).scalars().all()
    result = []
    for r in rows:
        dept = await db.get(Department, r.department_id) if r.department_id else None
        result.append({
            "id": r.id, "login": r.login, "email": r.email,
            "department_id": r.department_id,
            "department_name": dept.name if dept else None,
            "message": r.message, "status": r.status,
            "created_at": r.created_at,
        })
    return result


@router.post("/requests/{req_id}/approve")
async def approve(req_id: int, data: ApproveIn,
                  db: AsyncSession = Depends(get_db),
                  admin: User = Depends(require_admin)):
    req = await db.get(RegistrationRequest, req_id)
    if not req or req.status != "pending":
        raise HTTPException(404, "Заявка не найдена или уже обработана")
    if not req.department_id:
        raise HTTPException(400, "У заявки не указан отдел")
    if (await db.execute(select(User).where(User.login == data.login))).scalar_one_or_none():
        raise HTTPException(409, "Логин уже занят")
    user = User(
        login=data.login,
        email=req.email,
        password_hash=hash_password(data.password),
        department_id=req.department_id,
        role=data.role,
        is_active=True,
    )
    db.add(user)
    req.status = "approved"
    req.processed_at = datetime.utcnow()
    req.processed_by = admin.id
    await db.commit()
    return {"ok": True, "user_id": user.id, "login": user.login}


@router.post("/requests/{req_id}/reject")
async def reject(req_id: int, db: AsyncSession = Depends(get_db),
                 admin: User = Depends(require_admin)):
    req = await db.get(RegistrationRequest, req_id)
    if not req or req.status != "pending":
        raise HTTPException(404, "Заявка не найдена")
    req.status = "rejected"
    req.processed_at = datetime.utcnow()
    req.processed_by = admin.id
    await db.commit()
    return {"ok": True}


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db),
                     _: User = Depends(require_admin)):
    rows = (await db.execute(
        select(User, Department.name)
        .outerjoin(Department, Department.id == User.department_id)
        .order_by(User.login)
    )).all()
    return [UserOut(
        id=u.id, login=u.login, email=u.email,
        department_id=u.department_id, department_name=dept_name,
        role=u.role, is_active=u.is_active,
    ) for u, dept_name in rows]


@router.post("/users/{user_id}/deactivate")
async def deactivate(user_id: int, db: AsyncSession = Depends(get_db),
                     _: User = Depends(require_admin)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(404)
    u.is_active = False
    await db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: int, db: AsyncSession = Depends(get_db),
                               _: User = Depends(require_admin)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(404)
    new_pw = secrets.token_urlsafe(8)
    u.password_hash = hash_password(new_pw)
    await db.commit()
    return {"ok": True, "temp_password": new_pw}


@router.patch("/users/{user_id}/department")
async def change_user_department(user_id: int, data: ChangeDeptIn,
                                 db: AsyncSession = Depends(get_db),
                                 _: User = Depends(require_admin)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Пользователь не найден")
    dept = await db.get(Department, data.department_id)
    if not dept:
        raise HTTPException(404, "Отдел не найден")
    u.department_id = data.department_id
    await db.commit()
    return {"ok": True, "department_id": dept.id, "department_name": dept.name}


@router.post("/departments", response_model=DepartmentOut)
async def create_department(data: DepartmentIn,
                            db: AsyncSession = Depends(get_db),
                            _: User = Depends(require_admin)):
    d = Department(name=data.name, code=data.code)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(db: AsyncSession = Depends(get_db),
                           _: User = Depends(require_admin)):
    return (await db.execute(select(Department).order_by(Department.name))).scalars().all()


@router.get("/document-types")
async def list_types(db: AsyncSession = Depends(get_db),
                     _: User = Depends(require_admin)):
    rows = (await db.execute(select(DocumentType).order_by(DocumentType.name))).scalars().all()
    return [{"id": t.id, "name": t.name, "source": t.source} for t in rows]


@router.post("/document-types")
async def create_type(name: str, db: AsyncSession = Depends(get_db),
                      _: User = Depends(require_admin)):
    t = DocumentType(name=name, source="manual")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "name": t.name}