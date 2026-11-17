import csv
import random
from datetime import datetime, timedelta

NUM_RECORDS = 1000
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 12, 31)

prefixes = ["Справка-отзыв", "Аналитическая справка", "Справка-меморандум", "Сопроводительное письмо", "Выписка из приказа", "Служебная записка", "Акт сверки"]
organs = ["УУР УМВД России по Хабаровскому краю", "УЭБ и ПК УМВД России по Хабаровскому краю", "ОП №8 УМВД России по г. Хабаровску", "Следственный департамент", "УНК УМВД"]
grifs = ["", "Секретно", "ДСП", "Для служебного пользования"]
ciphers = ["Ш-45", "Ш-46", "Ш-100", "К-12", ""]
employees = ["188", "331", "477", "237", "112"]

def random_date():
    delta = END_DATE - START_DATE
    random_days = random.randint(0, delta.days)
    return (START_DATE + timedelta(days=random_days)).strftime("%Y-%m-%d")

with open('data/fake_source.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow([
        "external_ref", "title", "account_number", "page_count", 
        "incoming_num", "incoming_date", "outgoing_num", "outgoing_date", 
        "copy_num", "cipher", "grif", "organ", "doc_num", "employee"
    ])
    
    for i in range(1, NUM_RECORDS + 1):
        ref = f"EXT-{i:04d}"
        title = f"{random.choice(prefixes)}"
        acc_num = f"АС-{random.randint(100, 999)}"
        pages = random.randint(1, 15)
        
        has_incoming = random.choice([True, False])
        has_outgoing = random.choice([True, False])
        
        inc_num = f"{random.randint(1000, 9999)}с" if has_incoming else ""
        inc_date = random_date() if has_incoming else ""
        
        out_num = f"{random.randint(1000, 9999)}с" if has_outgoing else ""
        out_date = random_date() if has_outgoing else ""
        
        if not has_incoming and not has_outgoing:
            inc_num = f"{random.randint(1000, 9999)}с"
            inc_date = random_date()
            
        copy = random.choice(["1", "1", "1", "2", "3"])
        cipher = random.choice(ciphers)
        grif = random.choice(grifs)
        organ = random.choice(organs)
        doc_num = f"{random.randint(100, 999)}н/с"
        employee = random.choice(employees)

        writer.writerow([
            ref, title, acc_num, pages, inc_num, inc_date, out_num, out_date, 
            copy, cipher, grif, organ, doc_num, employee
        ])

print(f"✅ Успешно сгенерировано {NUM_RECORDS} записей в файл data/fake_source.csv")