import csv
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings
from ..models import ExternalDocumentStaging, Document, DocumentChange

def _parse_date(val: str):
    if not val: return None
    try: return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except ValueError: return None

def _open_csv(path: Path):
    f = path.open("r", encoding="utf-8-sig", newline="")
    sample = f.read(4096); f.seek(0)
    try: dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error: dialect = csv.excel
    return f, csv.DictReader(f, dialect=dialect)

async def sync_from_csv(db: AsyncSession) -> dict:
    path = Path(settings.csv_source_path)
    if not path.exists(): return {"ok": False, "error": f"Файл не найден: {path}"}

    f, reader = _open_csv(path)
    rows: dict[str, dict] = {}
    
    try:
        for lineno, raw in enumerate(reader, start=2):
            ref = (raw.get("external_ref") or "").strip()
            title = (raw.get("title") or "").strip()
            if not ref or not title: continue
            try: pc = int((raw.get("page_count") or "0").strip())
            except ValueError: continue
            
            rows[ref] = {
                "external_ref": ref, "title": title,
                "account_number": (raw.get("account_number") or "").strip() or None,
                "page_count": pc,
                "incoming_num": (raw.get("incoming_num") or "").strip() or None,
                "incoming_date": _parse_date(raw.get("incoming_date", "")),
                "outgoing_num": (raw.get("outgoing_num") or "").strip() or None,
                "outgoing_date": _parse_date(raw.get("outgoing_date", "")),
                "copy_num": (raw.get("copy_num") or "1").strip(),
                "cipher": (raw.get("cipher") or "").strip() or None,
                "grif": (raw.get("grif") or "").strip() or None,
                "organ": (raw.get("organ") or "").strip() or None,
                "doc_num": (raw.get("doc_num") or "").strip() or None,
                "employee": (raw.get("employee") or "").strip() or None,
            }
    finally: f.close()

    if not rows: return {"ok": False, "error": "Нет валидных строк"}

    now = datetime.utcnow()
    current_refs = set(rows.keys())
    existing_map = {e.external_ref: e for e in (await db.execute(select(ExternalDocumentStaging))).scalars().all()}
    added = updated = deleted = 0
    
    placed_docs = {d.external_ref: d for d in (await db.execute(select(Document).where(Document.external_ref.in_(current_refs)))).scalars().all()}

    # Словарь для перевода полей на русский
    field_names_ru = {
        "title": "Название",
        "doc_num": "№ документа",
        "organ": "Орган",
        "page_count": "Листов",
        "cipher": "Шифр",
        "incoming_num": "Вх. №"
    }

    for r in rows.values():
        e = existing_map.get(r["external_ref"])
        if e:
            for k, v in r.items(): setattr(e, k, v)
            e.synced_at = now; e.deleted_at = None; updated += 1
        else:
            db.add(ExternalDocumentStaging(**r, synced_at=now)); added += 1

        placed = placed_docs.get(r["external_ref"])
        if placed:
            fields_to_check = [
                ('title', 'title'), ('doc_num', 'doc_num'), ('organ', 'organ'),
                ('page_count', 'page_count'), ('cipher', 'cipher'), ('incoming_num', 'incoming_num')
            ]
            for f_name, f_key in fields_to_check:
                old_val = getattr(placed, f"original_{f_name}")
                new_val = r.get(f_key)
                
                if str(old_val or '') != str(new_val or ''):
                    db.add(DocumentChange(
                        document_id=placed.id, user_login='Внешняя БД', source='system',
                        field_name=field_names_ru.get(f_name, f_name), old_value=str(old_val or ''), new_value=str(new_val or '')
                    ))
                    setattr(placed, f"original_{f_name}", new_val)

    for ref, e in existing_map.items():
        if ref not in current_refs and e.deleted_at is None:
            e.deleted_at = now; deleted += 1

    await db.commit()
    return {"ok": True, "added": added, "updated": updated, "deleted": deleted, "total": len(rows)}
