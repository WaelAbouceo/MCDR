import os
import random
from datetime import datetime, timedelta

import pymysql
from faker import Faker

fake = Faker("ar_AA")

INVESTOR_COUNT = 50000
SECURITY_COUNT = 250

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "mcdr")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "mcdr_pass")

# ─── Egyptian Name Pools (sourced from census & forebears.io) ────

_MALE_FIRST = [
    "محمد", "محمد", "محمد", "أحمد", "أحمد", "أحمد", "محمود", "محمود",
    "مصطفى", "مصطفى", "عمرو", "عمرو", "علي", "علي", "إبراهيم", "إبراهيم",
    "خالد", "خالد", "عمر", "عمر",
    "حسن", "حسين", "يوسف", "كريم", "طارق", "نبيل", "سمير", "شريف",
    "رامي", "حسام", "أشرف", "وليد", "عادل", "جمال", "فادي", "ماجد",
    "إيهاب", "وائل", "سامر", "باسم", "تامر", "هشام", "ياسر", "عصام",
    "مروان", "أيمن", "زياد", "سيف", "بلال", "عبدالله", "عبدالرحمن",
    "أنور", "رضا", "مدحت", "صلاح", "ممدوح", "مجدي", "رمضان", "سعد",
    "صالح", "سعيد", "كمال", "عاطف", "محسن", "منير", "ناصر", "عماد",
    "بهاء", "هاني", "أسامة", "حاتم", "ثروت", "مينا", "جورج", "بطرس",
]
_FEMALE_FIRST = [
    "إيمان", "إيمان", "منى", "منى", "هبة", "هبة", "آية", "آية",
    "مروة", "مروة", "علاء", "سارة", "سارة", "أسماء", "أميرة",
    "فاطمة", "نور", "هنا", "مريم", "ياسمين", "دينا", "رانيا", "ليلى",
    "أمل", "نهى", "سلمى", "نهلة", "غادة", "سميرة", "ريم", "هالة",
    "داليا", "لمياء", "مها", "نورهان", "شيماء", "عبير", "سحر", "مي",
    "رضوى", "هدى", "سهام", "نجلاء", "إسراء", "دعاء", "ندى", "رنا",
    "حنان", "سناء", "ناهد", "منال", "نيفين", "مارينا", "كريستين",
]
_LAST = [
    "محمد", "محمد", "محمد", "أحمد", "أحمد", "أحمد", "علي", "علي",
    "حسن", "حسن", "محمود", "محمود", "إبراهيم", "إبراهيم",
    "صلاح", "مصطفى", "عادل", "جمال",
    "سعد", "السيد", "سمير", "عمر", "حسين", "كمال", "مجدي", "سالم",
    "صالح", "رمضان", "حمدي", "خالد", "سعيد", "فاروق", "منصور",
    "عبدالرحمن", "ناصر", "سليمان", "فهمي", "عبدالله", "يوسف", "عثمان",
    "المصري", "حلمي", "شاكر", "جابر", "توفيق", "بركات", "حسنين",
    "زكي", "كامل", "رفعت", "بدوي", "الشافعي", "عوض", "رزق", "خليل",
    "الجمال", "عبدالعزيز", "عبدالحميد", "عبدالفتاح", "البنا", "الششتاوي",
]

_MALE_FIRST_EN = [
    "Mohamed", "Mohamed", "Ahmed", "Ahmed", "Mahmoud", "Mahmoud",
    "Mostafa", "Amr", "Ali", "Ibrahim", "Khaled", "Omar",
    "Hassan", "Hussein", "Youssef", "Karim", "Tarek", "Sherif",
    "Ramy", "Hossam", "Waleed", "Fady", "Wael", "Tamer", "Hesham",
    "Yasser", "Essam", "Marwan", "Ayman", "Ziad", "Seif", "Adel",
    "Gamal", "Samir", "Nabil", "Ashraf", "Magdy", "Saad", "Emad",
    "Hany", "Osama", "Hatem", "Mina", "George",
]
_FEMALE_FIRST_EN = [
    "Eman", "Eman", "Mona", "Mona", "Heba", "Heba", "Aya", "Aya",
    "Marwa", "Sara", "Asmaa", "Amira",
    "Fatma", "Nour", "Mariam", "Yasmin", "Dina", "Rania", "Laila",
    "Salma", "Dalia", "Reem", "Hala", "Shimaa", "Noha", "Ghada",
    "Nahla", "Maha", "Nourhan", "Esraa", "Doaa", "Nada", "Rana",
    "Hanan", "Manal", "Neveen", "Marina", "Christine",
]
_LAST_EN = [
    "Mohamed", "Mohamed", "Ahmed", "Ahmed", "Ali", "Ali",
    "Hassan", "Hassan", "Mahmoud", "Ibrahim",
    "Salah", "Mostafa", "Adel", "Gamal", "Saad", "El-Sayed",
    "Samir", "Omar", "Hussein", "Kamal", "Magdy", "Salem",
    "Saleh", "Ramadan", "Hamdy", "Khaled", "Saeed", "Farouk",
    "Mansour", "Abdel-Rahman", "Nasser", "Soliman", "Fahmy",
    "Abdallah", "Youssef", "Osman", "El-Masry", "Helmy", "Shaker",
    "Gaber", "Tawfik", "Barakat", "Zaki", "Kamel", "Khalil",
    "Abdel-Aziz", "Abdel-Hamid", "El-Banna",
]

_EG_INSTITUTIONS = [
    "البنك التجاري الدولي - مصر (CIB)", "البنك الأهلي المصري", "بنك مصر",
    "بنك القاهرة", "بنك التعمير والإسكان", "بنك كريدي أجريكول مصر",
    "البنك العربي الإفريقي الدولي", "بنك الإسكندرية", "بنك قناة السويس",
    "بنك فيصل الإسلامي المصري", "بنك قطر الوطني الأهلي", "المصرف المتحد",
    "إي إف جي هيرميس", "سي آي كابيتال", "بلتون المالية القابضة",
    "القلعة للاستشارات المالية", "إتش سي للأوراق المالية والاستثمار",
    "مجموعة طلعت مصطفى القابضة", "أوراسكوم للتنمية مصر",
    "السويدي إلكتريك", "القابضة المصرية الكويتية",
    "مجموعة إي فاينانس", "صندوق مصر السيادي",
    "الهيئة القومية للتأمين الاجتماعي", "بنك الاستثمار القومي",
]

_EG_SECURITIES = [
    ("COMI", "البنك التجاري الدولي - مصر"), ("TMGH", "مجموعة طلعت مصطفى القابضة"),
    ("SWDY", "السويدي إلكتريك"), ("ETEL", "المصرية للاتصالات"),
    ("EAST", "الشرقية - إيسترن كومباني"), ("MFPC", "مصر لإنتاج الأسمدة - موبكو"),
    ("EGAL", "مصر للألومنيوم"), ("ABUK", "أبو قير للأسمدة والصناعات الكيماوية"),
    ("EFIH", "إي فاينانس للاستثمارات المالية والرقمية"), ("HRHO", "إي إف جي هيرميس القابضة"),
    ("CCAP", "القلعة للاستشارات المالية"), ("PHDC", "بالم هيلز للتعمير"),
    ("ORWE", "النساجون الشرقيون"), ("SKPC", "سيدي كرير للبتروكيماويات"),
    ("ORAS", "أوراسكوم كونستراكشون"), ("HDBK", "بنك التعمير والإسكان"),
    ("AUTO", "جي بي أوتو"), ("MNHD", "مدينة نصر للإسكان والتعمير"),
    ("AMOC", "الإسكندرية للزيوت المعدنية"), ("JUFO", "جهينة للصناعات الغذائية"),
    ("CLHO", "القابضة المصرية الكويتية"), ("OCDI", "أوراسكوم للتنمية"),
    ("FWRY", "فوري لتكنولوجيا البنوك والمدفوعات الإلكترونية"),
    ("BINV", "بلتون المالية القابضة"), ("IRON", "حديد عز"),
]

_EGX_SECTORS = {
    "COMI": "البنوك والخدمات المالية", "TMGH": "العقارات",
    "SWDY": "الصناعات الهندسية", "ETEL": "الاتصالات وتكنولوجيا المعلومات",
    "EAST": "الأغذية والمشروبات والتبغ", "MFPC": "الكيماويات",
    "EGAL": "الموارد الأساسية", "ABUK": "الكيماويات",
    "EFIH": "البنوك والخدمات المالية", "HRHO": "البنوك والخدمات المالية",
    "CCAP": "البنوك والخدمات المالية", "PHDC": "العقارات",
    "ORWE": "الصناعات الهندسية", "SKPC": "الكيماويات",
    "ORAS": "التشييد ومواد البناء", "HDBK": "البنوك والخدمات المالية",
    "AUTO": "السيارات وقطع الغيار", "MNHD": "العقارات",
    "AMOC": "الطاقة والبترول", "JUFO": "الأغذية والمشروبات والتبغ",
    "CLHO": "البنوك والخدمات المالية", "OCDI": "العقارات",
    "IRON": "الموارد الأساسية", "FWRY": "الاتصالات وتكنولوجيا المعلومات",
    "BINV": "البنوك والخدمات المالية",
}
_extra_sectors = [
    "البنوك والخدمات المالية", "العقارات", "الأغذية والمشروبات والتبغ",
    "الكيماويات", "الموارد الأساسية", "الصناعات الهندسية",
    "الاتصالات وتكنولوجيا المعلومات", "التشييد ومواد البناء",
    "الطاقة والبترول", "الرعاية الصحية والأدوية", "التأمين", "السياحة والترفيه",
]


def _egyptian_name() -> str:
    gender = random.choice(["m", "f"])
    if random.random() < 0.7:
        first = random.choice(_MALE_FIRST if gender == "m" else _FEMALE_FIRST)
        last = random.choice(_LAST)
    else:
        first = random.choice(_MALE_FIRST_EN if gender == "m" else _FEMALE_FIRST_EN)
        last = random.choice(_LAST_EN)
    return f"{first} {last}"


def _egyptian_email(investor_id: int) -> str:
    first = random.choice(_MALE_FIRST_EN + _FEMALE_FIRST_EN).lower()
    last = random.choice(_LAST_EN).lower().replace("-", "")
    domain = random.choice(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"])
    return f"{first}.{last}{investor_id % 100}@{domain}"


def random_date(days_back=900):
    return datetime.now() - timedelta(days=random.randint(0, days_back))


def _conn(database):
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=database, charset="utf8mb4",
    )


# =========================
# CORE REGISTRY DB
# =========================

print("Populating mcdr_core database...")

core_conn = _conn("mcdr_core")
core = core_conn.cursor()

core.execute("DELETE FROM holdings")
core.execute("DELETE FROM securities")
core.execute("DELETE FROM investors")

BATCH_SIZE = 1000

# Insert Securities
sec_rows = []
for i in range(1, SECURITY_COUNT + 1):
    if i <= len(_EG_SECURITIES):
        ticker, company = _EG_SECURITIES[i - 1]
        sector = _EGX_SECTORS.get(ticker, random.choice(_extra_sectors))
    else:
        ticker = f"EGX{i:03}"
        company = fake.company()
        sector = random.choice(_extra_sectors)
    sec_rows.append((
        i,
        f"EGS{random.randint(1000000,9999999)}C01{i%10}",
        ticker, company, sector,
    ))
core.executemany(
    "INSERT INTO securities (security_id, isin, ticker, company_name, sector) VALUES (%s,%s,%s,%s,%s)",
    sec_rows,
)

# Insert Investors in batches
inv_rows = []
for i in range(1, INVESTOR_COUNT + 1):
    investor_type = "Institutional" if random.random() < 0.02 else "Retail"
    name = random.choice(_EG_INSTITUTIONS) if investor_type == "Institutional" else _egyptian_name()
    inv_rows.append((
        i, f"INV-{i:06}", name,
        str(random.randint(20000000000000, 39999999999999)) if investor_type == "Retail" else None,
        investor_type,
        random.choices(["Active", "Dormant", "Suspended"], weights=[85, 10, 5])[0],
        random_date().strftime("%Y-%m-%d"),
    ))
    if len(inv_rows) >= BATCH_SIZE:
        core.executemany(
            "INSERT INTO investors (investor_id, investor_code, full_name, national_id, investor_type, account_status, created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)", inv_rows,
        )
        inv_rows = []
if inv_rows:
    core.executemany(
        "INSERT INTO investors (investor_id, investor_code, full_name, national_id, investor_type, account_status, created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)", inv_rows,
    )

# Insert Holdings in batches
holding_id = 1
hold_rows = []
for investor_id in range(1, INVESTOR_COUNT + 1):
    for _ in range(random.randint(3, 12)):
        hold_rows.append((
            holding_id, investor_id, random.randint(1, SECURITY_COUNT),
            random.randint(10, 5000), round(random.uniform(5, 250), 2),
            random_date().strftime("%Y-%m-%d"),
        ))
        holding_id += 1
        if len(hold_rows) >= BATCH_SIZE:
            core.executemany(
                "INSERT INTO holdings (holding_id, investor_id, security_id, quantity, avg_price, last_updated) "
                "VALUES (%s,%s,%s,%s,%s,%s)", hold_rows,
            )
            hold_rows = []
if hold_rows:
    core.executemany(
        "INSERT INTO holdings (holding_id, investor_id, security_id, quantity, avg_price, last_updated) "
        "VALUES (%s,%s,%s,%s,%s,%s)", hold_rows,
    )

core_conn.commit()
core_conn.close()

# =========================
# MOBILE APP DB
# =========================

print("Populating mcdr_mobile database...")

mobile_conn = _conn("mcdr_mobile")
mobile = mobile_conn.cursor()

mobile.execute("DELETE FROM app_users")

app_user_id = 1
user_rows = []
for investor_id in range(1, INVESTOR_COUNT + 1):
    if random.random() < 0.6:
        user_rows.append((
            app_user_id, investor_id, f"user{investor_id}",
            "+20" + random.choice(["10", "11", "12", "15"]) + str(random.randint(10000000, 99999999)),
            _egyptian_email(investor_id),
            "$2b$12$mockhashvalue123456",
            1 if random.random() < 0.9 else 0,
            random.choices(["Active", "Locked", "Disabled"], weights=[90, 5, 5])[0],
            random_date(60).strftime("%Y-%m-%d %H:%M:%S"),
            random_date().strftime("%Y-%m-%d"),
        ))
        app_user_id += 1
        if len(user_rows) >= BATCH_SIZE:
            mobile.executemany(
                "INSERT INTO app_users (app_user_id, investor_id, username, mobile, email, password_hash, otp_verified, status, last_login, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", user_rows,
            )
            user_rows = []
if user_rows:
    mobile.executemany(
        "INSERT INTO app_users (app_user_id, investor_id, username, mobile, email, password_hash, otp_verified, status, last_login, created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", user_rows,
    )

mobile_conn.commit()
mobile_conn.close()

print("50K MCDR Mock Databases Generated Successfully.")
