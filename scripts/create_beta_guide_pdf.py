from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "WealthOS-Beta-Quick-Guide-AR.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

FONT = r"C:\Windows\Fonts\tahoma.ttf"
FONT_BOLD = r"C:\Windows\Fonts\tahomabd.ttf"
pdfmetrics.registerFont(TTFont("Arabic", FONT))
pdfmetrics.registerFont(TTFont("ArabicBold", FONT_BOLD))

NAVY = HexColor("#102947")
GOLD = HexColor("#B58A2B")
INK = HexColor("#10213A")
MUTED = HexColor("#66758A")
LINE = HexColor("#DCE3EB")
SOFT = HexColor("#F5F7FA")
GREEN = HexColor("#16845B")


def ar(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def right(c: canvas.Canvas, text: str, x: float, y: float, size=11, bold=False, color=INK):
    c.setFont("ArabicBold" if bold else "Arabic", size)
    c.setFillColor(color)
    c.drawRightString(x, y, ar(text))


def section(c: canvas.Canvas, number: str, title: str, items: list[str], y: float) -> float:
    c.setFillColor(NAVY)
    c.roundRect(43, y - 22, 509, 30, 7, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.circle(530, y - 7, 10, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(530, y - 10, number)
    right(c, title, 510, y - 12, 11.5, True, HexColor("#FFFFFF"))
    y -= 39
    for item in items:
        c.setFillColor(GOLD)
        c.circle(535, y + 3, 2.2, fill=1, stroke=0)
        right(c, item, 524, y, 10.2, False, INK)
        y -= 22
    return y - 5


c = canvas.Canvas(str(OUTPUT), pagesize=A4)
w, h = A4
c.setTitle("WealthOS Private Beta - Quick Guide")
c.setAuthor("WealthOS")

c.setFillColor(NAVY)
c.rect(0, h - 150, w, 150, fill=1, stroke=0)
c.setFillColor(GOLD)
c.roundRect(43, h - 77, 42, 42, 10, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 22)
c.drawCentredString(64, h - 64, "W")
c.setFillColor(HexColor("#FFFFFF"))
c.setFont("Helvetica-Bold", 18)
c.drawString(98, h - 58, "WealthOS")
right(c, "دليل التجربة السريع", 552, h - 105, 22, True, HexColor("#FFFFFF"))
right(c, "نسخة بيتا خاصة، بياناتك تبقى على جهازك", 552, h - 130, 11, False, HexColor("#DCE6F3"))

y = h - 180
y = section(c, "1", "قبل التشغيل", [
    "فك ضغط ملف النسخة بالكامل، ولا تشغّل البرنامج من داخل الملف المضغوط.",
    "احتفظ بملف البرنامج وملف التعليمات وملف الهوية داخل المجلد نفسه.",
    "استخدم النسخة المرسلة لك فقط، فهي مخصصة باسمك وبقاعدة بيانات مستقلة.",
], y)

y = section(c, "2", "تشغيل البرنامج", [
    "انقر مرتين على ملف التشغيل الموجود داخل المجلد.",
    "عند ظهور تحذير ويندوز، اختر معلومات إضافية ثم تشغيل على أي حال.",
    "اترك نافذة الخادم الصغيرة مفتوحة؛ سيفتح WealthOS تلقائيًا في المتصفح.",
], y)

c.setFillColor(SOFT)
c.roundRect(75, y - 13, 445, 30, 8, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 11)
c.drawCentredString(w / 2, y - 3, "WealthOS Beta.exe")
y -= 38

y = section(c, "3", "الخصوصية والبيانات", [
    "جميع بيانات التجربة تُحفظ محليًا على جهازك ولا تُشارك مع المختبرين الآخرين.",
    "ابدأ ببيانات تجريبية، وتجنب رفع مستند يحتوي أرقامًا أو معلومات حساسة كاملة.",
    "لا ترسل مجلد بيانات البرنامج أو نسخه الاحتياطية لأي شخص.",
], y)

y = section(c, "4", "إرسال الملاحظات", [
    "اكتب اسم الصفحة، والخطوة التي نفذتها، والنتيجة التي توقعتها والنتيجة التي ظهرت.",
    "يمكن إرفاق صورة للشاشة بعد إخفاء الأسماء والأرقام وأي بيانات مالية حساسة.",
    "عند الانتهاء أغلق المتصفح، ثم أغلق نافذة WealthOS الصغيرة.",
], y)

c.setStrokeColor(LINE)
c.line(43, 56, 552, 56)
c.setFillColor(GREEN)
c.circle(535, 34, 4, fill=1, stroke=0)
right(c, "شكرًا لمساعدتنا في بناء تجربة مالية أوضح وأكثر أمانًا", 524, 30, 9.5, True, MUTED)
c.setFillColor(MUTED)
c.setFont("Helvetica", 7.5)
c.drawString(43, 30, "PRIVATE BETA  |  v0.1.0")

c.save()
print(OUTPUT)
