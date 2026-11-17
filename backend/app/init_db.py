from sqlalchemy import select
from .database import SessionLocal, engine, Base
from .models import Department, User
from .security import hash_password
from .config import settings


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        dept = (await db.execute(
            select(Department).where(Department.name == settings.admin_department)
        )).scalar_one_or_none()
        if not dept:
            dept = Department(name=settings.admin_department, code="ADMIN")
            db.add(dept)
            await db.flush()

        admin = (await db.execute(
            select(User).where(User.login == settings.admin_login)
        )).scalar_one_or_none()
        if not admin:
            admin = User(
                login=settings.admin_login,
                password_hash=hash_password(settings.admin_password),
                department_id=dept.id,
                role="admin",
                is_active=True,
            )
            db.add(admin)
        await db.commit()