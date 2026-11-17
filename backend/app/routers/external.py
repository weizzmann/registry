from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from ..database import get_db
from ..models import ExternalDocumentStaging, Document, Tom, Delo, Department, User
from ..deps import get_current_user
from ..services.csv_sync import sync_from_csv

router = APIRouter(prefix="/api/external", tags=["external"])

@router.post("/sync")
async def trigger_sync(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await sync_from_csv(db)

@router.get("/documents")
async def list_external(
    search: str | None = Query(None), unplaced_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    date_from: date | None = Query(None), date_to: date | None = Query(None), 
    organ: str | None = Query(None), employee: str | None = Query(None),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    base = select(ExternalDocumentStaging).where(ExternalDocumentStaging.deleted_at.is_(None))
    
    if search:
        pattern = f"%{search}%"
        base = base.where(
            ExternalDocumentStaging.title.ilike(pattern) | 
            ExternalDocumentStaging.doc_num.ilike(pattern) |
            ExternalDocumentStaging.incoming_num.ilike(pattern) | 
            ExternalDocumentStaging.outgoing_num.ilike(pattern) |
            ExternalDocumentStaging.cipher.ilike(pattern) |
            ExternalDocumentStaging.account_number.ilike(pattern) | 
            ExternalDocumentStaging.external_ref.ilike(pattern)
        )
        
    if date_from: base = base.where(ExternalDocumentStaging.incoming_date >= date_from)
    if date_to: base = base.where(ExternalDocumentStaging.incoming_date <= date_to)
    
    # Множественный выбор по органу (через запятую)
    if organ:
        orgs = [o.strip() for o in organ.split(',') if o.strip()]
        if orgs:
            base = base.where(or_(*[ExternalDocumentStaging.organ.ilike(f"%{o}%") for o in orgs]))
            
    # Множественный выбор по сотруднику (через запятую)
    if employee:
        emps = [e.strip() for e in employee.split(',') if e.strip()]
        if emps:
            base = base.where(or_(*[ExternalDocumentStaging.employee.ilike(f"%{e}%") for e in emps]))

    if unplaced_only:
        placed_exists = select(Document.id).where(Document.external_ref == ExternalDocumentStaging.external_ref).exists()
        base = base.where(~placed_exists)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (await db.execute(
        base.order_by(ExternalDocumentStaging.incoming_date.desc().nullslast(), ExternalDocumentStaging.external_ref).limit(limit).offset(offset)
    )).scalars().all()

    refs = [r.external_ref for r in rows]
    placed_map = {}
    if refs:
        placed_rows = (await db.execute(
            select(Document, Tom, Delo, Department).join(Tom, Tom.id == Document.tom_id)
            .join(Delo, Delo.id == Tom.delo_id).join(Department, Department.id == Delo.department_id)
            .where(Document.external_ref.in_(refs))
        )).all()
        for doc, tom, delo, dept in placed_rows:
            placed_map[doc.external_ref] = {
                "department": dept.name, "department_id": dept.id,
                "delo": delo.index_code, "year": delo.year, "tom": tom.tom_number,
                "pages": f"{doc.page_start}–{doc.page_end}" if doc.page_start != doc.page_end else str(doc.page_start),
                "own": dept.id == user.department_id,
            }

    items = []
    for r in rows:
        items.append({
            "external_ref": r.external_ref, "title": r.title,
            "account_number": r.account_number, "page_count": r.page_count,
            "incoming_num": r.incoming_num, "incoming_date": r.incoming_date.isoformat() if r.incoming_date else None,
            "outgoing_num": r.outgoing_num, "outgoing_date": r.outgoing_date.isoformat() if r.outgoing_date else None,
            "copy_num": r.copy_num, "cipher": r.cipher, "grif": r.grif, "organ": r.organ,
            "doc_num": r.doc_num, "employee": r.employee,
            "placed": placed_map.get(r.external_ref),
        })

    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": offset + len(items) < total}
