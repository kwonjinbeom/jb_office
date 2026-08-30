from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


VERIFIED_ON = "2026-08-30"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "portfolio"
OUTPUT_FILE = OUTPUT_DIR / "AI_Meeting_Assistants_5_Vendor_Source_Verified_Comparison_2026-08-30.xlsx"

NAVY = "172A3A"
BLUE = "246BCE"
TEAL = "0F8B8D"
PALE_BLUE = "EAF2FB"
PALE_TEAL = "E7F5F4"
PALE_GOLD = "FFF4D6"
PALE_RED = "FCE8E6"
PALE_GREEN = "E6F4EA"
WHITE = "FFFFFF"
GRAY = "68737D"
LIGHT_GRAY = "F5F7F9"
GRID = "D9E1E8"

sources = {
    "fireflies_pricing": "https://fireflies.ai/pricing",
    "fireflies_business": "https://guide.fireflies.ai/articles/2063312779-fireflies-business-tier-pricing-and-features",
    "fathom_pricing": "https://www.fathom.ai/pricing",
    "fathom_free_premium": "https://help.fathom.video/en/articles/5290881",
    "fathom_devices": "https://help.fathom.video/en/articles/296576",
    "fathom_languages": "https://help.fathom.video/en/articles/296192",
    "otter_pricing": "https://otter.ai/pricing",
    "tldv_pricing": "https://tldv.io/blog/tldv-honest-review/",
    "tldv_free": "https://intercom.help/tldv/en/articles/8919450-what-are-the-limits-of-the-free-plan",
    "tldv_api": "https://intercom.help/tldv/en/articles/11583137-api",
    "tldv_languages": "https://intercom.help/tldv/en/articles/6231678-how-to-change-transcript-language",
    "tldv_desktop": "https://intercom.help/tldv/en/articles/14433922-record-meetings-on-any-platform-with-or-without-a-bot-tl-dv-desktop-app",
    "tldv_mobile": "https://intercom.help/tldv/en/articles/8490450-mobile-app",
    "tldv_terms": "https://tldv.io/terms/",
    "meetgeek_pricing": "https://meetgeek.ai/pricing",
    "meetgeek_plans": "https://support.meetgeek.ai/en/articles/8979527-choosing-subscriptions-team-plans",
}

summary_rows = [
    {
        "vendor": "Fireflies.ai",
        "free": "Yes",
        "free_allowance": "Unlimited transcription; 400 min storage/team",
        "paid_plan": "Pro",
        "monthly": 18.00,
        "annual": 10.00,
        "best_fit": "Broad-language teams needing API access and integrations at a low annual price",
        "caveat": "Free transcription is unlimited, but storage is capped; advanced AI uses credits",
        "source": sources["fireflies_pricing"],
    },
    {
        "vendor": "Fathom",
        "free": "Yes",
        "free_allowance": "Unlimited recordings, storage and transcription; 5 advanced summaries/mo",
        "paid_plan": "Team (2-user minimum)",
        "monthly": 19.00,
        "annual": 15.00,
        "best_fit": "Teams prioritizing generous free capture and straightforward meeting collaboration",
        "caveat": "No current mobile-device recording support; team plan has a 2-user minimum",
        "source": sources["fathom_pricing"],
    },
    {
        "vendor": "Otter.ai",
        "free": "Yes",
        "free_allowance": "300 transcription min/mo; 3 lifetime file imports",
        "paid_plan": "Pro (up to 5 billed users)",
        "monthly": 16.99,
        "annual": 8.33,
        "best_fit": "Small English-led teams wanting the lowest listed annual entry price",
        "caveat": "Only 6 listed transcription languages; API, SSO and video replay are Enterprise",
        "source": sources["otter_pricing"],
    },
    {
        "vendor": "tl;dv",
        "free": "Yes",
        "free_allowance": "Unlimited recordings/transcripts; AI and retention caps apply",
        "paid_plan": "Pro",
        "monthly": 29.00,
        "annual": 18.00,
        "best_fit": "Sales/customer teams needing recordings, CRM workflows and an API",
        "caveat": "Highest entry price here; free recordings are archived and AI usage is capped",
        "source": sources["tldv_pricing"],
    },
    {
        "vendor": "MeetGeek",
        "free": "Yes",
        "free_allowance": "3 transcription hours/mo; unlimited AI summaries",
        "paid_plan": "Pro",
        "monthly": 15.99,
        "annual": 9.99,
        "best_fit": "Multilingual teams valuing transparent retention and automation access",
        "caveat": "Pro is capped at 20 transcription hours/mo; HD video begins on Business",
        "source": sources["meetgeek_pricing"],
    },
]

pricing_rows = [
    ["Fireflies.ai", "Free", "$0", "Unlimited", "400 min/team", "Not stated as time period", "Pro", 18.00, 10.00, "8,000 min storage/seat", "3-hour recording limit", "Published list price"],
    ["Fathom", "Free", "$0", "Unlimited", "Unlimited", "Unlimited", "Team", 19.00, 15.00, "Unlimited meetings", "2-user minimum", "Team-ready plan used; individual Premium is $20 monthly / $16 annual"],
    ["Otter.ai", "Basic", "$0", "300 min/mo", "25 most recent conversations", "Not published", "Pro", 16.99, 8.33, "1,200 min/mo; unlimited storage", "90 min/meeting; max 5 billed users", "India-only promotional prices excluded"],
    ["tl;dv", "Free Forever", "$0", "Unlimited*", "Recordings archived after 3 days", "3 months", "Pro", 29.00, 18.00, "Unlimited uploads and storage", "80 recordings/week; 2 concurrent", "*Fair-use: free plan capped at 40 recordings/week"],
    ["MeetGeek", "Basic", "$0", "3 hours/mo", "Transcript: 3 months", "Audio: 1 month", "Pro", 15.99, 9.99, "20 hours/mo", "Transcript 1 year; audio 6 months", "$0.50 per extra hour"],
]

feature_rows = [
    ["Fireflies.ai", "Zoom, Google Meet, Microsoft Teams, 10+", "100+", "Yes — Pro+", "Unlimited on Free", "AskFred + meeting search", "API listed on Free; unlimited integrations on Pro", "iOS + Android", "Enterprise", "Yes", "Free API access is unusually broad; advanced AI uses credits"],
    ["Fathom", "Zoom, Google Meet, Microsoft Teams", "38", "Yes", "5 advanced/mo on Free; unlimited advanced on paid", "Ask Fathom on Premium/Team", "CRM sync (HubSpot, Salesforce, Close) up to 3 users/domain; Zapier", "No current mobile recording; iOS announced as upcoming", "Enterprise", "Yes", "Desktop on Windows/Mac; bot-free experience was Mac-only at verification"],
    ["Otter.ai", "Zoom, Microsoft Teams, Google Meet", "6", "Enterprise video replay only", "Yes", "AI Chat within/across meetings; plan query caps", "Salesforce/HubSpot/Zapier on paid; API/webhooks Enterprise", "iOS + Android", "Enterprise (100-seat minimum stated)", "Yes", "Pro workspace permits up to 5 billed users"],
    ["tl;dv", "Zoom, Google Meet, Microsoft Teams; bot-free audio on other platforms", "30+", "Yes with bot; bot-free mode is audio-only", "First 10 meetings on Free; paid removes core AI-note cap", "Multi-meeting queries limited on Free/Pro; unlimited on Business", "5,000+ via Zapier on Pro; API on Pro/Business (alpha)", "No mature native online-meeting app; in-person beta", "Enterprise", "Yes", "Free retention and AI caps make it better for evaluation than a permanent archive"],
    ["MeetGeek", "Zoom, Google Meet, Microsoft Teams and more", "100+", "HD video on Business+", "Unlimited on Basic", "Global search + AI Chat; advanced tools on paid", "API + MCP on Basic; unlimited integrations on Pro", "Mobile apps + Chrome extension", "Enterprise", "Yes", "Basic includes API/MCP; Pro has 20-hour monthly transcription cap"],
]

source_rows = [
    ["Fireflies.ai", "Pricing, allowances, platforms, languages, mobile, API, SSO", "Official pricing page", VERIFIED_ON, "Verified", sources["fireflies_pricing"], "Primary source for current public plan data"],
    ["Fireflies.ai", "Business plan pricing and features", "Official help guide", VERIFIED_ON, "Verified", sources["fireflies_business"], "Secondary cross-check; live pricing page takes precedence if figures conflict"],
    ["Fathom", "Individual/team prices, minimum seats, feature tiers", "Official pricing page", VERIFIED_ON, "Verified", sources["fathom_pricing"], "Dynamic page shows annual and monthly values together"],
    ["Fathom", "Free/Premium allowances, languages, AI summaries, CRM sync", "Official help center", VERIFIED_ON, "Verified", sources["fathom_free_premium"], "Article edited 2026-06-04"],
    ["Fathom", "Supported devices and meeting platforms", "Official help center", VERIFIED_ON, "Verified", sources["fathom_devices"], "Article edited 2026-05-04"],
    ["Fathom", "38 supported transcription languages", "Official help center", VERIFIED_ON, "Verified", sources["fathom_languages"], "Korean is included"],
    ["Otter.ai", "All pricing, limits, languages, mobile, integrations, API, SSO", "Official pricing page", VERIFIED_ON, "Verified", sources["otter_pricing"], "India-issued-card promotional values excluded"],
    ["tl;dv", "Current Free/Pro/Business pricing and paid features", "Official vendor blog", VERIFIED_ON, "Verified", sources["tldv_pricing"], "Official pricing explainer; exact prices were not exposed in the public static pricing page"],
    ["tl;dv", "Free-plan AI, upload, retention and meeting caps", "Official help center", VERIFIED_ON, "Verified", sources["tldv_free"], "Free-plan operational limits"],
    ["tl;dv", "API eligibility and alpha status", "Official help center", VERIFIED_ON, "Verified", sources["tldv_api"], "API requires Pro or Business"],
    ["tl;dv", "30+ transcription languages", "Official help center", VERIFIED_ON, "Verified", sources["tldv_languages"], "Korean is listed"],
    ["tl;dv", "Supported platforms and bot-free desktop capture", "Official help center", VERIFIED_ON, "Verified", sources["tldv_desktop"], "Bot-free captures system audio on Mac/Windows"],
    ["tl;dv", "Mobile availability", "Official help center", VERIFIED_ON, "Verified", sources["tldv_mobile"], "Online-meeting native app not mature; in-person app in early testing"],
    ["tl;dv", "Weekly and concurrent recording limits", "Official terms", VERIFIED_ON, "Verified", sources["tldv_terms"], "Free 40/week, Pro 80/week, Business 120/week"],
    ["MeetGeek", "Pricing, allowances, retention, languages, API/MCP, mobile, SSO", "Official pricing page", VERIFIED_ON, "Verified", sources["meetgeek_pricing"], "Primary source for current plan data"],
    ["MeetGeek", "Plan selection and mixed subscriptions", "Official help center", VERIFIED_ON, "Verified", sources["meetgeek_plans"], "Pricing page is identified by vendor as the always-current source"],
]


def style_title(ws, title, subtitle, last_col):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    ws["A1"] = title
    ws["A1"].font = Font(name="Aptos Display", size=22, bold=True, color=WHITE)
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 36
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=last_col)
    ws["A2"] = subtitle
    ws["A2"].font = Font(name="Aptos", size=10, color=GRAY, italic=True)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 30


def style_table(ws, header_row, widths, freeze_cell):
    thin = Side(style="thin", color=GRID)
    for cell in ws[header_row]:
        if cell.value is None:
            continue
        cell.font = Font(name="Aptos", size=10, bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = Border(bottom=thin)
    ws.row_dimensions[header_row].height = 36
    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        for cell in row:
            cell.font = Font(name="Aptos", size=10, color=NAVY)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = Border(bottom=thin)
        ws.row_dimensions[row[0].row].height = 58
        if row[0].row % 2 == 0:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor=LIGHT_GRAY)
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = freeze_cell
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(ws.max_column)}{ws.max_row}"
    ws.sheet_view.showGridLines = False


def add_source_hyperlinks(ws, col_idx, start_row, end_row):
    for row in range(start_row, end_row + 1):
        cell = ws.cell(row, col_idx)
        if isinstance(cell.value, str) and cell.value.startswith("http"):
            cell.hyperlink = cell.value
            cell.style = "Hyperlink"
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def build_workbook():
    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = "Source-Verified AI Meeting Assistant Comparison"
    wb.properties.subject = "Five-vendor pricing and feature comparison with an auditable source ledger"
    wb.properties.creator = "Source-verified research portfolio sample"
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"

    # Executive summary
    ws = wb.create_sheet("Executive_Summary")
    headers = [
        "Vendor", "Free plan", "Free allowance", "First team-ready paid plan",
        "Monthly USD\n/user/mo", "Annual USD\n/user/mo", "5 users: monthly cost\non annual billing",
        "Annual savings\nvs monthly", "Best fit", "Main caveat", "Verified on", "Primary official source"
    ]
    style_title(
        ws,
        "AI Meeting Assistants — 5-Vendor Source-Verified Comparison",
        "Public USD list prices and published feature limits, checked against official vendor pages on 2026-08-30. Taxes, promotions and negotiated enterprise pricing are excluded.",
        len(headers),
    )
    ws.append([])
    ws.append(headers)
    for item in summary_rows:
        row = ws.max_row + 1
        ws.append([
            item["vendor"], item["free"], item["free_allowance"], item["paid_plan"],
            item["monthly"], item["annual"], f"=F{row}*5", f"=1-(F{row}/E{row})",
            item["best_fit"], item["caveat"], VERIFIED_ON, item["source"],
        ])
    style_table(ws, 4, [18, 11, 34, 27, 14, 14, 19, 16, 35, 38, 13, 42], "A5")
    for row in range(5, 10):
        for col in (5, 6, 7):
            ws.cell(row, col).number_format = '$0.00'
        ws.cell(row, 8).number_format = '0%'
        if ws.cell(row, 2).value == "Yes":
            ws.cell(row, 2).fill = PatternFill("solid", fgColor=PALE_GREEN)
    add_source_hyperlinks(ws, 12, 5, 9)
    ws.conditional_formatting.add("F5:F9", ColorScaleRule(start_type="min", start_color="63BE7B", mid_type="percentile", mid_value=50, mid_color="FFEB84", end_type="max", end_color="F8696B"))

    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = "First team-ready paid plan — annual USD/user/month"
    chart.y_axis.title = "Vendor"
    chart.x_axis.title = "USD per user/month"
    chart.height = 7.2
    chart.width = 16
    data = Reference(ws, min_col=6, min_row=4, max_row=9)
    cats = Reference(ws, min_col=1, min_row=5, max_row=9)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.legend = None
    ws.add_chart(chart, "A12")
    ws["I12"] = "Interpretation guardrails"
    ws["I12"].font = Font(name="Aptos", bold=True, color=WHITE)
    ws["I12"].fill = PatternFill("solid", fgColor=TEAL)
    guardrails = [
        "Cheapest is not automatically best: usage caps, language coverage and admin requirements differ.",
        "The 5-user figure is a normalized estimate: annual per-user rate × 5, not a checkout quote.",
        "Rows marked as Enterprise or 'not published' should be confirmed with sales before procurement.",
    ]
    for idx, note in enumerate(guardrails, start=13):
        ws.merge_cells(start_row=idx, start_column=9, end_row=idx, end_column=12)
        ws.cell(idx, 9).value = f"• {note}"
        ws.cell(idx, 9).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(idx, 9).fill = PatternFill("solid", fgColor=PALE_TEAL)
        ws.row_dimensions[idx].height = 34

    # Pricing and limits
    ws = wb.create_sheet("Pricing_and_Limits")
    headers = ["Vendor", "Free plan", "Free price", "Free transcription/recording", "Free storage/history", "Free retention", "Compared paid plan", "Monthly USD/user", "Annual USD/user/mo", "Paid usage/storage", "Operational limit", "Research note"]
    style_title(ws, "Pricing & Usage Limits", "Comparable public list-price data. Blank or 'Not published' means the official pages reviewed did not state a value; it is not an estimate.", len(headers))
    ws.append([])
    ws.append(headers)
    for row in pricing_rows:
        ws.append(row)
    style_table(ws, 4, [18, 18, 12, 27, 27, 18, 24, 15, 15, 28, 28, 42], "A5")
    for row in range(5, 10):
        ws.cell(row, 8).number_format = '$0.00'
        ws.cell(row, 9).number_format = '$0.00'

    # Features
    ws = wb.create_sheet("Feature_Matrix")
    headers = ["Vendor", "Meeting platforms", "Transcription languages", "Video recording", "AI summaries on Free", "Chat/search across meetings", "Integrations / API", "Mobile", "SSO / SCIM", "Korean transcription", "Important nuance"]
    style_title(ws, "Feature Matrix", "Feature availability is plan-specific. The wording below preserves important plan gates instead of flattening every feature to Yes/No.", len(headers))
    ws.append([])
    ws.append(headers)
    for row in feature_rows:
        ws.append(row)
    style_table(ws, 4, [18, 35, 19, 29, 31, 36, 43, 32, 25, 18, 44], "A5")
    for row in range(5, 10):
        if ws.cell(row, 10).value == "Yes":
            ws.cell(row, 10).fill = PatternFill("solid", fgColor=PALE_GREEN)

    # Source ledger
    ws = wb.create_sheet("Source_Ledger")
    headers = ["Vendor", "Claim group", "Source type", "Checked on", "Status", "Official URL", "Research note"]
    style_title(ws, "Source Ledger", "One row per source. Every comparison cell can be traced to these official vendor pages; no affiliate or third-party review sites were used as evidence.", len(headers))
    ws.append([])
    ws.append(headers)
    for row in source_rows:
        ws.append(row)
    style_table(ws, 4, [18, 40, 23, 14, 14, 65, 48], "A5")
    add_source_hyperlinks(ws, 6, 5, ws.max_row)
    for row in range(5, ws.max_row + 1):
        status = ws.cell(row, 5)
        status.fill = PatternFill("solid", fgColor=PALE_GREEN if status.value == "Verified" else PALE_GOLD)

    # Methodology
    ws = wb.create_sheet("Methodology")
    style_title(ws, "Methodology & Quality Controls", "A concise audit trail for clients reviewing how the comparison was produced.", 4)
    sections = [
        ("Scope", [
            "Five widely used AI meeting assistants: Fireflies.ai, Fathom, Otter.ai, tl;dv and MeetGeek.",
            "Public plan and feature information available without account login on 2026-08-30.",
            "Currency normalized to USD list prices; tax, discounts, promotional prices and enterprise quotes excluded.",
        ]),
        ("Comparison rule", [
            "For the five-user estimate, use the first public paid plan that can reasonably serve a small team.",
            "Monthly cost on annual billing = published annual per-user monthly rate × 5 users.",
            "Different usage caps and collaboration features mean the normalized price is directional, not a procurement quote.",
        ]),
        ("Source policy", [
            "Use official pricing pages, official help centers, official terms and official vendor articles only.",
            "When official pages disagree, prefer the live pricing page and record the conflict in the source ledger.",
            "Never infer an unpublished price or feature. Use 'Not published' and recommend direct confirmation.",
        ]),
        ("Quality checks", [
            "All source URLs are clickable and paired with a verification date.",
            "Promotional values restricted by geography or payment method are excluded from the normalized comparison.",
            "Plan gates are preserved in text (for example, API on Enterprise only) instead of reducing features to a misleading Yes.",
        ]),
        ("Known limitations", [
            "Vendor pages can change after the verification date; refresh before a buying decision or client delivery.",
            "No account-level checkout, free-trial usage test, transcription accuracy benchmark or privacy-law assessment was performed.",
            "Feature names are vendor-defined and may not represent equivalent implementation quality.",
        ]),
    ]
    row_idx = 4
    for heading, bullets in sections:
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
        ws.cell(row_idx, 1).value = heading
        ws.cell(row_idx, 1).font = Font(name="Aptos", size=12, bold=True, color=WHITE)
        ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor=TEAL)
        ws.row_dimensions[row_idx].height = 24
        row_idx += 1
        for bullet in bullets:
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
            ws.cell(row_idx, 1).value = f"• {bullet}"
            ws.cell(row_idx, 1).font = Font(name="Aptos", size=10, color=NAVY)
            ws.cell(row_idx, 1).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row_idx, 1).fill = PatternFill("solid", fgColor=LIGHT_GRAY if row_idx % 2 == 0 else WHITE)
            ws.row_dimensions[row_idx].height = 32
            row_idx += 1
        row_idx += 1
    for col, width in zip(range(1, 5), [34, 24, 24, 24]):
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A4"
    ws.sheet_view.showGridLines = False

    # Workbook polish
    for ws in wb.worksheets:
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_margins.left = 0.25
        ws.page_margins.right = 0.25
        ws.page_margins.top = 0.5
        ws.page_margins.bottom = 0.5
        ws.oddFooter.center.text = "Source-verified portfolio sample | Verified 2026-08-30"
        ws.oddFooter.center.size = 8
        ws.oddFooter.center.color = GRAY

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_FILE)


def validate_workbook():
    wb = load_workbook(OUTPUT_FILE, data_only=False)
    expected_sheets = ["Executive_Summary", "Pricing_and_Limits", "Feature_Matrix", "Source_Ledger", "Methodology"]
    assert wb.sheetnames == expected_sheets, wb.sheetnames
    assert wb["Executive_Summary"].max_row >= 15
    assert wb["Pricing_and_Limits"].max_row == 9
    assert wb["Feature_Matrix"].max_row == 9
    assert wb["Source_Ledger"].max_row == 20
    assert wb["Executive_Summary"]["G5"].value == "=F5*5"
    assert wb["Executive_Summary"]["L5"].hyperlink is not None
    assert wb["Source_Ledger"]["F5"].hyperlink is not None
    assert len(wb["Executive_Summary"]._charts) == 1
    return {
        "path": str(OUTPUT_FILE),
        "size_bytes": OUTPUT_FILE.stat().st_size,
        "sheets": wb.sheetnames,
        "vendors": [wb["Executive_Summary"].cell(row, 1).value for row in range(5, 10)],
        "sources": wb["Source_Ledger"].max_row - 4,
    }


if __name__ == "__main__":
    build_workbook()
    print(validate_workbook())
