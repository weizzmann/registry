import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from ..database import get_db
from ..models import Delo, Tom, Document, User, DocumentChange
from ..schemas import ReorderIn
from ..deps import get_current_user

router = APIRouter(prefix="/api/toms", tags=["toms"])

def number_to_words(n: int) -> str:
    units = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
    teens = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
    tens = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
    hundreds = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]
    if n == 0: return "ноль"
    res = []
    h = n // 100; t = (n % 100) // 10; u = n % 10
    if h > 0: res.append(hundreds[h])
    if t == 1: res.append(teens[u])
    else:
        if t > 1: res.append(tens[t])
        if u > 0: res.append(units[u])
    return " ".join(res)

async def _check_access(db: AsyncSession, tom_id: int, user: User):
    tom = await db.get(Tom, tom_id)
    if not tom: raise HTTPException(404, "Том не найден")
    delo = await db.get(Delo, tom.delo_id)
    if not delo: raise HTTPException(404, "Дело не найдено")
    if user.role != "admin" and delo.department_id != user.department_id: raise HTTPException(403, "Нет доступа")
    return tom, delo

@router.get("/{tom_id}")
async def tom_detail(tom_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tom, delo = await _check_access(db, tom_id, user)
    docs = (await db.execute(select(Document).where(Document.tom_id == tom_id).order_by(Document.order_in_tom))).scalars().all()
    
    doc_ids = [d.id for d in docs]
    changes = (await db.execute(select(DocumentChange).where(DocumentChange.document_id.in_(doc_ids)).order_by(DocumentChange.changed_at))).scalars().all()
    
    changes_map = {}
    for c in changes:
        if c.document_id not in changes_map: changes_map[c.document_id] = []
        changes_map[c.document_id].append({
            "field": c.field_name, "old": c.old_value, "new": c.new_value,
            "user": c.user_login, "source": c.source, "date": c.changed_at.isoformat()
        })

    current_end = max((d.page_end for d in docs), default=0)
    return {
        "tom": {"id": tom.id, "tom_number": tom.tom_number, "max_pages": tom.max_pages, "status": tom.status, "current_end": current_end, "free_pages": tom.max_pages - current_end},
        "delo": {"id": delo.id, "index_code": delo.index_code, "full_title": f"Дело № {delo.base_title}-{delo.year}", "year": delo.year, "status": delo.status},
        "documents": [{
            "id": d.id, "title": d.title, "doc_num": d.doc_num, "organ": d.organ,
            "original_title": d.original_title, "original_doc_num": d.original_doc_num, "original_organ": d.original_organ,
            "page_count": d.page_count, "original_page_count": d.original_page_count,
            "page_start": d.page_start, "page_end": d.page_end, "order_in_tom": d.order_in_tom,
            "source": d.source, "external_ref": d.external_ref, "incoming_num": d.incoming_num, "incoming_date": d.incoming_date.isoformat() if d.incoming_date else None,
            "outgoing_num": d.outgoing_num, "outgoing_date": d.outgoing_date.isoformat() if d.outgoing_date else None,
            "copy_num": d.copy_num, "cipher": d.cipher, "grif": d.grif, "employee": d.employee,
            "changes": changes_map.get(d.id, [])
        } for d in docs],
    }

@router.get("/{tom_id}/export")
async def export_tom_excel(tom_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tom, delo = await _check_access(db, tom_id, user)
    docs = (await db.execute(select(Document).where(Document.tom_id == tom_id).order_by(Document.order_in_tom))).scalars().all()

    wb = Workbook(); ws = wb.active; ws.title = f"Том {tom.tom_number}"
    bold = Font(bold=True, size=12); center = Alignment(horizontal="center", vertical="center", wrap_text=True); left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin = Side(style='thin'); border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells('A1:G1'); ws['A1'] = "ВНУТРЕННЯЯ ОПИСЬ"; ws['A1'].font = Font(bold=True, size=14); ws['A1'].alignment = center
    ws.merge_cells('A2:G2'); ws['A2'] = f"документов, находящихся в деле № {delo.base_title} том № {tom.tom_number}"; ws['A2'].alignment = center
    ws.merge_cells('A3:G3'); ws['A3'] = f"за {delo.year} год"; ws['A3'].alignment = center

    ws.merge_cells('A4:A5'); ws['A4'] = "Порядковый номер"
    ws.merge_cells('B4:C4'); ws['B4'] = "Номер документа и дата"
    ws['B5'] = "входящего"; ws['C5'] = "подготовленного (исходящего)"
    ws.merge_cells('D4:D5'); ws['D4'] = "Номер экземпляра"
    ws.merge_cells('E4:E5'); ws['E4'] = "Вид и краткое содержание документа, откуда поступил, кто подготовил"
    ws.merge_cells('F4:F5'); ws['F4'] = "Номер листов"
    ws.merge_cells('G4:G5'); ws['G4'] = "Отметка об изъятии документа из дела и его местонахождении"

    for r in range(4, 6):
        for c in range(1, 8): ws.cell(row=r, column=c).font = bold; ws.cell(row=r, column=c).alignment = center; ws.cell(row=r, column=c).border = border

    start_row = 6
    for i, d in enumerate(docs, 1):
        row = start_row + i - 1
        inc_str = f"{d.incoming_num} от {d.incoming_date.strftime('%d.%m.%Y')}" if d.incoming_num and d.incoming_date else (d.incoming_num or "")
        out_str = f"{d.outgoing_num} от {d.outgoing_date.strftime('%d.%m.%Y')}" if d.outgoing_num and d.outgoing_date else (d.outgoing_num or "")
        pages_str = f"{d.page_start}" if d.page_start == d.page_end else f"{d.page_start}-{d.page_end}"
        
        full_desc = d.title
        if d.doc_num: full_desc += f" №{d.doc_num}"
        if d.organ: full_desc += f", {d.organ}"

        ws.cell(row=row, column=1, value=i).alignment = center
        ws.cell(row=row, column=2, value=inc_str).alignment = center
        ws.cell(row=row, column=3, value=out_str).alignment = center
        ws.cell(row=row, column=4, value=d.copy_num or "1").alignment = center
        ws.cell(row=row, column=5, value=full_desc).alignment = left
        ws.cell(row=row, column=6, value=pages_str).alignment = center
        ws.cell(row=row, column=7, value="").alignment = center
        for c in range(1, 8): ws.cell(row=row, column=c).border = border

    tr = start_row + len(docs) + 2
    ws.merge_cells(start_row=tr, start_column=1, end_row=tr, end_column=3); ws.cell(row=tr, column=1, value="Всего в опись внесено").alignment = Alignment(horizontal="right")
    ws.merge_cells(start_row=tr, start_column=4, end_row=tr, end_column=5); ws.cell(row=tr, column=4, value=f"{len(docs)} ({number_to_words(len(docs))})").alignment = center
    ws.cell(row=tr, column=6, value="документов,").alignment = left

    ws.merge_cells(start_row=tr+1, start_column=1, end_row=tr+1, end_column=3); ws.cell(row=tr+1, column=1, value="на").alignment = Alignment(horizontal="right")
    tp = sum(d.page_count for d in docs)
    ws.merge_cells(start_row=tr+1, start_column=4, end_row=tr+1, end_column=5); ws.cell(row=tr+1, column=4, value=f"{tp} ({number_to_words(tp)})").alignment = center
    ws.cell(row=tr+1, column=6, value="листах.").alignment = left

    ws.merge_cells(start_row=tr+3, start_column=1, end_row=tr+3, end_column=7); ws.cell(row=tr+3, column=1, value="листов из дела изъято, взамен их подшито _____________________________________").alignment = left
    ws.merge_cells(start_row=tr+4, start_column=1, end_row=tr+4, end_column=7); ws.cell(row=tr+4, column=1, value="справок-заместителей.").alignment = left
    ws.merge_cells(start_row=tr+6, start_column=1, end_row=tr+6, end_column=7); ws.cell(row=tr+6, column=1, value="Опись составил: ___________________________________________________________").alignment = left
    ws.merge_cells(start_row=tr+7, start_column=2, end_row=tr+7, end_column=7); ws.cell(row=tr+7, column=2, value="(должность, ф.и.о. сотрудника, его подпись с указанием даты)").alignment = center

    ws.column_dimensions['A'].width = 12; ws.column_dimensions['B'].width = 25; ws.column_dimensions['C'].width = 25; ws.column_dimensions['D'].width = 10; ws.column_dimensions['E'].width = 55; ws.column_dimensions['F'].width = 10; ws.column_dimensions['G'].width = 25

    output = io.BytesIO(); wb.save(output); output.seek(0)
    filename = f"delo_{delo.index_code.replace('/', '_')}_tom_{tom.tom_number}.xlsx"
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@router.post("/{tom_id}/reorder")
async def reorder_tom_documents(tom_id: int, data: ReorderIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tom, delo = await _check_access(db, tom_id, user)
    if user.role == "admin" or delo.status == "closed" or tom.status != "open": raise HTTPException(409, "Том закрыт")
    docs = (await db.execute(select(Document).where(Document.tom_id == tom_id))).scalars().all()
    if len(data.order) != len(docs): raise HTTPException(422)
    by_id = {d.id: d for d in docs}
    if any(d_id not in by_id for d_id in data.order): raise HTTPException(422)
    for d in docs: d.order_in_tom = -d.id; d.page_start = -d.id
    await db.flush()
    updates = []; cursor = 1
    for new_pos, doc_id in enumerate(data.order):
        d = by_id[doc_id]; updates.append((d, new_pos + 1, cursor)); cursor += d.page_count
    for d, order, ps in updates:
        d.order_in_tom = order; d.page_start = ps; d.page_end = ps + d.page_count - 1
    await db.commit()
    return {"ok": True}
