"""Branded PDF for individual report cards / results and class broadsheets.

Individual printout columns:
  Code | Subject | Score | Grade | Remarks (per-subject)
  Bottom: Average mark + Overall (total) grade
  Overall teacher/DoS/head remarks are separate from subject remarks.

Broadsheet columns:
  Name | each subject (score + grade side by side; blank if missing) |
  Overall grade | Average mark
"""
from __future__ import annotations

from decimal import Decimal

from reportlab.platypus import Spacer, Table

from apps.core.pdf_template import branded_table_style, build_branded_pdf, p
from apps.examinations.grading import resolve_band
from apps.examinations.models import GradingScheme


def _fmt_score(value) -> str:
    if value is None or value == "":
        return ""
    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return str(int(d))
        return f"{d:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _overall_grade_for_card(report_card, tenant=None) -> str:
    meta = report_card.generation_meta or {}
    if meta.get("overall_grade"):
        return str(meta["overall_grade"])
    if report_card.division:
        return str(report_card.division)
    # Fallback: resolve from average using default scheme
    scheme = (
        GradingScheme.objects.filter(tenant=tenant or report_card.tenant_id, is_deleted=False, is_default=True)
        .prefetch_related("bands")
        .first()
        or GradingScheme.objects.filter(tenant=tenant or report_card.tenant_id, is_deleted=False)
        .prefetch_related("bands")
        .order_by("name")
        .first()
    )
    if scheme is None:
        return ""
    bands = list(scheme.bands.filter(is_deleted=False))
    band = resolve_band(bands, score=report_card.average_score) if bands else None
    return (band.grade if band else "") or ""


def build_report_card_pdf(*, tenant, report_card, request=None) -> bytes:
    """Individual learner report card / results printout (all subjects with scores)."""
    student = report_card.student
    term = report_card.term
    lines = list(report_card.subject_lines.filter(is_deleted=False).order_by("sort_order", "subject_code", "subject_name"))
    overall_grade = _overall_grade_for_card(report_card, tenant=tenant)
    class_label = report_card.school_class.name if report_card.school_class_id else ""
    if report_card.stream_id and report_card.stream:
        class_label = f"{class_label} · {report_card.stream.name}"
    year_label = ""
    if term and term.academic_year_id and getattr(term, "academic_year", None):
        year_label = term.academic_year.name
    term_label = term.name if term else ""

    def story(ctx, styles):
        # Title/subtitle already come from build_branded_pdf — do not repeat the document heading here.
        bits = [
            p(f"Student: {student.full_name if student else '—'}", styles["Body"]),
            p(f"Admission No: {student.admission_number if student else '—'}", styles["Body"]),
            p(f"Class: {class_label or '—'}", styles["Body"]),
            p(
                f"Term: {term_label}"
                + (f"  ·  Academic year: {year_label}" if year_label else ""),
                styles["Body"],
            ),
            Spacer(1, 8),
            p("Subject performance", styles["Label"]),
            Spacer(1, 3),
        ]

        # Code | Subject | Score | Grade | Remarks
        rows = [[
            p("Code", styles["Label"]),
            p("Subject", styles["Label"]),
            p("Score", styles["Label"]),
            p("Grade", styles["Label"]),
            p("Remarks", styles["Label"]),
        ]]
        for line in lines:
            rows.append([
                p(line.subject_code or "—", styles["Small"]),
                p(line.subject_name or "—", styles["Small"]),
                p(_fmt_score(line.total_score) if line.total_score is not None else "", styles["Small"]),
                p(line.grade or "", styles["Small"]),
                p(line.remarks or "", styles["Small"]),
            ])

        if len(rows) == 1:
            rows.append([
                p("—", styles["Small"]),
                p("No subject marks entered for this learner.", styles["Small"]),
                p("", styles["Small"]),
                p("", styles["Small"]),
                p("", styles["Small"]),
            ])

        w = ctx.content_width
        table = Table(
            rows,
            colWidths=[w * 0.12, w * 0.34, w * 0.12, w * 0.12, w * 0.30],
        )
        table.setStyle(branded_table_style(ctx, header=True, header_fill="white"))
        bits.append(table)
        bits.append(Spacer(1, 10))

        # Average mark + overall (total) grade
        summary_rows = [[
            p("Average mark", styles["Label"]),
            p("Overall grade", styles["Label"]),
            p("Class rank", styles["Label"]),
            p("Stream rank", styles["Label"]),
        ], [
            p(_fmt_score(report_card.average_score), styles["Body"]),
            p(overall_grade or "—", styles["Body"]),
            p(
                f"{report_card.rank or '—'}/{report_card.class_size or '—'}",
                styles["Body"],
            ),
            p(
                f"{report_card.stream_rank or '—'}/{report_card.stream_size or '—'}",
                styles["Body"],
            ),
        ]]
        summary = Table(summary_rows, colWidths=[w * 0.25] * 4)
        summary.setStyle(branded_table_style(ctx, header=True, header_fill="white"))
        bits.append(summary)
        bits.append(Spacer(1, 8))

        bits.append(p(
            f"Attendance — Present: {report_card.days_present} · Absent: {report_card.days_absent} "
            f"· Late: {report_card.days_late} · Excused: {report_card.days_excused}",
            styles["Meta"],
        ))
        if report_card.next_term_opens:
            bits.append(p(f"Next term opens: {report_card.next_term_opens}", styles["Meta"]))

        bits.append(Spacer(1, 12))
        bits.append(p("Overall remarks", styles["Label"]))
        bits.append(Spacer(1, 3))
        bits.append(p(
            f"Class teacher: {report_card.teacher_remarks or '________________'}",
            styles["Body"],
        ))
        bits.append(p(
            f"Director of Studies: {report_card.dos_remarks or '________________'}",
            styles["Body"],
        ))
        bits.append(p(
            f"Head Teacher: {report_card.principal_remarks or '________________'}",
            styles["Body"],
        ))
        bits.append(Spacer(1, 10))
        bits.append(p(
            "Signatures: Class teacher ________    DoS ________    Head Teacher ________",
            styles["Meta"],
        ))
        return bits

    published = bool(report_card.is_published)
    doc_title = "Student Report Card" if published else "Student Results"
    return build_branded_pdf(
        tenant=tenant,
        document_type="report_card",
        document_meta={
            "student": student.admission_number if student else "",
            "term": term_label,
            "class": class_label,
            "version": report_card.version,
            "published": published,
        },
        title=doc_title,
        subtitle=f"{student.full_name if student else ''} — {term_label}",
        build_story=story,
        request=request,
    )


def _collect_broadsheet_subjects(report_cards) -> list[dict]:
    """Union of all subject columns across the class (stable order by code/name)."""
    seen: dict[str, dict] = {}
    for rc in report_cards:
        for line in rc.subject_lines.filter(is_deleted=False).order_by("sort_order"):
            key = (line.subject_code or "").strip() or line.subject_name
            if not key:
                continue
            if key not in seen:
                seen[key] = {
                    "key": key,
                    "code": line.subject_code or key,
                    "name": line.subject_name or key,
                }
    # Sort by subject code then name for a predictable broadsheet
    return sorted(seen.values(), key=lambda s: (s["code"] or s["name"]).lower())


def build_class_broadsheet_pdf(
    *,
    tenant,
    term,
    school_class,
    report_cards,
    stream=None,
    request=None,
) -> bytes:
    """Class-wide results broadsheet: name, every subject (score + grade), overall grade, average."""
    cards = list(report_cards)
    subjects = _collect_broadsheet_subjects(cards)
    year_label = ""
    if term and getattr(term, "academic_year_id", None) and getattr(term, "academic_year", None):
        year_label = term.academic_year.name
    class_title = school_class.name
    if stream:
        class_title = f"{class_title} · {stream.name}"

    def story(ctx, styles):
        # Document title already set by build_branded_pdf — avoid repeating the heading.
        body = [
            p(
                f"Class: {class_title}"
                + (f"  ·  Term: {term.name}" if term else "")
                + (f"  ·  Year: {year_label}" if year_label else ""),
                styles["Body"],
            ),
            p(
                f"{len(cards)} learner(s) · Score and grade shown for each subject; blank cells mean no mark entered.",
                styles["Meta"],
            ),
            Spacer(1, 6),
        ]

        # Header: Name | Adm | for each subject: Code (score / grade as value cells)
        # Each subject gets one column with "score / grade"
        header = [
            p("Name", styles["Label"]),
            p("Adm #", styles["Label"]),
        ]
        for sub in subjects:
            header.append(p(sub["code"] or sub["name"][:10], styles["Label"]))
        header.extend([
            p("Overall grade", styles["Label"]),
            p("Average", styles["Label"]),
        ])
        rows = [header]

        for rc in cards:
            line_map = {}
            for ln in rc.subject_lines.filter(is_deleted=False):
                key = (ln.subject_code or "").strip() or ln.subject_name
                line_map[key] = ln
            # also index by code alone
            for ln in rc.subject_lines.filter(is_deleted=False):
                if ln.subject_code:
                    line_map.setdefault(ln.subject_code, ln)

            row = [
                p(rc.student.full_name if rc.student_id else "—", styles["Small"]),
                p(rc.student.admission_number if rc.student_id else "—", styles["Small"]),
            ]
            for sub in subjects:
                ln = line_map.get(sub["key"]) or line_map.get(sub["code"])
                if not ln or ln.total_score is None:
                    row.append(p("", styles["Small"]))  # blank when missing
                else:
                    score = _fmt_score(ln.total_score)
                    grade = (ln.grade or "").strip()
                    cell = f"{score} {grade}".strip() if grade else score
                    row.append(p(cell, styles["Small"]))
            row.append(p(_overall_grade_for_card(rc, tenant=tenant) or "", styles["Small"]))
            row.append(p(_fmt_score(rc.average_score), styles["Small"]))
            rows.append(row)

        n = max(len(header), 1)
        # Name wider; subject columns share remaining space
        name_w = min(ctx.content_width * 0.18, 90)
        adm_w = min(ctx.content_width * 0.08, 48)
        tail_w = min(ctx.content_width * 0.08, 42)
        remaining = ctx.content_width - name_w - adm_w - 2 * tail_w
        subj_n = max(len(subjects), 1)
        subj_w = remaining / subj_n if subjects else remaining
        col_widths = [name_w, adm_w] + [subj_w] * len(subjects) + [tail_w, tail_w]

        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(branded_table_style(ctx, header=True, header_fill="white"))
        body.append(table)
        body.append(Spacer(1, 8))
        body.append(p(
            "Key: each subject column shows Score and Grade (e.g. 72 A). "
            "Overall grade is derived from the average mark. Blank = no mark entered.",
            styles["Meta"],
        ))
        return body

    # Landscape for wide class lists
    return build_branded_pdf(
        tenant=tenant,
        document_type="class_broadsheet",
        document_meta={
            "class": school_class.code or school_class.name,
            "term": term.name if term else "",
            "stream": stream.name if stream else "",
            "learners": len(cards),
        },
        title="Class Results Broadsheet",
        subtitle=f"{class_title} — {term.name if term else ''}",
        build_story=story,
        request=request,
        orientation="landscape",
    )
