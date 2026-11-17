from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Department, User
from ..deps import get_current_user

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("")
async def list_departments(db: AsyncSession = Depends(get_db),
                           _: User = Depends(get_current_user)):
    rows = (await db.execute(select(Department).order_by(Department.name))).scalars().all()
    return [{"id": d.id, "name": d.name, "code": d.code} for d in rows]