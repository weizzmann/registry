from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Delo, Tom, User, Document, Department
from ..schemas import DeloIn, DeloOut
from ..deps import get_current_user

router = APIRouter(prefix="/api/delos", tags=["delos"])

def _full_title(base_title: str, year: int) -> str:
    return f"Дело № {base_title}-{year}"

@router.get("", response_model=list[DeloOut])
async def list_delos(db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    stmt = (select(Delo, Department.name)
            .join(Department, Department.id == Delo.department_id)
            .order_by(Delo.year.desc(), Delo.base_title))
    if user.role != "admin":
        stmt = stmt.where(Delo.department_id == user.department_id)
    rows = (await db.execute(stmt)).all()
    return [DeloOut(
        id=d.id, department_id=d.department_id,
        department_name=dept_name,
        index_code=d.index_code,
        base_title=d.base_title, year=d.year, retention=d.retention,
        status=d.status, full_title=_full_title(d.base_title, d.year),
    ) for d, dept_name in rows]

@router.post("", response_model=DeloOut)
async def create_delo(data: DeloIn, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    if user.role == "admin":
        raise HTTPException(403, "Администратор не создаёт дела")

    title = (data.base_title or "").strip()
    if not title:
        raise HTTPException(422, "Название дела не может быть пустым")

    # Ищем все дела с таким же названием (по всей системе, любой год, любой статус)
    candidates = (await db.execute(
        select(Delo, Department.name)
        .join(Department, Department.id == Delo.department_id)
        .where(
            (func.trim(Delo.base_title) == title) | (func.trim(Delo.index_code) == title),
        )
        .order_by(Delo.year.desc())
    )).all()

    same_year = None          # дело с тем же названием в этом же году
    open_same_name = None     # незакрытое дело с тем же названием в другом году

    for d, dept_name in candidates:
        if d.year == data.year:
            same_year = (d, dept_name)
            break
        if d.status != "closed" and open_same_name is None:
            open_same_name = (d, dept_name)

    # 1. Дубль в текущем году — запрещён всегда
    if same_year:
        d, dept_name = same_year
        status_text = "закрыто" if d.status == "closed" else "открыто"
        raise HTTPException(
            409,
            f"Дело «{title}-{data.year}» уже существует в отделе «{dept_name}» "
            f"(статус: {status_text}). В одном году не может быть двух дел "
            f"с одинаковым названием — даже в разных отделах."
        )

    # 2. Незакрытое одноимённое дело за другой год — запрещено, пока не закрыто
    if open_same_name:
        d, dept_name = open_same_name
        raise HTTPException(
            409,
            f"Нельзя создать дело «{title}-{data.year}»: в отделе «{dept_name}» "
            f"есть незакрытое дело «{d.base_title}-{d.year}» с таким же названием. "
            f"Сначала откройте это дело и нажмите «Завершить дело», "
            f"затем создавайте новое."
        )

    d = Delo(
        department_id=user.department_id,
        index_code=title,
        base_title=title,
        year=data.year,
        retention=data.retention,
        status="open",
    )
    db.add(d)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            409,
            f"Дело «{title}-{data.year}» уже существует. "
            "Скорее всего, его только что создал другой пользователь."
        )
    await db.refresh(d)
    dept = await db.get(Department, d.department_id)
    return DeloOut(
        id=d.id, department_id=d.department_id,
        department_name=dept.name if dept else None,
        index_code=d.index_code,
        base_title=d.base_title, year=d.year, retention=d.retention,
        status=d.status, full_title=_full_title(d.base_title, d.year),
    )

@router.get("/{delo_id}/toms")
async def list_toms(delo_id: int, db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    delo = await db.get(Delo, delo_id)
    if not delo:
        raise HTTPException(404, "Дело не найдено")
    if user.role != "admin" and delo.department_id != user.department_id:
        raise HTTPException(404, "Дело не найдено")

    toms = (await db.execute(
        select(Tom).where(Tom.delo_id == delo_id).order_by(Tom.tom_number)
    )).scalars().all()

    result = []
    for t in toms:
        docs = (await db.execute(
            select(Document).where(Document.tom_id == t.id)
            .order_by(Document.order_in_tom)
        )).scalars().all()
        current_end = max((d.page_end for d in docs), default=0)
        result.append({
            "id": t.id,
            "tom_number": t.tom_number,
            "max_pages": t.max_pages,
            "status": t.status,
            "current_end": current_end,
            "documents_count": len(docs),
            "documents": [{
                "id": d.id, "title": d.title,
                "account_number": d.account_number, "page_count": d.page_count,
                "page_start": d.page_start, "page_end": d.page_end,
                "order_in_tom": d.order_in_tom, "source": d.source,
                "external_ref": d.external_ref,
            } for d in docs],
        })
    return result

@router.post("/{delo_id}/close")
async def close_delo(delo_id: int, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    if user.role == "admin":
        raise HTTPException(403, "Администратор не закрывает дела")
    delo = await db.get(Delo, delo_id)
    if not delo or delo.department_id != user.department_id:
        raise HTTPException(404, "Дело не найдено")
    if delo.status == "closed":
        raise HTTPException(409, "Дело уже закрыто")

    toms = (await db.execute(
        select(Tom).where(Tom.delo_id == delo_id).order_by(Tom.tom_number)
    )).scalars().all()
    if not toms:
        raise HTTPException(422, "В деле нет томов")

    violations = []
    for t in toms[:-1]:
        end = (await db.execute(
            select(func.coalesce(func.max(Document.page_end), 0)).where(Document.tom_id == t.id)
        )).scalar() or 0
        if end != t.max_pages:
            violations.append({"tom_number": t.tom_number,
                              "filled": end, "missing": t.max_pages - end})
    if violations:
        raise HTTPException(422, {"error": "intermediate_toms_not_full",
                                  "violations": violations})

    delo.status = "closed"
    last = toms[-1]
    last.status = "final"
    for t in toms[:-1]:
        t.status = "full"
    await db.commit()
    last_end = (await db.execute(
        select(func.coalesce(func.max(Document.page_end), 0)).where(Document.tom_id == last.id)
    )).scalar() or 0
    return {"delo_id": delo_id, "final_tom": last.tom_number,
            "final_tom_pages": last_end, "closed_at": datetime.utcnow()}