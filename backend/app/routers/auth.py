import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import User, RegistrationRequest, PasswordReset, Department
from ..schemas import LoginIn, RegisterRequestIn, ResetRequestIn, ResetConfirmIn, UserOut
from ..security import verify_password, create_token, hash_password
from ..deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/departments")
async def public_departments(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Department).order_by(Department.name))).scalars().all()
    return [{"id": d.id, "name": d.name} for d in rows]


@router.post("/login")
async def login(data: LoginIn, response: Response, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.login == data.login))).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(403, "Учётная запись отключена")
    token = create_token(user.id)
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=60*60*24*7)
    dept = await db.get(Department, user.department_id)
    return {
        "id": user.id, "login": user.login, "role": user.role,
        "department_id": user.department_id,
        "department_name": dept.name if dept else None,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user),
             db: AsyncSession = Depends(get_db)):
    dept = await db.get(Department, user.department_id)
    return UserOut(
        id=user.id, login=user.login, email=user.email,
        department_id=user.department_id,
        department_name=dept.name if dept else None,
        role=user.role, is_active=user.is_active,
    )


@router.post("/request")
async def request_access(data: RegisterRequestIn, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.login == data.login))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Логин уже занят")
    req = RegistrationRequest(
        login=data.login, email=data.email,
        department_id=data.department_id, message=data.message,
        status="pending",
    )
    db.add(req)
    await db.commit()
    return {"ok": True, "message": "Заявка отправлена. Администратор обработает её."}


@router.post("/password-reset-request")
async def password_reset_request(data: ResetRequestIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.login == data.login))).scalar_one_or_none()
    if user:
        token = secrets.token_urlsafe(32)
        pr = PasswordReset(
            user_id=user.id, token=token,
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        db.add(pr)
        await db.commit()
        return {"ok": True, "message": "Заявка создана. Обратитесь к администратору за токеном."}
    return {"ok": True, "message": "Если такой логин есть — заявка создана."}


@router.post("/password-reset")
async def password_reset(data: ResetConfirmIn, db: AsyncSession = Depends(get_db)):
    pr = (await db.execute(
        select(PasswordReset).where(PasswordReset.token == data.token,
                                    PasswordReset.used_at.is_(None))
    )).scalar_one_or_none()
    if not pr or pr.expires_at < datetime.utcnow():
        raise HTTPException(400, "Токен недействителен или истёк")
    user = await db.get(User, pr.user_id)
    if not user:
        raise HTTPException(400, "Пользователь не найден")
    user.password_hash = hash_password(data.new_password)
    pr.used_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}