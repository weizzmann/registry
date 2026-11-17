from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Delo, Tom, Document, User, DocumentType, DocumentChange, Department
from ..schemas import DraftItemPatch
from ..deps import get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])

class DocumentTypeIn(BaseModel):
    name: str

async def _load_doc_with_owner(db, doc_id, user):
    doc = await db.get(Document, doc_id)
    if not doc: raise HTTPException(404, "Документ не найден")
    tom = await db.get(Tom, doc.tom_id)
    delo = await db.get(Delo, tom.delo_id)
    if not delo or delo.department_id != user.department_id: raise HTTPException(403)
    return doc, tom, delo

@router.get("/types")
async def list_document_types(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (await db.execute(select(DocumentType).order_by(DocumentType.name))).scalars().all()
    return [{"id": r.id, "name": r.name} for r in rows]

@router.post("/types")
async def create_document_type(data: DocumentTypeIn, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    name = data.name.strip()
    if not name: raise HTTPException(400, "Название не может быть пустым")
    existing = (await db.execute(select(DocumentType).where(DocumentType.name == name))).scalar_one_or_none()
    if existing: return {"id": existing.id, "name": existing.name}
    t = DocumentType(name=name, source="manual")
    db.add(t); await db.commit(); await db.refresh(t)
    return {"id": t.id, "name": t.name}

@router.get("/search")
async def search_documents(q: str = Query(..., min_length=2, max_length=200), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    pattern = f"%{q.strip()}%"

    stmt = (
        select(Document, Tom, Delo, Department)
        .join(Tom, Tom.id == Document.tom_id).join(Delo, Delo.id == Tom.delo_id).join(Department, Department.id == Delo.department_id)
        .where(
            Document.title.ilike(pattern) | Document.original_title.ilike(pattern) |
            Document.doc_num.ilike(pattern) | Document.original_doc_num.ilike(pattern) |
            Document.organ.ilike(pattern) | Document.original_organ.ilike(pattern) |
            Document.account_number.ilike(pattern) | Document.incoming_num.ilike(pattern) | Document.outgoing_num.ilike(pattern)
        )
    )
    if user.role != "admin": stmt = stmt.where(Delo.department_id == user.department_id)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    rows = (await db.execute(stmt.order_by(Delo.year.desc(), Delo.base_title, Tom.tom_number, Document.order_in_tom).limit(limit).offset(offset))).all()

    items = []
    for doc, tom, delo, dept in rows:
        pages_str = str(doc.page_start) if doc.page_start == doc.page_end else f"{doc.page_start}–{doc.page_end}"
        base = delo.base_title.strip()
        is_changed = (doc.title != doc.original_title) or (doc.doc_num != doc.original_doc_num) or (doc.organ != doc.original_organ) or (doc.page_count != doc.original_page_count)
        
        items.append({
            "id": doc.id, "title": doc.title, "original_title": doc.original_title,
            "doc_num": doc.doc_num, "original_doc_num": doc.original_doc_num,
            "organ": doc.organ, "original_organ": doc.original_organ,
            "account_number": doc.account_number, "page_count": doc.page_count, "original_page_count": doc.original_page_count,
            "page_start": doc.page_start, "page_end": doc.page_end,
            "location": f"д. {base} - {delo.year} т. {tom.tom_number} л. {pages_str}",
            "delo_id": delo.id, "delo_full_title": f"Дело № {base}-{delo.year}", "tom_id": tom.id, "tom_number": tom.tom_number,
            "department_id": dept.id, "department_name": dept.name,
            "is_changed": is_changed
        })
    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": offset + len(items) < total}

@router.put("/{doc_id}")
async def update_document(doc_id: int, data: DraftItemPatch, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    doc, tom, delo = await _load_doc_with_owner(db, doc_id, user)
    if delo.status != "open" or tom.status not in ("open",): raise HTTPException(409, "Редактирование недоступно")

    changes = []
    # Словарь для перевода технических названий полей на русский язык
    field_names_ru = {
        "title": "Название",
        "doc_num": "№ документа",
        "organ": "Орган",
        "page_count": "Листов",
        "cipher": "Шифр",
        "incoming_num": "Вх. №",
        "outgoing_num": "Исх. №",
        "copy_num": "Экз.",
        "employee": "Сотрудник",
        "grif": "Гриф",
        "account_number": "Учётный №"
    }

    def log_change(field_code, old, new):
        if str(old or '') != str(new or ''):
            field_name = field_names_ru.get(field_code, field_code)
            changes.append(DocumentChange(
                document_id=doc.id, user_id=user.id, user_login=user.login, source='user',
                field_name=field_name, old_value=str(old or ''), new_value=str(new or '')
            ))

    if data.title is not None and data.title.strip() != doc.title:
        log_change('title', doc.title, data.title.strip()); doc.title = data.title.strip()
    if data.account_number is not None and data.account_number.strip() != (doc.account_number or ''):
        log_change('account_number', doc.account_number, data.account_number.strip()); doc.account_number = data.account_number.strip() or None
    if data.doc_num is not None and data.doc_num.strip() != (doc.doc_num or ''):
        log_change('doc_num', doc.doc_num, data.doc_num.strip()); doc.doc_num = data.doc_num.strip() or None
    if data.organ is not None and data.organ.strip() != (doc.organ or ''):
        log_change('organ', doc.organ, data.organ.strip()); doc.organ = data.organ.strip() or None

    if data.page_count is not None and data.page_count != doc.page_count:
        if data.page_count <= 0 or data.page_count > tom.max_pages: raise HTTPException(422, "Некорректное количество листов")
        delta = data.page_count - doc.page_count
        current_end = (await db.execute(select(func.coalesce(func.max(Document.page_end), 0)).where(Document.tom_id == tom.id))).scalar() or 0
        
        if current_end + delta > tom.max_pages:
            free = tom.max_pages - current_end
            raise HTTPException(422, f"В томе свободно {free} л. Не хватает {delta} л.")

        following = (await db.execute(select(Document).where(Document.tom_id == tom.id, Document.order_in_tom > doc.order_in_tom))).scalars().all()
        updates = [(d, d.page_start, d.page_end) for d in following]
        for d, _, _ in updates: d.page_start = -d.id; d.page_end = -d.id
        await db.flush()
        for d, old_start, old_end in updates: d.page_start = old_start + delta; d.page_end = old_end + delta
        
        log_change('page_count', doc.page_count, data.page_count)
        doc.page_count = data.page_count
        doc.page_end = doc.page_start + data.page_count - 1

    for c in changes: db.add(c)
    await db.commit()
    return {"ok": True}

@router.delete("/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    doc, tom, delo = await _load_doc_with_owner(db, doc_id, user)
    if delo.status != "open" or tom.status not in ("open",): raise HTTPException(409, "Удаление недоступно")

    removed_order = doc.order_in_tom
    shift = doc.page_count

    await db.delete(doc); await db.flush()
    following = (await db.execute(select(Document).where(Document.tom_id == tom.id, Document.order_in_tom > removed_order).order_by(Document.order_in_tom))).scalars().all()
    updates = [(d, d.page_start, d.page_end, d.order_in_tom) for d in following]
    for d, _, _, _ in updates:
        d.page_start = -d.id; d.page_end = -d.id; d.order_in_tom = -d.id
    await db.flush()
    for d, old_start, old_end, old_order in updates:
        d.page_start = old_start - shift; d.page_end = old_end - shift; d.order_in_tom = old_order - 1

    await db.commit()
    return {"ok": True, "freed_pages": shift}
