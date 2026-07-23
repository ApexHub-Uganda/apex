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
from reportlab.lib.pagesizes import A4, landscape as rl_landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
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

# Margins: full header band on page 1 only; later pages keep a slim top inset + footer.
LEFT_MARGIN = 16 * mm
RIGHT_MARGIN = 16 * mm
TOP_MARGIN = 38 * mm  # first page (logo + school block + rules)
TOP_MARGIN_LATER = 14 * mm  # subsequent pages — footer only chrome
BOTTOM_MARGIN = 22 * mm

HEADER_TOP_PAD = 10 * mm
LOGO_SIZE = 18 * mm
# Slightly larger than the logo so the verification code is obvious on printouts.
QR_SIZE = 20 * mm
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
    page_width: float = PAGE_WIDTH
    page_height: float = PAGE_HEIGHT
    orientation: str = "portrait"

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
    Compact professional JSON for the header QR.

    Default envelope is minimal (school code only). Callers add a short set of
    fields via *document_meta* — e.g. document name, status, term, class.
    Long IDs, timestamps, and audit fields do not belong in a print QR.
    """
    school = (branding.get("school_code") or branding.get("school_name") or "").strip()
    payload: dict[str, Any] = {}
    if school:
        payload["school"] = school[:40]

    # Preferred short keys from meta (order preserved for stable scanning UX)
    preferred = ("name", "document", "status", "term", "class", "classes", "student", "ref")
    meta = dict(document_meta or {})

    def _put(key: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, bool):
            text = "yes" if value else "no"
        elif isinstance(value, (int, float)):
            text = str(value)
        else:
            text = str(value).strip()
        if not text or text.lower() in ("none", "null", "—", "-"):
            return
        payload[str(key)[:24]] = text[:80]

    for key in preferred:
        if key in meta:
            _put(key, meta.pop(key))

    # "name" is the document title; fall back to a clean document_type label
    if "name" not in payload and "document" not in payload:
        label = (document_type or "document").replace("_", " ").strip()
        if label:
            _put("name", label.title()[:80])

    # Any remaining short meta (callers may pass a few extras deliberately)
    for key, value in meta.items():
        if str(key).startswith("_"):
            continue
        # Skip heavy/audit keys that bloat QR codes
        if str(key).lower() in {
            "v", "school_id", "schedule_id", "issued_at", "created_at", "published_at",
            "created_by", "published_by", "lessons", "slots", "class_count", "kind",
            "doc", "scope", "scope_label", "date_from", "date_to", "session",
        }:
            continue
        _put(str(key), value)

    # printed_at intentionally omitted — keep QR short and professional
    _ = printed_at
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _make_qr_image(data: str, box_size: int = 4):
    """Return a PIL Image for the QR payload (or None on failure)."""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M

        # Prefer M for denser recovery; fall back to L if payload is large.
        for level in (ERROR_CORRECT_M, ERROR_CORRECT_L):
            try:
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=level,
                    box_size=box_size,
                    border=1,
                )
                qr.add_data(data)
                qr.make(fit=True)
                return qr.make_image(fill_color="black", back_color="white").convert("RGB")
            except Exception:
                continue
        return None
    except Exception:
        return None


def _qr_matrix(data: str):
    """
    Build a QR boolean matrix for the payload.

    Prefer the optional qrcode package; returns None if unavailable.
    """
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M

        for level in (ERROR_CORRECT_M, ERROR_CORRECT_L):
            try:
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=level,
                    box_size=1,
                    border=1,
                )
                qr.add_data(data)
                qr.make(fit=True)
                return qr.get_matrix()
            except Exception:
                continue
    except Exception:
        return None
    return None


def _draw_qr_pad(c: canvas.Canvas, x: float, y: float, size: float) -> None:
    """White plate + border behind the QR so modules stay legible on any header."""
    pad = 1.5
    c.setFillColor(colors.white)
    c.roundRect(x - pad, y - pad, size + 2 * pad, size + 2 * pad, 1.5, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.6)
    c.roundRect(x - pad, y - pad, size + 2 * pad, size + 2 * pad, 1.5, fill=0, stroke=1)


def _draw_qr_reportlab_native(c: canvas.Canvas, data: str, x: float, y: float, size: float) -> bool:
    """
    Draw QR using ReportLab's built-in barcode QR (no third-party qrcode package).

    This is the primary path — works in every env that already has reportlab.
    """
    try:
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderPDF

        widget = QrCodeWidget(data)
        bounds = widget.getBounds()
        bw = float(bounds[2] - bounds[0]) or 1.0
        bh = float(bounds[3] - bounds[1]) or 1.0
        # Scale widget into a Drawing of exactly *size* × *size*
        drawing = Drawing(size, size, transform=[size / bw, 0, 0, size / bh, 0, 0])
        drawing.add(widget)
        _draw_qr_pad(c, x, y, size)
        renderPDF.draw(drawing, c, x, y)
        return True
    except Exception:
        return False


def _draw_qr_matrix_modules(c: canvas.Canvas, matrix, x: float, y: float, size: float) -> bool:
    """Paint a boolean QR matrix as black vector modules."""
    if not matrix:
        return False
    n = len(matrix)
    if n <= 0:
        return False
    _draw_qr_pad(c, x, y, size)
    module = size / float(n)
    cell = module + 0.08
    c.setFillColor(colors.black)
    for row_i, row in enumerate(matrix):
        py = y + (n - 1 - row_i) * module
        for col_i, dark in enumerate(row):
            if dark:
                c.rect(x + col_i * module, py, cell, cell, fill=1, stroke=0)
    return True


def _draw_qr_image_fallback(c: canvas.Canvas, data: str, x: float, y: float, size: float) -> bool:
    """PNG path via optional qrcode package (no mask — viewers hide masked B&W)."""
    qr_img = _make_qr_image(data)
    if qr_img is None:
        return False
    try:
        buf = io.BytesIO()
        qr_img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        _draw_qr_pad(c, x, y, size)
        c.drawImage(
            ImageReader(buf),
            x,
            y,
            width=size,
            height=size,
            preserveAspectRatio=True,
            mask=None,
        )
        return True
    except Exception:
        return False


def _draw_qr_code(c: canvas.Canvas, data: str, x: float, y: float, size: float) -> bool:
    """
    Draw a scannable QR at (x, y) bottom-left, *size* points square.

    Priority:
      1) ReportLab built-in QrCodeWidget (always available with reportlab)
      2) Optional qrcode package matrix
      3) Optional qrcode PNG image
      4) Visible hollow placeholder (last resort)
    """
    if _draw_qr_reportlab_native(c, data, x, y, size):
        return True
    if _draw_qr_matrix_modules(c, _qr_matrix(data), x, y, size):
        return True
    if _draw_qr_image_fallback(c, data, x, y, size):
        return True

    # Last-resort placeholder — still visible so chrome never looks "empty"
    _draw_qr_pad(c, x, y, size)
    c.setStrokeColor(colors.HexColor("#64748B"))
    c.setLineWidth(0.9)
    c.rect(x, y, size, size, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawCentredString(x + size / 2, y + size / 2 - 2, "QR")
    return False


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
    page_w = getattr(ctx, "page_width", PAGE_WIDTH) or PAGE_WIDTH
    page_h = getattr(ctx, "page_height", PAGE_HEIGHT) or PAGE_HEIGHT
    header_rule_y = page_h - 34 * mm

    # White page already; draw chrome only.
    left = LEFT_MARGIN
    right = page_w - RIGHT_MARGIN
    usable = right - left

    logo_x = left
    logo_y = page_h - HEADER_TOP_PAD - LOGO_SIZE
    _draw_logo_or_placeholder(c, branding, logo_x, logo_y, LOGO_SIZE)

    # QR on the right — ReportLab-native first (works without optional qrcode package)
    # Align QR bottom with logo bottom so both sit in the header band.
    qr_x = right - QR_SIZE
    qr_y = page_h - HEADER_TOP_PAD - QR_SIZE
    qr_payload = encode_document_qr_payload(
        branding=branding,
        document_type=ctx.document_type,
        document_meta=ctx.document_meta,
        printed_at=ctx.printed_at,
    )
    _draw_qr_code(c, qr_payload, qr_x, qr_y, QR_SIZE)

    # Center professional info (between logo and QR)
    mid_left = left + LOGO_SIZE + 4 * mm
    mid_right = qr_x - 4 * mm
    mid_width = max(40, mid_right - mid_left)
    center_x = mid_left + mid_width / 2
    text_top = page_h - HEADER_TOP_PAD - 2 * mm

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
    c.line(left, header_rule_y, right, header_rule_y)
    # Thin secondary accent line under primary rule
    c.setStrokeColor(colors.HexColor(branding["secondary_color"]))
    c.setLineWidth(0.6)
    c.line(left, header_rule_y - 2.2, right, header_rule_y - 2.2)


def _draw_footer(c: canvas.Canvas, ctx: PDFDocumentContext, page_number: int, page_count: int | None = None) -> None:
    branding = ctx.branding
    primary = colors.HexColor(branding["primary_color"])
    page_w = getattr(ctx, "page_width", PAGE_WIDTH) or PAGE_WIDTH
    left = LEFT_MARGIN
    right = page_w - RIGHT_MARGIN

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


def branded_table_style(
    ctx: PDFDocumentContext,
    *,
    header: bool = True,
    header_fill: str | None = None,
) -> TableStyle:
    """Common table chrome using school colours.

    *header_fill*:
      - None / \"brand\" — tenant primary background with white text (default)
      - \"white\" / \"light\" — white header row with dark text (better contrast on
        report cards, broadsheets, and certificates)
    """
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
        fill = (header_fill or "brand").strip().lower()
        if fill in {"white", "light", "plain"}:
            commands.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.white),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor(primary)),
            ])
        else:
            commands.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(primary)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ])
    return TableStyle(commands)


StoryBuilder = Callable[[PDFDocumentContext, dict[str, ParagraphStyle]], Sequence[Flowable]]


def _paint_page_background(canv: canvas.Canvas, page_w: float, page_h: float) -> None:
    canv.setFillColor(colors.white)
    canv.rect(0, 0, page_w, page_h, fill=1, stroke=0)


def build_branded_pdf(
    *,
    tenant,
    document_type: str,
    build_story: StoryBuilder,
    document_meta: dict[str, Any] | None = None,
    title: str = "",
    subtitle: str = "",
    request=None,
    orientation: str = "portrait",
) -> bytes:
    """
    Build a complete A4 branded PDF (portrait by default; landscape supported).

    *build_story(ctx, styles)* must return a sequence of ReportLab flowables
    for the document body only.

    Chrome rules:
      - **Page 1**: school header (logo, identity, QR) + footer
      - **Page 2+**: footer only (no repeating header) with a tighter top margin
    """
    orientation = (orientation or "portrait").lower()
    if orientation not in ("portrait", "landscape"):
        orientation = "portrait"
    pagesize = rl_landscape(A4) if orientation == "landscape" else A4
    page_w, page_h = pagesize

    branding = build_tenant_branding(tenant, request=request)
    printed_at = _resolve_print_datetime(branding.get("timezone"))
    ctx = PDFDocumentContext(
        branding=branding,
        document_type=document_type,
        document_meta=dict(document_meta or {}),
        title=title,
        subtitle=subtitle,
        printed_at=printed_at,
        content_width=page_w - LEFT_MARGIN - RIGHT_MARGIN,
        page_width=page_w,
        page_height=page_h,
        orientation=orientation,
    )
    styles = get_pdf_styles(ctx)

    buffer = io.BytesIO()
    frame_w = page_w - LEFT_MARGIN - RIGHT_MARGIN
    frame_h_first = page_h - TOP_MARGIN - BOTTOM_MARGIN
    frame_h_later = page_h - TOP_MARGIN_LATER - BOTTOM_MARGIN

    frame_first = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        frame_w,
        frame_h_first,
        id="first",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    frame_later = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        frame_w,
        frame_h_later,
        id="later",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    def _on_first(canv: canvas.Canvas, doc_):
        canv.saveState()
        _paint_page_background(canv, page_w, page_h)
        _draw_header(canv, ctx)
        _draw_footer(canv, ctx, page_number=doc_.page)
        canv.restoreState()

    def _on_later(canv: canvas.Canvas, doc_):
        canv.saveState()
        _paint_page_background(canv, page_w, page_h)
        # Header intentionally omitted — footer only on continuation pages
        _draw_footer(canv, ctx, page_number=doc_.page)
        canv.restoreState()

    doc = BaseDocTemplate(
        buffer,
        pagesize=pagesize,
        title=title or f"{branding.get('school_name')} — {document_type}",
        author=branding.get("school_name") or "Apex Hub",
    )
    doc.addPageTemplates([
        PageTemplate(id="First", frames=[frame_first], onPage=_on_first),
        PageTemplate(id="Later", frames=[frame_later], onPage=_on_later),
    ])

    story: list[Flowable] = [NextPageTemplate("Later")]
    if title:
        story.append(p(title, styles["Title"]))
    if subtitle:
        story.append(p(subtitle, styles["Subtitle"]))

    body = list(build_story(ctx, styles) or [])
    story.extend(body)

    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("PDF generation produced an invalid document.")
    return pdf_bytes


def build_headed_paper_pdf(
    *,
    tenant,
    page_count: int = 1,
    request=None,
) -> bytes:
    """
    Blank professional letterhead sheets for school staff.

    - Page 1: full branded header + footer
    - Pages 2…N: footer only (no header) — ready for handwriting or printing
    """
    try:
        pages = int(page_count)
    except (TypeError, ValueError):
        pages = 1
    pages = max(1, min(pages, 50))

    branding = build_tenant_branding(tenant, request=request)
    printed_at = _resolve_print_datetime(branding.get("timezone"))
    ctx = PDFDocumentContext(
        branding=branding,
        document_type="headed_paper",
        document_meta={
            "name": "Headed paper",
            "pages": pages,
        },
        title="Headed paper",
        subtitle="",
        printed_at=printed_at,
        content_width=PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
        orientation="portrait",
    )

    buffer = io.BytesIO()
    canv = canvas.Canvas(buffer, pagesize=A4)
    canv.setTitle(f"{branding.get('school_name') or 'School'} — Headed paper")
    canv.setAuthor(branding.get("school_name") or "Apex Hub")

    for page_no in range(1, pages + 1):
        _paint_page_background(canv, PAGE_WIDTH, PAGE_HEIGHT)
        if page_no == 1:
            _draw_header(canv, ctx)
            # Subtle guide for writable area under the header rule
            canv.setStrokeColor(colors.HexColor("#E2E8F0"))
            canv.setDash(1, 3)
            canv.setLineWidth(0.4)
            guide_top = HEADER_RULE_Y - 8 * mm
            guide_bottom = FOOTER_RULE_Y + 14 * mm
            # light horizontal writing guides (professional notepad feel, not busy)
            y = guide_top
            step = 8 * mm
            while y > guide_bottom:
                canv.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
                y -= step
            canv.setDash()
        else:
            # Continuation pages: clean writable field, footer chrome only
            canv.setStrokeColor(colors.HexColor("#F1F5F9"))
            canv.setDash(1, 4)
            canv.setLineWidth(0.35)
            y = PAGE_HEIGHT - TOP_MARGIN_LATER - 4 * mm
            guide_bottom = FOOTER_RULE_Y + 14 * mm
            step = 8 * mm
            while y > guide_bottom:
                canv.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
                y -= step
            canv.setDash()

        _draw_footer(canv, ctx, page_number=page_no, page_count=pages)
        canv.showPage()

    canv.save()
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Headed paper PDF generation produced an invalid document.")
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
        "document content in this middle region. The full school header appears on page 1 only; "
        "continuation pages keep the footer (motto, contacts, page number) without repeating the header.",
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
