from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE = Path(__file__).resolve().parents[2]
PORTFOLIO_DIR = BASE / "portfolio"
ASSET_DIR = BASE / "sales_assets"
PDF_PATH = PORTFOLIO_DIR / "AI_Meeting_Assistants_5_Vendor_Comparison_Portfolio_Summary.pdf"
PNG_PATH = ASSET_DIR / "upwork_portfolio_preview_v1.png"

NAVY = "#172A3A"
BLUE = "#246BCE"
TEAL = "#0F8B8D"
PALE = "#F5F7F9"
GOLD = "#C69214"
WHITE = "#FFFFFF"
GRAY = "#68737D"
GRID = "#D9E1E8"

vendors = [
    {
        "name": "Fireflies.ai",
        "free": "Unlimited transcription; 400 min storage/team",
        "plan": "Pro",
        "monthly": 18.00,
        "annual": 10.00,
        "languages": "100+",
        "api": "Listed on Free",
        "note": "Broad language coverage and low annual entry price",
    },
    {
        "name": "Fathom",
        "free": "Unlimited recording, storage and transcription",
        "plan": "Team",
        "monthly": 19.00,
        "annual": 15.00,
        "languages": "38",
        "api": "Not publicly listed",
        "note": "Generous free capture; Team requires 2+ users",
    },
    {
        "name": "Otter.ai",
        "free": "300 transcription min/month",
        "plan": "Pro",
        "monthly": 16.99,
        "annual": 8.33,
        "languages": "6",
        "api": "Enterprise",
        "note": "Lowest annual entry; narrower language coverage",
    },
    {
        "name": "tl;dv",
        "free": "Unlimited recordings/transcripts; AI caps",
        "plan": "Pro",
        "monthly": 29.00,
        "annual": 18.00,
        "languages": "30+",
        "api": "Pro/Business (alpha)",
        "note": "Sales workflows and API; highest entry price",
    },
    {
        "name": "MeetGeek",
        "free": "3 transcription hours/month",
        "plan": "Pro",
        "monthly": 15.99,
        "annual": 9.99,
        "languages": "100+",
        "api": "API + MCP on Basic",
        "note": "Transparent retention; Pro capped at 20 hours",
    },
]

sources = [
    ("Fireflies.ai pricing", "https://fireflies.ai/pricing"),
    ("Fathom pricing", "https://www.fathom.ai/pricing"),
    ("Fathom Free vs Premium", "https://help.fathom.video/en/articles/5290881"),
    ("Otter.ai pricing", "https://otter.ai/pricing"),
    ("tl;dv official pricing explainer", "https://tldv.io/blog/tldv-honest-review/"),
    ("tl;dv Free plan limits", "https://intercom.help/tldv/en/articles/8919450-what-are-the-limits-of-the-free-plan"),
    ("tl;dv API", "https://intercom.help/tldv/en/articles/11583137-api"),
    ("MeetGeek pricing", "https://meetgeek.ai/pricing"),
]


def money(value):
    return f"${value:,.2f}"


def build_pdf():
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    font_regular = Path(r"C:\Windows\Fonts\arial.ttf")
    font_bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if font_regular.exists() and font_bold.exists():
        pdfmetrics.registerFont(TTFont("ArialLocal", str(font_regular)))
        pdfmetrics.registerFont(TTFont("ArialLocalBold", str(font_bold)))
        regular, bold = "ArialLocal", "ArialLocalBold"
    else:
        regular, bold = "Helvetica", "Helvetica-Bold"

    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=landscape(letter),
        leftMargin=0.38 * inch, rightMargin=0.38 * inch,
        topMargin=0.35 * inch, bottomMargin=0.35 * inch,
        title="Source-Verified AI Meeting Assistant Comparison",
        author="Source-verified research portfolio sample",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontName=bold, fontSize=22, leading=25, textColor=colors.HexColor(NAVY), alignment=TA_LEFT, spaceAfter=5)
    subtitle_style = ParagraphStyle("SubtitleCustom", parent=styles["BodyText"], fontName=regular, fontSize=8.5, leading=11, textColor=colors.HexColor(GRAY), spaceAfter=10)
    h2 = ParagraphStyle("H2Custom", parent=styles["Heading2"], fontName=bold, fontSize=13, leading=15, textColor=colors.HexColor(TEAL), spaceBefore=7, spaceAfter=5)
    body = ParagraphStyle("BodyCustom", parent=styles["BodyText"], fontName=regular, fontSize=8.5, leading=11, textColor=colors.HexColor(NAVY))
    small = ParagraphStyle("SmallCustom", parent=body, fontSize=7.4, leading=9)
    source_style = ParagraphStyle("SourceCustom", parent=body, fontSize=7.2, leading=9, textColor=colors.HexColor(BLUE))

    story = [
        Paragraph("AI Meeting Assistants — 5-Vendor Source-Verified Comparison", title_style),
        Paragraph("Public USD list prices and published feature limits verified against official vendor sources on 30 Aug 2026. Taxes, promotions and negotiated enterprise pricing are excluded.", subtitle_style),
    ]

    headers = ["Vendor", "Free allowance", "Team-ready plan", "Monthly", "Annual", "5 users / mo*", "Languages", "API", "Decision note"]
    table_data = [[Paragraph(h, small) for h in headers]]
    for v in vendors:
        table_data.append([
            Paragraph(f"<b>{v['name']}</b>", small),
            Paragraph(v["free"], small),
            Paragraph(v["plan"], small),
            money(v["monthly"]),
            money(v["annual"]),
            money(v["annual"] * 5),
            v["languages"],
            Paragraph(v["api"], small),
            Paragraph(v["note"], small),
        ])
    table = Table(table_data, colWidths=[0.78*inch, 1.65*inch, 0.85*inch, 0.62*inch, 0.62*inch, 0.77*inch, 0.58*inch, 1.12*inch, 1.70*inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor(BLUE)),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), bold),
        ("FONTNAME", (0,1), (-1,-1), regular),
        ("FONTSIZE", (0,0), (-1,-1), 7.2),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor(GRID)),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor(PALE)]),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.extend([table, Paragraph("* Normalized estimate: published annual per-user monthly rate × 5. It is not a checkout quote.", small), Spacer(1, 5)])

    insight_data = [
        [Paragraph("Lowest annual entry", small), Paragraph("Otter.ai Pro at $8.33/user/month, with a 1,200-minute monthly allowance and six listed transcription languages.", body)],
        [Paragraph("Broadest language coverage", small), Paragraph("Fireflies.ai and MeetGeek each publish support for 100+ transcription languages.", body)],
        [Paragraph("Most generous free capture", small), Paragraph("Fathom publishes unlimited recording, storage and transcription; advanced summaries are limited after the first five calls each month.", body)],
        [Paragraph("Key procurement warning", small), Paragraph("A lower price may hide usage, retention, language, API or admin limits. Plan gates are preserved rather than reduced to a misleading Yes/No.", body)],
    ]
    insights = Table(insight_data, colWidths=[1.45*inch, 8.25*inch])
    insights.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor(TEAL)),
        ("TEXTCOLOR", (0,0), (0,-1), colors.white),
        ("FONTNAME", (0,0), (0,-1), bold),
        ("ROWBACKGROUNDS", (1,0), (1,-1), [colors.HexColor("#E7F5F4"), colors.white]),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor(GRID)),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.extend([Paragraph("Decision Highlights", h2), insights])

    story.extend([
        PageBreak(),
        Paragraph("Methodology & Audit Trail", title_style),
        Paragraph("This sample demonstrates how public product information is converted into a traceable, decision-ready comparison.", subtitle_style),
        Paragraph("Research rules", h2),
        Paragraph("• Official pricing pages, help centers, terms and vendor documentation only.<br/>• Unpublished values are labeled, never estimated.<br/>• Region- or payment-method-specific promotions are excluded from the normalized comparison.<br/>• When official pages conflict, the current live pricing page takes precedence and the conflict is recorded.<br/>• Feature availability keeps its plan gate (for example, Enterprise only) instead of being flattened to Yes.", body),
        Paragraph("Quality controls", h2),
        Paragraph("• Each source is paired with a verification date.<br/>• Price units, team minimums, usage caps, retention and plan gates are checked separately.<br/>• Spreadsheet formulas, source hyperlinks, vendor count and source count are validated before delivery.<br/>• The full workbook contains five sheets: executive summary, pricing and limits, feature matrix, source ledger, and methodology.", body),
        Paragraph("Selected official sources", h2),
    ])
    source_table = []
    for name, url in sources:
        source_table.append([Paragraph(f"<b>{name}</b>", small), Paragraph(f'<link href="{url}">{url}</link>', source_style), "Checked 2026-08-30"])
    st = Table(source_table, colWidths=[1.65*inch, 7.15*inch, 1.25*inch])
    st.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor(PALE)]),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor(GRID)),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTNAME", (0,0), (-1,-1), regular),
        ("FONTSIZE", (0,0), (-1,-1), 7.2),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.extend([st, Spacer(1, 8), Paragraph("Limitations: no logged-in checkout, free-trial usage test, transcription-accuracy benchmark, or legal/privacy assessment was performed. Refresh public data before a procurement decision.", small)])

    def page_canvas(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(GRID))
        canvas.line(0.38*inch, 0.27*inch, 10.62*inch, 0.27*inch)
        canvas.setFont(regular, 7)
        canvas.setFillColor(colors.HexColor(GRAY))
        canvas.drawString(0.38*inch, 0.15*inch, "Source-verified research portfolio sample")
        canvas.drawRightString(10.62*inch, 0.15*inch, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_canvas, onLaterPages=page_canvas)


def load_font(size, bold=False):
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def fit_text(draw, text, box_width, start_size, min_size=16, bold=False):
    size = start_size
    while size >= min_size:
        font = load_font(size, bold=bold)
        if draw.textbbox((0, 0), text, font=font)[2] <= box_width:
            return font
        size -= 1
    return load_font(min_size, bold=bold)


def build_png():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1600, 1200
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 34), fill=TEAL)
    draw.rounded_rectangle((65, 65, width-65, height-65), radius=24, fill=WHITE, outline=GRID, width=2)

    title_font = fit_text(draw, "Source-Verified AI Software Comparison", 1410, 54, bold=True)
    subtitle_font = load_font(22)
    label_font = load_font(18, bold=True)
    body_font = load_font(17)
    small_font = load_font(15)
    draw.text((100, 96), "Source-Verified AI Software Comparison", font=title_font, fill=NAVY)
    draw.text((102, 162), "5 vendors · pricing · usage limits · feature gates · 16 official sources", font=subtitle_font, fill=GRAY)
    draw.rounded_rectangle((1240, 92, 1495, 150), radius=16, fill=BLUE)
    draw.text((1281, 109), "VERIFIED 2026-08-30", font=small_font, fill=WHITE)

    cols = [100, 330, 690, 865, 1030, 1210, 1495]
    header_y, row_h = 225, 105
    headers = ["Vendor", "Free allowance", "Plan", "Annual", "5 users/mo", "Decision note"]
    draw.rounded_rectangle((cols[0], header_y, cols[-1], header_y+58), radius=12, fill=BLUE)
    for i, header in enumerate(headers):
        draw.text((cols[i]+12, header_y+17), header, font=label_font, fill=WHITE)

    for idx, v in enumerate(vendors):
        y0 = header_y + 58 + idx*row_h
        fill = PALE if idx % 2 else WHITE
        draw.rectangle((cols[0], y0, cols[-1], y0+row_h), fill=fill, outline=GRID, width=1)
        values = [
            v["name"], v["free"], v["plan"], money(v["annual"]), money(v["annual"]*5), v["note"]
        ]
        widths = [cols[i+1]-cols[i]-24 for i in range(len(headers))]
        for i, value in enumerate(values):
            font = label_font if i == 0 else body_font
            max_chars = max(8, int(widths[i] / (font.size * 0.56)))
            lines = textwrap.wrap(value, width=max_chars)[:3]
            text_y = y0 + 14
            for line in lines:
                draw.text((cols[i]+12, text_y), line, font=font, fill=NAVY)
                text_y += 25

    bottom_y = header_y + 58 + len(vendors)*row_h + 35
    draw.rounded_rectangle((100, bottom_y, 1495, bottom_y+175), radius=16, fill="#E7F5F4")
    draw.text((128, bottom_y+22), "Research discipline", font=load_font(23, bold=True), fill=TEAL)
    bullets = [
        "Official vendor sources only — pricing pages, help centers, documentation and terms",
        "Unpublished values are labeled instead of estimated",
        "Plan gates, regional promotions and conflicting official pages are preserved as audit notes",
        "Full workbook: executive summary, pricing/limits, feature matrix, source ledger and methodology",
    ]
    for idx, bullet in enumerate(bullets):
        draw.ellipse((132, bottom_y+67+idx*27, 142, bottom_y+77+idx*27), fill=GOLD)
        draw.text((154, bottom_y+61+idx*27), bullet, font=body_font, fill=NAVY)

    draw.text((102, 1150), "Portfolio sample · Public information only · Refresh before procurement", font=small_font, fill=GRAY)
    image.save(PNG_PATH, format="PNG", optimize=True)


def validate():
    assert PDF_PATH.exists() and PDF_PATH.stat().st_size > 10_000
    assert PDF_PATH.read_bytes()[:4] == b"%PDF"
    with Image.open(PNG_PATH) as img:
        assert img.size == (1600, 1200)
        assert img.mode == "RGB"
    return {
        "pdf": str(PDF_PATH),
        "pdf_bytes": PDF_PATH.stat().st_size,
        "png": str(PNG_PATH),
        "png_bytes": PNG_PATH.stat().st_size,
        "png_size": "1600x1200",
    }


if __name__ == "__main__":
    build_pdf()
    build_png()
    print(validate())
