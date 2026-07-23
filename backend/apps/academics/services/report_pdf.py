"""Branded PDF for individual report cards and class broadsheets."""
from __future__ import annotations

from reportlab.platypus import Spacer, Table

from apps.core.pdf_template import branded_table_style, build_branded_pdf, p


def build_report_card_pdf(*, tenant, report_card, request=None) -> bytes:
    student = report_card.student
    term = report_card.term
    lines = list(report_card.subject_lines.filter(is_deleted=False).order_by("sort_order"))

    def story(ctx, styles):
        header_bits = [
            p(f"{student.full_name} · {student.admission_number}", styles["Heading"]),
            p(
                f"{report_card.school_class.name}"
                + (f" · {report_card.stream.name}" if report_card.stream_id else "")
                + f" · {term.name}"
                + (f" · {term.academic_year.name}" if term.academic_year_id else ""),
                styles["Meta"],
            ),
            Spacer(1, 6),
        ]
        rows = [[
            p("Subject", styles["Label"]),
            p("C.A.", styles["Label"]),
            p("Exam", styles["Label"]),
            p("Total", styles["Label"]),
            p("Grade", styles["Label"]),
            p("Remark", styles["Label"]),
        ]]
        for line in lines:
            rows.append([
                p(line.subject_name, styles["Small"]),
                p(str(line.ca_score) if line.ca_score is not None else "—", styles["Small"]),
                p(str(line.exam_score) if line.exam_score is not None else "—", styles["Small"]),
                p(str(line.total_score), styles["Small"]),
                p(line.grade or "—", styles["Small"]),
                p(line.remarks or "—", styles["Small"]),
            ])
        w = ctx.content_width
        table = Table(rows, colWidths=[w * 0.28, w * 0.12, w * 0.12, w * 0.12, w * 0.12, w * 0.24])
        table.setStyle(branded_table_style(ctx, header=True, header_fill="white"))
        header_bits.append(table)
        header_bits.append(Spacer(1, 10))
        header_bits.append(p(
            f"Average: {report_card.average_score} · Class rank: {report_card.rank or '—'}"
            f"/{report_card.class_size or '—'} · Stream rank: {report_card.stream_rank or '—'}"
            f"/{report_card.stream_size or '—'}",
            styles["Body"],
        ))
        header_bits.append(p(
            f"Attendance — Present: {report_card.days_present} · Absent: {report_card.days_absent} "
            f"· Late: {report_card.days_late} · Excused: {report_card.days_excused}",
            styles["Meta"],
        ))
        if report_card.next_term_opens:
            header_bits.append(p(f"Next term opens: {report_card.next_term_opens}", styles["Meta"]))
        header_bits.append(Spacer(1, 12))
        header_bits.append(p(f"Class teacher: {report_card.teacher_remarks or '________________'}", styles["Body"]))
        header_bits.append(p(f"Director of Studies: {report_card.dos_remarks or '________________'}", styles["Body"]))
        header_bits.append(p(f"Head Teacher: {report_card.principal_remarks or '________________'}", styles["Body"]))
        header_bits.append(Spacer(1, 8))
        header_bits.append(p("Signatures: Class teacher ________  DoS ________  Head Teacher ________", styles["Meta"]))
        return header_bits

    return build_branded_pdf(
        tenant=tenant,
        document_type="report_card",
        document_meta={
            "student": student.admission_number,
            "term": term.name,
            "version": report_card.version,
        },
        title="Term Report Card",
        subtitle=f"{student.full_name} — {term.name}",
        build_story=story,
        request=request,
    )


def build_class_broadsheet_pdf(*, tenant, term, school_class, report_cards, stream=None, request=None) -> bytes:
    cards = list(report_cards)

    def story(ctx, styles):
        title = f"{school_class.name}"
        if stream:
            title += f" · {stream.name}"
        body = [
            p(f"Broadsheet — {title} — {term.name}", styles["Heading"]),
            Spacer(1, 6),
        ]
        # collect subject columns from first card
        subjects = []
        if cards:
            subjects = [
                (line.subject_code or line.subject_name[:8], line.subject_name)
                for line in cards[0].subject_lines.filter(is_deleted=False).order_by("sort_order")[:8]
            ]
        header = [p("Student", styles["Label"]), p("Adm", styles["Label"])]
        for code, _ in subjects:
            header.append(p(code, styles["Label"]))
        header.extend([p("Avg", styles["Label"]), p("Rank", styles["Label"])])
        rows = [header]
        for rc in cards:
            line_map = {
                (l.subject_code or l.subject_name[:8]): l
                for l in rc.subject_lines.filter(is_deleted=False)
            }
            row = [
                p(rc.student.full_name if rc.student_id else "—", styles["Small"]),
                p(rc.student.admission_number if rc.student_id else "—", styles["Small"]),
            ]
            for code, _ in subjects:
                ln = line_map.get(code)
                row.append(p(str(ln.total_score) if ln else "—", styles["Small"]))
            row.append(p(str(rc.average_score), styles["Small"]))
            row.append(p(str(rc.rank or "—"), styles["Small"]))
            rows.append(row)
        n = max(len(header), 1)
        col_w = ctx.content_width / n
        table = Table(rows, colWidths=[col_w] * n)
        table.setStyle(branded_table_style(ctx, header=True, header_fill="white"))
        body.append(table)
        return body

    return build_branded_pdf(
        tenant=tenant,
        document_type="class_broadsheet",
        document_meta={"class": school_class.code, "term": term.name},
        title="Class Broadsheet",
        subtitle=f"{school_class.name} — {term.name}",
        build_story=story,
        request=request,
    )
