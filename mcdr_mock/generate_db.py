import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("ar_AA")

INVESTOR_COUNT = 50000
SECURITY_COUNT = 250

# ─── Egyptian Name Pools (sourced from census & forebears.io) ────
# Weighted towards the most common names in Egypt

_MALE_FIRST = [
    # Top 10 most common (higher weight via repetition)
    "محمد", "محمد", "محمد", "أحمد", "أحمد", "أحمد", "محمود", "محمود",
    "مصطفى", "مصطفى", "عمرو", "عمرو", "علي", "علي", "إبراهيم", "إبراهيم",
    "خالد", "خالد", "عمر", "عمر",
    # Common
    "حسن", "حسين", "يوسف", "كريم", "طارق", "نبيل", "سمير", "شريف",
    "رامي", "حسام", "أشرف", "وليد", "عادل", "جمال", "فادي", "ماجد",
    "إيهاب", "وائل", "سامر", "باسم", "تامر", "هشام", "ياسر", "عصام",
    "مروان", "أيمن", "زياد", "سيف", "بلال", "عبدالله", "عبدالرحمن",
    "أنور", "رضا", "مدحت", "صلاح", "ممدوح", "مجدي", "رمضان", "سعد",
    "صالح", "سعيد", "كمال", "عاطف", "محسن", "منير", "ناصر", "عماد",
    "بهاء", "هاني", "أسامة", "حاتم", "ثروت", "مينا", "جورج", "بطرس",
]
_FEMALE_FIRST = [
    # Top 10 most common
    "إيمان", "إيمان", "منى", "منى", "هبة", "هبة", "آية", "آية",
    "مروة", "مروة", "علاء", "سارة", "سارة", "أسماء", "أميرة",
    # Common
    "فاطمة", "نور", "هنا", "مريم", "ياسمين", "دينا", "رانيا", "ليلى",
    "أمل", "نهى", "سلمى", "نهلة", "غادة", "سميرة", "ريم", "هالة",
    "داليا", "لمياء", "مها", "نورهان", "شيماء", "عبير", "سحر", "مي",
    "رضوى", "هدى", "سهام", "نجلاء", "إسراء", "دعاء", "ندى", "رنا",
    "حنان", "سناء", "ناهد", "منال", "نيفين", "مارينا", "كريستين",
]
_LAST = [
    # Top 10 most common Egyptian surnames (weighted)
    "محمد", "محمد", "محمد", "أحمد", "أحمد", "أحمد", "علي", "علي",
    "حسن", "حسن", "محمود", "محمود", "إبراهيم", "إبراهيم",
    "صلاح", "مصطفى", "عادل", "جمال",
    # Common
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


def _egyptian_name() -> str:
    """Return a random Egyptian name — ~70% Arabic script, ~30% Latin."""
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


# ─── Egyptian Listed Companies & Institutional Investors ─────────
# Sourced from EGX 30 components, Forbes Egypt Top 50, and major
# Egyptian investment firms / brokerage houses / banks

_EG_SECURITIES = [
    # EGX 30 blue chips
    ("COMI", "البنك التجاري الدولي - مصر"),
    ("TMGH", "مجموعة طلعت مصطفى القابضة"),
    ("SWDY", "السويدي إلكتريك"),
    ("ETEL", "المصرية للاتصالات"),
    ("EAST", "الشرقية - إيسترن كومباني"),
    ("MFPC", "مصر لإنتاج الأسمدة - موبكو"),
    ("EGAL", "مصر للألومنيوم"),
    ("ABUK", "أبو قير للأسمدة والصناعات الكيماوية"),
    ("EFIH", "إي فاينانس للاستثمارات المالية والرقمية"),
    ("HRHO", "إي إف جي هيرميس القابضة"),
    ("CCAP", "القلعة للاستشارات المالية"),
    ("PHDC", "بالم هيلز للتعمير"),
    ("ORWE", "النساجون الشرقيون"),
    ("SKPC", "سيدي كرير للبتروكيماويات"),
    ("ORAS", "أوراسكوم كونستراكشون"),
    ("HDBK", "بنك التعمير والإسكان"),
    ("AUTO", "جي بي أوتو"),
    ("MNHD", "مدينة نصر للإسكان والتعمير"),
    ("AMOC", "الإسكندرية للزيوت المعدنية"),
    ("JUFO", "جهينة للصناعات الغذائية"),
    # Large caps
    ("CLHO", "القابضة المصرية الكويتية"),
    ("OCDI", "أوراسكوم للتنمية"),
    ("EKHOA", "إيكو هيلث"),
    ("ISPH", "المتحدة للصيدلة"),
    ("BINV", "بلتون المالية القابضة"),
    ("CIEB", "بنك كريدي أجريكول مصر"),
    ("ESRS", "عز الدخيلة للصلب - الإسكندرية"),
    ("IRON", "حديد عز"),
    ("FWRY", "فوري لتكنولوجيا البنوك والمدفوعات الإلكترونية"),
    ("ELMS", "المصرية لمدينة الإنتاج الإعلامي"),
    ("MNHP", "مينافارم للأدوية"),
    ("UEFM", "مطاحن مصر العليا"),
    ("WCDF", "مطاحن وسط وغرب الدلتا"),
    ("EDFM", "مطاحن شرق الدلتا"),
    ("SUGR", "الدلتا للسكر"),
    ("AXPH", "الإسكندرية للأدوية والصناعات الكيماوية"),
    ("ACGC", "الإسكندرية لتداول الحاويات والبضائع"),
    ("ALCN", "الكابلات الكهربائية المصرية"),
    ("EGCH", "الكيماويات المصرية"),
    ("MILS", "مصر لتأمينات الحياة"),
]

_EG_INSTITUTIONS = [
    # Banks
    "البنك التجاري الدولي - مصر (CIB)",
    "البنك الأهلي المصري",
    "بنك مصر",
    "بنك القاهرة",
    "بنك التعمير والإسكان",
    "بنك كريدي أجريكول مصر",
    "البنك العربي الإفريقي الدولي",
    "بنك الإسكندرية",
    "بنك قناة السويس",
    "بنك فيصل الإسلامي المصري",
    "بنك قطر الوطني الأهلي",
    "المصرف المتحد",
    # Investment & brokerage firms
    "إي إف جي هيرميس",
    "سي آي كابيتال",
    "بلتون المالية القابضة",
    "القلعة للاستشارات المالية",
    "إتش سي للأوراق المالية والاستثمار",
    "أكيومن القابضة",
    "أبيكس المالية القابضة",
    "عكاظ لتداول الأوراق المالية",
    "شعاع كابيتال مصر",
    "رينيسانس كابيتال",
    "فاروس القابضة للاستثمارات المالية",
    "هيرميس لإدارة صناديق الاستثمار",
    "بايونيرز القابضة للاستثمارات المالية",
    "جلوبال إنفست للأوراق المالية",
    # Insurance
    "مصر لتأمينات الحياة",
    "المصرية للتأمين التكافلي",
    "أليانز مصر لتأمينات الحياة",
    # Holding companies & asset managers
    "مجموعة طلعت مصطفى القابضة",
    "أوراسكوم للتنمية مصر",
    "السويدي إلكتريك",
    "القابضة المصرية الكويتية",
    "مجموعة إي فاينانس",
    "المجموعة المالية هيرميس",
    "صندوق مصر السيادي",
    # Pension & government funds
    "الهيئة القومية للتأمين الاجتماعي",
    "صندوق التأمينات والمعاشات",
    "بنك الاستثمار القومي",
]

def random_date(days_back=900):
    return datetime.now() - timedelta(days=random.randint(0, days_back))

# =========================
# CORE REGISTRY DB
# =========================

core_conn = sqlite3.connect("mcdr_core.db")
core = core_conn.cursor()

core.executescript("""
DROP TABLE IF EXISTS investors;
DROP TABLE IF EXISTS securities;
DROP TABLE IF EXISTS holdings;

CREATE TABLE investors (
    investor_id INTEGER PRIMARY KEY,
    investor_code TEXT UNIQUE,
    full_name TEXT,
    national_id TEXT,
    investor_type TEXT,
    account_status TEXT,
    created_at TEXT
);

CREATE TABLE securities (
    security_id INTEGER PRIMARY KEY,
    isin TEXT UNIQUE,
    ticker TEXT,
    company_name TEXT,
    sector TEXT
);

CREATE TABLE holdings (
    holding_id INTEGER PRIMARY KEY,
    investor_id INTEGER,
    security_id INTEGER,
    quantity INTEGER,
    avg_price REAL,
    last_updated TEXT
);
""")

# Insert Securities — real EGX companies first, then generated ones
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
    "ESRS": "الموارد الأساسية", "IRON": "الموارد الأساسية",
    "FWRY": "الاتصالات وتكنولوجيا المعلومات", "BINV": "البنوك والخدمات المالية",
    "CIEB": "البنوك والخدمات المالية", "MNHP": "الرعاية الصحية والأدوية",
    "UEFM": "الأغذية والمشروبات والتبغ", "WCDF": "الأغذية والمشروبات والتبغ",
    "EDFM": "الأغذية والمشروبات والتبغ", "SUGR": "الأغذية والمشروبات والتبغ",
    "AXPH": "الرعاية الصحية والأدوية", "ACGC": "خدمات النقل والشحن",
    "ALCN": "الصناعات الهندسية", "EGCH": "الكيماويات",
    "MILS": "التأمين",
}
_extra_sectors = [
    "البنوك والخدمات المالية", "العقارات", "الأغذية والمشروبات والتبغ",
    "الكيماويات", "الموارد الأساسية", "الصناعات الهندسية",
    "الاتصالات وتكنولوجيا المعلومات", "التشييد ومواد البناء",
    "الطاقة والبترول", "الرعاية الصحية والأدوية", "التأمين", "السياحة والترفيه",
]

for i in range(1, SECURITY_COUNT + 1):
    if i <= len(_EG_SECURITIES):
        ticker, company = _EG_SECURITIES[i - 1]
        sector = _EGX_SECTORS.get(ticker, random.choice(_extra_sectors))
    else:
        ticker = f"EGX{i:03}"
        company = fake.company()
        sector = random.choice(_extra_sectors)
    core.execute("""
        INSERT INTO securities VALUES (?, ?, ?, ?, ?)
    """, (
        i,
        f"EGS{random.randint(1000000,9999999)}C01{i%10}",
        ticker,
        company,
        sector,
    ))

# Insert Investors
for i in range(1, INVESTOR_COUNT + 1):
    investor_type = "Institutional" if random.random() < 0.02 else "Retail"
    name = random.choice(_EG_INSTITUTIONS) if investor_type == "Institutional" else _egyptian_name()

    core.execute("""
        INSERT INTO investors VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        i,
        f"INV-{i:06}",
        name,
        str(random.randint(20000000000000,39999999999999)) if investor_type == "Retail" else None,
        investor_type,
        random.choices(["Active","Dormant","Suspended"], weights=[85,10,5])[0],
        random_date().strftime("%Y-%m-%d")
    ))

# Insert Holdings
holding_id = 1
for investor_id in range(1, INVESTOR_COUNT + 1):
    for _ in range(random.randint(3, 12)):
        core.execute("""
            INSERT INTO holdings VALUES (?, ?, ?, ?, ?, ?)
        """, (
            holding_id,
            investor_id,
            random.randint(1, SECURITY_COUNT),
            random.randint(10, 5000),
            round(random.uniform(5, 250), 2),
            random_date().strftime("%Y-%m-%d")
        ))
        holding_id += 1

core_conn.commit()
core_conn.close()

# =========================
# MOBILE APP DB
# =========================

mobile_conn = sqlite3.connect("mcdr_mobile.db")
mobile = mobile_conn.cursor()

mobile.executescript("""
DROP TABLE IF EXISTS app_users;

CREATE TABLE app_users (
    app_user_id INTEGER PRIMARY KEY,
    investor_id INTEGER,
    username TEXT UNIQUE,
    mobile TEXT,
    email TEXT,
    password_hash TEXT,
    otp_verified INTEGER,
    status TEXT,
    last_login TEXT,
    created_at TEXT
);
""")

app_user_id = 1

for investor_id in range(1, INVESTOR_COUNT + 1):
    if random.random() < 0.6:
        mobile.execute("""
            INSERT INTO app_users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_user_id,
            investor_id,
            f"user{investor_id}",
            "+20" + random.choice(["10", "11", "12", "15"]) + str(random.randint(10000000, 99999999)),
            _egyptian_email(investor_id),
            "$2b$12$mockhashvalue123456",
            1 if random.random() < 0.9 else 0,
            random.choices(["Active","Locked","Disabled"], weights=[90,5,5])[0],
            random_date(60).strftime("%Y-%m-%d %H:%M:%S"),
            random_date().strftime("%Y-%m-%d")
        ))
        app_user_id += 1

mobile_conn.commit()
mobile_conn.close()

print("✅ 50K MCDR Mock Databases Generated Successfully.")
