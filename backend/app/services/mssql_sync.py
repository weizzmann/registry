"""
Синхронизация с внешней MS SQL. Заглушка — реализуется
при наличии доступа к MS SQL.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..models import ExternalDocumentStaging
from ..config import settings


async def sync_from_mssql(db: AsyncSession) -> dict:
    """Читает MS SQL и обновляет staging. Пока — no-op."""
    if not settings.mssql_conn:
        return {"skipped": True, "reason": "MSSQL_CONN не задан"}

    # Пример структуры (заполнить по реальной БД):
    # import pyodbc
    # conn = pyodbc.connect(settings.mssql_conn, readonly=True)
    # rows = conn.execute("SELECT ext_ref, title, acc_num, pages FROM v_docs").fetchall()
    # current_refs = set()
    # for r in rows:
    #     current_refs.add(r[0])
    #     await db.execute(text("""
    #         INSERT INTO external_documents_staging
    #           (external_ref, title, account_number, page_count, synced_at, deleted_at)
    #         VALUES (:r, :t, :a, :p, now(), NULL)
    #         ON CONFLICT (external_ref) DO UPDATE
    #         SET title=EXCLUDED.title, account_number=EXCLUDED.account_number,
    #             page_count=EXCLUDED.page_count, synced_at=now(), deleted_at=NULL
    #     """), {"r": r[0], "t": r[1], "a": r[2], "p": r[3]})
    # # помечаем исчезнувшие
    # if current_refs:
    #     await db.execute(text("""
    #         UPDATE external_documents_staging
    #         SET deleted_at = now()
    #         WHERE external_ref != ALL(:refs) AND deleted_at IS NULL
    #     """), {"refs": list(current_refs)})
    # await db.commit()

    return {"skipped": True, "reason": "not implemented"}