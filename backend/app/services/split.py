"""
Симуляция разбиения черновика по томам.
Правило: все промежуточные томы должны быть ровно max_pages (250).
Последний том может быть неполным.
"""
from typing import Optional

def simulate_split(
    items: list[dict],
    current_tom_number: Optional[int],
    current_end: int,
    max_pages: int,
    max_tom_number: int,
) -> list[dict]:
    """Возвращает список томов с раскладкой.

    Каждый элемент:
      {tom_number, existing, current_end, max_pages, items, final_page, is_last}
    """
    if not items:
        return []

    result: list[dict] = []
    
    # Логика инициализации первого тома в плане
    if current_tom_number is not None:
        is_existing = True
        tom_number = current_tom_number
        cursor = current_end + 1
        new_counter = max_tom_number
    else:
        is_existing = False
        new_counter = max_tom_number + 1
        tom_number = new_counter
        cursor = 1
        current_end = 0

    buf: list[dict] = []
    idx = 0

    while idx < len(items):
        item = items[idx]
        pc = int(item["page_count"])
        if pc <= 0 or pc > max_pages:
            raise ValueError(f"Некорректный page_count: {pc}")

        if cursor + pc - 1 <= max_pages:
            buf.append(item)
            cursor += pc
            idx += 1
        else:
            # закрываем текущий том
            result.append({
                "tom_number": tom_number,
                "existing": is_existing,
                "current_end": current_end if is_existing else 0,
                "max_pages": max_pages,
                "items": list(buf),
                "final_page": cursor - 1,
                "is_last": False,
            })
            new_counter += 1
            tom_number = new_counter
            is_existing = False
            current_end = 0
            cursor = 1
            buf = []

    if buf:
        result.append({
            "tom_number": tom_number,
            "existing": is_existing,
            "current_end": current_end if is_existing else 0,
            "max_pages": max_pages,
            "items": list(buf),
            "final_page": cursor - 1,
            "is_last": True,
        })

    if result:
        result[-1]["is_last"] = True

    return result


def validate_split(plan: list[dict]) -> list[dict]:
    """Возвращает список нарушений (все промежуточные должны быть full)."""
    violations = []
    for i, t in enumerate(plan):
        is_intermediate = i < len(plan) - 1
        if is_intermediate and t["final_page"] != t["max_pages"]:
            missing = t["max_pages"] - t["final_page"]
            violations.append({
                "tom_number": t["tom_number"],
                "filled": t["final_page"],
                "required": t["max_pages"],
                "missing": missing,
                "message": (
                    f"Том {t['tom_number']} будет {t['final_page']}/{t['max_pages']} л. "
                    f"Не хватает {missing} л. "
                    f"Промежуточный том должен быть ровно {t['max_pages']}."
                ),
            })
    return violations