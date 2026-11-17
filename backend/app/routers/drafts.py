from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import (Delo, Tom, Document, User, ExternalDocumentStaging,
                      PlacementDraft, PlacementDraftItem, DocumentType, Department, DocumentChange)
from ..schemas import DraftItemsPayload, DraftItemPatch, ReorderIn
from ..deps import get_current_user
from ..services.split import simulate_split, validate_split

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

async def _get_or_create_draft(db, user, delo_id):
    if user.role == "admin": raise HTTPException(403, "Администратор не может редактировать дела")
    delo = await db.get(Delo, delo_id)
    if not delo or delo.department_id != user.department_id: raise HTTPException(404, "Дело не найдено")
    if delo.status != "open": raise HTTPException(409, "Дело закрыто")
    draft = (await db.execute(select(PlacementDraft).where(PlacementDraft.user_id == user.id, PlacementDraft.delo_id == delo_id))).scalar_one_or_none()
    if not draft:
        draft = PlacementDraft(user_id=user.id, delo_id=delo_id)
        db.add(draft); await db.commit(); await db.refresh(draft)
    return delo, draft

async def _build_preview(db, draft, delo, current_user_id=None):
    if draft is not None:
        items = (await db.execute(select(PlacementDraftItem).where(PlacementDraftItem.draft_id == draft.id).order_by(PlacementDraftItem.position))).scalars().all()
        draft_id = draft.id
    else:
        items = []; draft_id = None

    tom = (await db.execute(select(Tom).where(Tom.delo_id == delo.id).order_by(Tom.tom_number.desc()).limit(1))).scalar_one_or_none()
    current_end = 0
    if tom: current_end = (await db.execute(select(func.coalesce(func.max(Document.page_end), 0)).where(Document.tom_id == tom.id))).scalar() or 0
    max_tom_number = (await db.execute(select(func.coalesce(func.max(Tom.tom_number), 0)).where(Tom.delo_id == delo.id))).scalar() or 0

    items_data = [{
        "id": it.id, "position": it.position, "source": it.source,
        "external_ref": it.external_ref, "title": it.title,
        "account_number": it.account_number, "page_count": it.page_count,
        "type_id": it.type_id, "incoming_num": it.incoming_num,
        "incoming_date": it.incoming_date.isoformat() if it.incoming_date else None,
        "outgoing_num": it.outgoing_num, "outgoing_date": it.outgoing_date.isoformat() if it.outgoing_date else None,
        "copy_num": it.copy_num, "cipher": it.cipher, "grif": it.grif, "organ": it.organ,
        "doc_num": it.doc_num, "employee": it.employee,
    } for it in items]

    total_pages = sum(it["page_count"] for it in items_data)

    if items_data:
        current_tom_number = tom.tom_number if tom and tom.status == "open" else None
        plan = simulate_split(items_data, current_tom_number, current_end if current_tom_number else 0, 250, max_tom_number)
        violations = validate_split(plan)
    else:
        plan = []; violations = []

    refs = [it["external_ref"] for it in items_data if it["source"] == "external" and it["external_ref"]]
    conflicts = []
    if refs:
        placed = (await db.execute(
            select(Document.external_ref, Document.title, Document.page_start, Document.page_end, Tom.tom_number, Delo.index_code, Delo.year, Department.name)
            .join(Tom, Tom.id == Document.tom_id).join(Delo, Delo.id == Tom.delo_id).join(Department, Department.id == Delo.department_id)
            .where(Document.external_ref.in_(refs))
        )).all()
        for ref, title, ps, pe, tnum, idx, yr, dept in placed:
            pages = f"{ps}" if ps == pe else f"{ps}–{pe}"
            conflicts.append({"external_ref": ref, "title": title, "location": f"д. {idx} - {yr} т. {tnum} л. {pages} ({dept})"})

    other_drafts = []
    if current_user_id is not None:
        rows = (await db.execute(
            select(PlacementDraft, User.login).join(User, User.id == PlacementDraft.user_id)
            .where(PlacementDraft.delo_id == delo.id, PlacementDraft.user_id != current_user_id)
        )).all()
        for od, login in rows:
            count = (await db.execute(select(func.count()).select_from(PlacementDraftItem).where(PlacementDraftItem.draft_id == od.id))).scalar() or 0
            if count > 0: other_drafts.append({"user_login": login, "items_count": count})

    return {
        "draft_id": draft_id,
        "delo": {"id": delo.id, "index_code": delo.index_code, "full_title": f"Дело № {delo.base_title}-{delo.year}", "year": delo.year, "status": delo.status, "department_id": delo.department_id, "department_name": (await db.get(Department, delo.department_id)).name if delo.department_id else None},
        "current_tom": {"id": tom.id if tom else None, "tom_number": tom.tom_number if tom else 0, "current_end": current_end, "max_pages": 250, "free_pages": 250 - current_end, "status": tom.status if tom else "none"},
        "items": items_data, "total_pages": total_pages,
        "plan": [{"tom_number": p["tom_number"], "existing": p["existing"], "current_end": p["current_end"], "max_pages": p["max_pages"], "final_page": p["final_page"], "is_last": p["is_last"], "items_count": len(p["items"]), "pages_used": p["final_page"] - (p["current_end"] if p["existing"] else 0), "items": p["items"]} for p in plan],
        "violations": violations, "can_commit": len(items_data) > 0 and len(violations) == 0 and len(conflicts) == 0, "conflicts": conflicts, "other_drafts": other_drafts,
    }

@router.get("/{delo_id}")
async def get_draft(delo_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delo = await db.get(Delo, delo_id)
    if not delo: raise HTTPException(404)
    if user.role == "admin": return await _build_preview(db, None, delo, user.id)
    if delo.department_id != user.department_id: raise HTTPException(404)
    if delo.status != "open": return await _build_preview(db, None, delo, user.id)
    draft = (await db.execute(select(PlacementDraft).where(PlacementDraft.user_id == user.id, PlacementDraft.delo_id == delo_id))).scalar_one_or_none()
    if not draft:
        draft = PlacementDraft(user_id=user.id, delo_id=delo_id)
        db.add(draft); await db.commit(); await db.refresh(draft)
    return await _build_preview(db, draft, delo, user.id)

@router.post("/{delo_id}/items")
async def set_items(delo_id: int, payload: DraftItemsPayload, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delo, draft = await _get_or_create_draft(db, user, delo_id)
    existing = (await db.execute(select(PlacementDraftItem).where(PlacementDraftItem.draft_id == draft.id))).scalars().all()
    for e in existing: await db.delete(e)
    await db.flush()

    for i, it in enumerate(payload.items):
        if it.source == "external":
            ext = await db.get(ExternalDocumentStaging, it.external_ref)
            if not ext or ext.deleted_at: raise HTTPException(404)
            item = PlacementDraftItem(
                draft_id=draft.id, position=i + 1, source="external", external_ref=it.external_ref,
                title=ext.title, account_number=ext.account_number, page_count=ext.page_count, type_id=it.type_id,
                incoming_num=ext.incoming_num, incoming_date=ext.incoming_date,
                outgoing_num=ext.outgoing_num, outgoing_date=ext.outgoing_date,
                copy_num=ext.copy_num, cipher=ext.cipher, grif=ext.grif, organ=ext.organ,
                doc_num=ext.doc_num, employee=ext.employee,
                original_title=ext.title, original_doc_num=ext.doc_num, original_organ=ext.organ, original_page_count=ext.page_count
            )
        else:
            if not it.page_count or it.page_count <= 0 or it.page_count > 250: raise HTTPException(422)
            title = it.title or ""
            if not title and it.type_id:
                dt = await db.get(DocumentType, it.type_id); title = dt.name if dt else ""
            item = PlacementDraftItem(
                draft_id=draft.id, position=i + 1, source="manual", title=title,
                account_number=it.account_number, page_count=it.page_count, type_id=it.type_id,
                copy_num="1", original_title=title, original_page_count=it.page_count
            )
        db.add(item)

    draft.updated_at = datetime.utcnow()
    await db.commit(); await db.refresh(draft)
    return await _build_preview(db, draft, delo, user.id)

@router.patch("/{delo_id}/items/{item_id}")
async def patch_item(delo_id: int, item_id: int, data: DraftItemPatch, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delo, draft = await _get_or_create_draft(db, user, delo_id)
    item = await db.get(PlacementDraftItem, item_id)
    if not item or item.draft_id != draft.id: raise HTTPException(404)
    
    if data.title is not None: item.title = data.title.strip() or item.title
    if data.account_number is not None: item.account_number = data.account_number.strip() or None
    if data.doc_num is not None: item.doc_num = data.doc_num.strip() or None
    if data.organ is not None: item.organ = data.organ.strip() or None
    if data.cipher is not None: item.cipher = data.cipher.strip() or None
    if data.employee is not None: item.employee = data.employee.strip() or None
    if data.incoming_num is not None: item.incoming_num = data.incoming_num.strip() or None
    if data.outgoing_num is not None: item.outgoing_num = data.outgoing_num.strip() or None
    if data.copy_num is not None: item.copy_num = data.copy_num.strip() or None
    if data.grif is not None: item.grif = data.grif.strip() or None
    
    if data.incoming_date is not None: item.incoming_date = data.incoming_date
    if data.outgoing_date is not None: item.outgoing_date = data.outgoing_date

    if data.page_count is not None:
        if data.page_count <= 0 or data.page_count > 250: raise HTTPException(422, "page_count должен быть 1–250")
        item.page_count = data.page_count

    draft.updated_at = datetime.utcnow(); await db.commit(); await db.refresh(draft)
    return await _build_preview(db, draft, delo, user.id)

@router.delete("/{delo_id}/items/{item_id}")
async def delete_item(delo_id: int, item_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delo, draft = await _get_or_create_draft(db, user, delo_id)
    item = await db.get(PlacementDraftItem, item_id)
    if not item or item.draft_id != draft.id: raise HTTPException(404)
    pos = item.position; await db.delete(item); await db.flush()
    rest = (await db.execute(select(PlacementDraftItem).where(PlacementDraftItem.draft_id == draft.id, PlacementDraftItem.position > pos).order_by(PlacementDraftItem.position))).scalars().all()
    updates = []
    for r in rest:
        updates.append((r, r.position)); r.position = -r.id
    await db.flush()
    for r, old_pos in updates: r.position = old_pos - 1
    draft.updated_at = datetime.utcnow(); await db.commit(); await db.refresh(draft)
    return await _build_preview(db, draft, delo, user.id)

@router.post("/{delo_id}/reorder")
async def reorder(delo_id: int, data: ReorderIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delo, draft = await _get_or_create_draft(db, user, delo_id)
    items = (await db.execute(select(PlacementDraftItem).where(PlacementDraftItem.draft_id == draft.id))).scalars().all()
    if len(data.order) != len(items): raise HTTPException(422)
    by_id = {it.id: it for it in items}
    for it in items: it.position = -it.id
    await db.flush()
    for new_pos, item_id in enumerate(data.order):
        if item_id not in by_id: raise HTTPException(422)
        by_id[item_id].position = new_pos + 1
    draft.updated_at = datetime.utcnow(); await db.commit(); await db.refresh(draft)
    return await _build_preview(db, draft, delo, user.id)

@router.post("/{delo_id}/commit")
async def commit_draft(delo_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    delo, draft = await _get_or_create_draft(db, user, delo_id)
    await db.execute(select(Delo).where(Delo.id == delo_id).with_for_update())
    preview = await _build_preview(db, draft, delo, user.id)
    if not preview["can_commit"]:
        raise HTTPException(422, {"error": "cannot_commit", "violations": preview["violations"], "conflicts": preview["conflicts"]})

    items = (await db.execute(select(PlacementDraftItem).where(PlacementDraftItem.draft_id == draft.id).order_by(PlacementDraftItem.position))).scalars().all()
    refs = [it.external_ref for it in items if it.external_ref]
    if refs:
        placed = (await db.execute(select(Document.external_ref, Document.title, Tom.tom_number, Delo.index_code, Delo.year, Department.name).join(Tom, Tom.id == Document.tom_id).join(Delo, Delo.id == Tom.delo_id).join(Department, Department.id == Delo.department_id).where(Document.external_ref.in_(refs)))).all()
        if placed:
            raise HTTPException(409, {"error": "already_placed", "message": "Часть документов уже размещена", "conflicts": [{"external_ref": p[0], "title": p[1], "location": f"д. {p[3]} - {p[4]} т. {p[2]} ({p[5]})"} for p in placed]})

    tom = (await db.execute(select(Tom).where(Tom.delo_id == delo_id).order_by(Tom.tom_number.desc()).limit(1))).scalar_one_or_none()
    if not tom or tom.status != "open":
        next_number = 1 if not tom else tom.tom_number + 1
        tom = Tom(delo_id=delo_id, tom_number=next_number, max_pages=250, status="open")
        db.add(tom); await db.flush()
        current_end = 0
    else:
        current_end = (await db.execute(select(func.coalesce(func.max(Document.page_end), 0)).where(Document.tom_id == tom.id))).scalar() or 0

    cursor = current_end + 1
    next_order = ((await db.execute(select(func.coalesce(func.max(Document.order_in_tom), 0)).where(Document.tom_id == tom.id))).scalar() or 0) + 1
    created_toms = [{"tom_id": tom.id, "tom_number": tom.tom_number, "docs": 0, "pages": 0}]

    for it in items:
        if cursor + it.page_count - 1 > tom.max_pages:
            if cursor - 1 != tom.max_pages: await db.rollback(); raise HTTPException(422, "Промежуточный том не заполнен до 250.")
            tom.status = "full"; next_number = tom.tom_number + 1
            tom = Tom(delo_id=delo_id, tom_number=next_number, max_pages=250, status="open")
            db.add(tom); await db.flush()
            cursor = 1; next_order = 1
            created_toms.append({"tom_id": tom.id, "tom_number": tom.tom_number, "docs": 0, "pages": 0})

        d = Document(
            tom_id=tom.id, title=it.title, account_number=it.account_number, page_count=it.page_count,
            page_start=cursor, page_end=cursor + it.page_count - 1, order_in_tom=next_order,
            source=it.source, external_ref=it.external_ref, type_id=it.type_id,
            incoming_num=it.incoming_num, incoming_date=it.incoming_date,
            outgoing_num=it.outgoing_num, outgoing_date=it.outgoing_date,
            copy_num=it.copy_num, cipher=it.cipher, grif=it.grif, organ=it.organ,
            doc_num=it.doc_num, employee=it.employee,
            original_title=it.original_title or it.title,
            original_doc_num=it.original_doc_num or it.doc_num,
            original_organ=it.original_organ or it.organ,
            original_incoming_num=it.incoming_num,
            original_incoming_date=it.incoming_date,
            original_outgoing_num=it.outgoing_num,
            original_outgoing_date=it.outgoing_date,
            original_copy_num=it.copy_num,
            original_cipher=it.cipher,
            original_employee=it.employee,
            original_page_count=it.original_page_count or it.page_count
        )
        db.add(d)
        await db.flush()

        # Логирование изменений при фиксации
        change_fields = [
            ("Название", it.original_title, it.title),
            ("№ документа", it.original_doc_num, it.doc_num),
            ("Орган", it.original_organ, it.organ),
            ("Листов", str(it.original_page_count) if it.original_page_count else None, str(it.page_count))
        ]
        for field, old_val, new_val in change_fields:
            if old_val and old_val != new_val:
                db.add(DocumentChange(
                    document_id=d.id, user_id=user.id, user_login=user.login, source='user',
                    field_name=field, old_value=old_val, new_value=new_val
                ))

        created_toms[-1]["docs"] += 1; created_toms[-1]["pages"] += it.page_count
        cursor = d.page_end + 1; next_order += 1

    for it in items: await db.delete(it)
    await db.delete(draft)
    try: await db.commit()
    except IntegrityError: await db.rollback(); raise HTTPException(409, {"error": "conflict", "message": "Обновите страницу и попробуйте снова."})
    return {"ok": True, "placed": len(items), "toms": created_toms}
