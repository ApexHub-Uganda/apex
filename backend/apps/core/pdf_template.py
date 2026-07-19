"""
Globally reusable branded A4 PDF template for school documents.

Layout (portrait A4, white page):
  ┌────────────────────────────────────────────────────────────┐
  │  [LOGO]     School name / address / contacts     [QR CODE] │  ← header
  │  ════════════════════════════════════════════════════════  │  ← primary underline
  │                                                            │
  │                     document body                          │
  │                                                            │
  │  ════════════════════════════════════════════════════════  │  ← primary underline
  │  Motto · contacts                    Printed: YYYY-MM-DD   │  ← footer
  └────────────────────────────────────────────────────────────┘

Usage:
    from apps.core.pdf_template import build_branded_pdf, sample_preview_story

    pdf_bytes = build_branded_pdf(
        tenant=request.user.tenant,
        document_type="student_result",
        document_meta={"student": "ADM-001", "term": "Term 1"},
        title="Term 1 Report Card",
        build_story=lambda ctx: [... flowables ...],
    )
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.core.exports import escape_pdf_text
from apps.core.pdf_branding import build_tenant_branding, normalize_hex_color

# A4
PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 × 841.89 pt

# Margins leave room for fixed header/footer drawn on every page.
LEFT_MARGIN = 16 * mm
RIGHT_MARGIN = 16 * mm
TOP_MARGIN = 38 * mm
BOTTOM_MARGIN = 22 * mm

HEADER_TOP_PAD = 10 * mm
LOGO_SIZE = 18 * mm
QR_SIZE = 18 * mm
HEADER_RULE_Y = PAGE_HEIGHT - 34 * mm
FOOTER_RULE_Y = 16 * mm


@dataclass
class PDFDocumentContext:
    """Context passed to story builders and available during page chrome draw."""

    branding: dict[str, Any]
    document_type: str
    document_meta: dict[str, Any] = field(default_factory=dict)
    title: str = ""
    subtitle: str = ""
    printed_at: datetime | None = None
    content_width: float = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

    @property
    def primary(self) -> colors.Color:
        return colors.HexColor(self.branding["primary_color"])

    @property
    def secondary(self) -> colors.Color:
        return colors.HexColor(self.branding["secondary_color"])

    @property
    def accent(self) -> colors.Color:
        return colors.HexColor(self.branding["accent_color"])


def _resolve_print_datetime(tenant_tz: str | None) -> datetime:
    now = timezone.now()
    if tenant_tz:
        try:
            return now.astimezone(ZoneInfo(tenant_tz))
        except Exception:
            pass
    return timezone.localtime(now) if timezone.is_aware(now) else now


def encode_document_qr_payload(
    *,
    branding: dict[str, Any],
    document_type: str,
    document_meta: dict[str, Any] | None = None,
    printed_at: datetime | None = None,
) -> str:
    """
    Compact JSON payload for the header QR code.

    Callers put document-specific keys in *document_meta*
    (e.g. student admission no., result term, letter ref).
    """
    payload = {
        "v": 1,
        "type": document_type or "document",
        "school": branding.get("school_code") or branding.get("school_name"),
        "school_id": branding.get("school_id"),
        "issued_at": (printed_at or timezone.now()).isoformat(),
    }
    if document_meta:
        # Keep QR compact — string values only, shallow.
        for key, value in document_meta.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                payload[str(key)[:40]] = value
            else:
                payload[str(key)[:40]] = str(value)[:120]
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _make_qr_image(data: str, box_size: int = 4):
    """Return a PIL Image for the QR payload (or None on failure)."""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=box_size,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").convert("RGB")
    except Exception:
        return None


def _draw_logo_or_placeholder(c: canvas.Canvas, branding: dict[str, Any], x: float, y: float, size: float) -> None:
    """Draw school logo (left) or a monogram placeholder."""
    path = branding.get("logo_path")
    primary = branding.get("primary_color") or "#0F766E"
    if path:
        try:
            c.drawImage(
                ImageReader(path),
                x,
                y,
                width=size,
                height=size,
                preserveAspectRatio=True,
                mask="auto",
            )
            return
        except Exception:
            pass

    # Placeholder monogram
    c.setFillColor(colors.HexColor(primary))
    c.roundRect(x, y, size, size, 3, fill=1, stroke=0)
    c.setFillColor(colors.white)
    name = branding.get("school_name") or "S"
    initials = "".join(part[0] for part in name.split()[:2] if part).upper() or "S"
    c.setFont("Helvetica-Bold", max(8, size * 0.32))
    c.drawCentredString(x + size / 2, y + size / 2 - 3, initials[:3])


def _draw_header(c: canvas.Canvas, ctx: PDFDocumentContext) -> None:
    branding = ctx.branding
    primary_hex = branding["primary_color"]
    primary = colors.HexColor(primary_hex)

    # White page already; draw chrome only.
    left = LEFT_MARGIN
    right = PAGE_WIDTH - RIGHT_MARGIN
    usable = right - left

    logo_x = left
    logo_y = PAGE_HEIGHT - HEADER_TOP_PAD - LOGO_SIZE
    _draw_logo_or_placeholder(c, branding, logo_x, logo_y, LOGO_SIZE)

    # QR on the right
    qr_x = right - QR_SIZE
    qr_y = logo_y
    qr_payload = encode_document_qr_payload(
        branding=branding,
        document_type=ctx.document_type,
        document_meta=ctx.document_meta,
        printed_at=ctx.printed_at,
    )
    qr_img = _make_qr_image(qr_payload)
    if qr_img is not None:
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), qr_x, qr_y, width=QR_SIZE, height=QR_SIZE, mask="auto")
    else:
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.rect(qr_x, qr_y, QR_SIZE, QR_SIZE, stroke=1, fill=0)
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawCentredString(qr_x + QR_SIZE / 2, qr_y + QR_SIZE / 2 - 2, "QR")

    # Center professional info (between logo and QR)
    mid_left = left + LOGO_SIZE + 4 * mm
    mid_right = qr_x - 4 * mm
    mid_width = max(40, mid_right - mid_left)
    center_x = mid_left + mid_width / 2
    text_top = PAGE_HEIGHT - HEADER_TOP_PAD - 2 * mm

    c.setFillColor(primary)
    c.setFont("Helvetica-Bold", 13)
    school_name = (branding.get("school_name") or "School")[:80]
    c.drawCentredString(center_x, text_top - 10, school_name)

    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 8)
    y = text_top - 22
    location = branding.get("location_line") or ""
    if location:
        c.drawCentredString(center_x, y, location[:110])
        y -= 11
    contact = branding.get("contact_line") or ""
    if contact:
        c.drawCentredString(center_x, y, contact[:110])
        y -= 11
    code = branding.get("school_code") or ""
    if code:
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(center_x, y, f"School code: {code}")

    # Header underline (school primary colour)
    c.setStrokeColor(primary)
    c.setLineWidth(1.6)
    c.line(left, HEADER_RULE_Y, right, HEADER_RULE_Y)
    # Thin secondary accent line under primary rule
    c.setStrokeColor(colors.HexColor(branding["secondary_color"]))
    c.setLineWidth(0.6)
    c.line(left, HEADER_RULE_Y - 2.2, right, HEADER_RULE_Y - 2.2)


def _draw_footer(c: canvas.Canvas, ctx: PDFDocumentContext, page_number: int, page_count: int | None = None) -> None:
    branding = ctx.branding
    primary = colors.HexColor(branding["primary_color"])
    left = LEFT_MARGIN
    right = PAGE_WIDTH - RIGHT_MARGIN

    # Footer underline
    c.setStrokeColor(primary)
    c.setLineWidth(1.2)
    c.line(left, FOOTER_RULE_Y + 10 * mm, right, FOOTER_RULE_Y + 10 * mm)
    c.setStrokeColor(colors.HexColor(branding["secondary_color"]))
    c.setLineWidth(0.5)
    c.line(left, FOOTER_RULE_Y + 10 * mm - 2, right, FOOTER_RULE_Y + 10 * mm - 2)

    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Oblique", 7.5)
    motto = branding.get("motto") or branding.get("tagline") or ""
    footer_y = FOOTER_RULE_Y + 5.5 * mm
    if motto:
        c.drawString(left, footer_y, f"“{motto[:90]}”")

    # Contact snippets under the rule
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    contact_bits = []
    if branding.get("email"):
        contact_bits.append(branding["email"])
    if branding.get("phone"):
        contact_bits.append(branding["phone"])
    contact_text = "  ·  ".join(contact_bits)
    if contact_text:
        c.drawString(left, FOOTER_RULE_Y + 2.2 * mm, contact_text[:95])

    # Print date/time + page on the right
    printed = ctx.printed_at or timezone.now()
    stamp = printed.strftime("%Y-%m-%d %H:%M")
    if getattr(printed, "tzinfo", None):
        try:
            stamp = printed.strftime("%Y-%m-%d %H:%M %Z").strip()
        except Exception:
            pass
    page_label = f"Page {page_number}"
    if page_count:
        page_label = f"Page {page_number} of {page_count}"
    right_text = f"Printed: {stamp}   {page_label}"
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawRightString(right, FOOTER_RULE_Y + 2.2 * mm, right_text)


def get_pdf_styles(ctx: PDFDocumentContext) -> dict[str, ParagraphStyle]:
    """Standard paragraph styles tinted with the school primary colour."""
    base = getSampleStyleSheet()
    primary = ctx.branding["primary_color"]
    styles = {
        "Title": ParagraphStyle(
            "ApexDocTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor(primary),
            spaceAfter=8,
            alignment=1,  # center
        ),
        "Subtitle": ParagraphStyle(
            "ApexDocSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
            alignment=1,
        ),
        "Heading": ParagraphStyle(
            "ApexDocHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(primary),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "ApexDocBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        ),
        "Meta": ParagraphStyle(
            "ApexDocMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        ),
        "Small": ParagraphStyle(
            "ApexDocSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#334155"),
        ),
        "Label": ParagraphStyle(
            "ApexDocLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        ),
    }
    return styles


def p(text: Any, style: ParagraphStyle) -> Paragraph:
    """Safe Paragraph helper (escapes ReportLab markup)."""
    return Paragraph(escape_pdf_text(text), style)


def branded_table_style(ctx: PDFDocumentContext, *, header: bool = True) -> TableStyle:
    """Common table chrome using school colours."""
    primary = ctx.branding["primary_color"]
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(primary)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ])
    return TableStyle(commands)


StoryBuilder = Callable[[PDFDocumentContext, dict[str, ParagraphStyle]], Sequence[Flowable]]


def build_branded_pdf(
    *,
    tenant,
    document_type: str,
    build_story: StoryBuilder,
    document_meta: dict[str, Any] | None = None,
    title: str = "",
    subtitle: str = "",
    request=None,
) -> bytes:
    """
    Build a complete A4 branded PDF.

    *build_story(ctx, styles)* must return a sequence of ReportLab flowables
    for the document body only (header/footer are drawn automatically).
    """
    branding = build_tenant_branding(tenant, request=request)
    printed_at = _resolve_print_datetime(branding.get("timezone"))
    ctx = PDFDocumentContext(
        branding=branding,
        document_type=document_type,
        document_meta=dict(document_meta or {}),
        title=title,
        subtitle=subtitle,
        printed_at=printed_at,
    )
    styles = get_pdf_styles(ctx)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=title or f"{branding.get('school_name')} — {document_type}",
        author=branding.get("school_name") or "Apex Hub",
    )

    story: list[Flowable] = []
    if title:
        story.append(p(title, styles["Title"]))
    if subtitle:
        story.append(p(subtitle, styles["Subtitle"]))

    body = list(build_story(ctx, styles) or [])
    story.extend(body)

    page_state: dict[str, int] = {"count": 0}

    def _on_page(canv: canvas.Canvas, doc_):
        canv.saveState()
        # Ensure white page background
        canv.setFillColor(colors.white)
        canv.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        page_state["count"] = doc_.page
        _draw_header(canv, ctx)
        _draw_footer(canv, ctx, page_number=doc_.page)
        canv.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("PDF generation produced an invalid document.")
    return pdf_bytes


def sample_preview_story(ctx: PDFDocumentContext, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """
    Demo body used by the school-admin PDF template preview.
    Shows how real documents will sit between header and footer.
    """
    story: list[Flowable] = []
    story.append(p(
        "This is a live preview of your school’s branded PDF template. "
        "Colours, logo, contact details, motto, and QR chrome match School Settings.",
        styles["Body"],
    ))
    story.append(Spacer(1, 6))
    story.append(p("Document sample section", styles["Heading"]))
    story.append(p(
        "Place report cards, admission letters, fee statements, or any other school "
        "document content in this middle region. Header and footer are applied on every page.",
        styles["Body"],
    ))
    story.append(Spacer(1, 8))

    rows = [
        [p("Field", styles["Label"]), p("Sample value", styles["Label"])],
        [p("Learner", styles["Body"]), p("Jane A. Doe", styles["Body"])],
        [p("Admission No.", styles["Body"]), p("ADM-2026-001", styles["Body"])],
        [p("Class / Stream", styles["Body"]), p("Grade 7 · East", styles["Body"])],
        [p("Document type", styles["Body"]), p(ctx.document_type.replace("_", " ").title(), styles["Body"])],
        [p("Primary colour", styles["Body"]), p(ctx.branding["primary_color"], styles["Body"])],
        [p("Secondary colour", styles["Body"]), p(ctx.branding["secondary_color"], styles["Body"])],
    ]
    table = Table(rows, colWidths=[ctx.content_width * 0.35, ctx.content_width * 0.65])
    table.setStyle(branded_table_style(ctx, header=True))
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(p(
        "QR code (top-right) encodes document type, school identity, and reference metadata "
        "so recipients can verify the document later.",
        styles["Meta"],
    ))
    return story


def build_pdf_template_preview(*, tenant, request=None) -> bytes:
    """School-admin settings preview PDF."""
    return build_branded_pdf(
        tenant=tenant,
        document_type="template_preview",
        document_meta={
            "purpose": "settings_preview",
            "label": "PDF template preview",
        },
        title="PDF Template Preview",
        subtitle="School branded document layout — A4 portrait",
        build_story=sample_preview_story,
        request=request,
    )
