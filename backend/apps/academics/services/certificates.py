"""Transfer / leaving certificates and multi-year academic transcripts (branded PDF)."""
from __future__ import annotations

from reportlab.platypus import Spacer, Table

from apps.academics.models import StudentAcademicPlacement
from apps.core.pdf_template import branded_table_style, build_branded_pdf, p
from apps.examinations.models import ReportCard
from apps.students.models import Student


def build_leaving_certificate_pdf(*, tenant, student: Student, reason: str = "", request=None) -> bytes:
    def story(ctx, styles):
        bits = [
            p("TO WHOM IT MAY CONCERN", styles["Heading"]),
            Spacer(1, 8),
            p(
                f"This is to certify that {student.full_name} "
                f"(Admission No. {student.admission_number})"
                + (f", Registration/Index No. {student.registration_number}" if student.registration_number else "")
                + f", nationality {student.nationality or 'Ugandan'}, "
                f"was a student of this school.",
                styles["Body"],
            ),
            Spacer(1, 6),
        ]
        if student.school_class_id:
            bits.append(p(
                f"Last class/stream: {student.school_class.name}"
                + (f" / {student.stream.name}" if student.stream_id else "")
                + f". Status: {student.status}.",
                styles["Body"],
            ))
        placements = StudentAcademicPlacement.objects.filter(
            tenant=tenant, student=student, is_deleted=False,
        ).select_related("academic_year", "school_class", "stream").order_by("academic_year__start_date")[:20]
        if placements:
            bits.append(Spacer(1, 8))
            bits.append(p("Academic placement history", styles["Label"]))
            rows = [[p("Year", styles["Label"]), p("Class", styles["Label"]), p("Stream", styles["Label"]), p("Status", styles["Label"])]]
            for pl in placements:
                rows.append([
                    p(pl.academic_year.name if pl.academic_year_id else "—", styles["Small"]),
                    p(pl.school_class.name if pl.school_class_id else "—", styles["Small"]),
                    p(pl.stream.name if pl.stream_id else "—", styles["Small"]),
                    p(pl.status, styles["Small"]),
                ])
            w = ctx.content_width
            t = Table(rows, colWidths=[w * 0.25, w * 0.3, w * 0.2, w * 0.25])
            t.setStyle(branded_table_style(ctx, header=True))
            bits.append(t)
        if reason:
            bits.append(Spacer(1, 8))
            bits.append(p(f"Reason for leaving: {reason}", styles["Body"]))
        bits.append(Spacer(1, 16))
        bits.append(p("________________________          ________________________", styles["Meta"]))
        bits.append(p("Head Teacher                                          Director of Studies", styles["Meta"]))
        bits.append(Spacer(1, 6))
        bits.append(p("School stamp / official seal", styles["Meta"]))
        return bits

    return build_branded_pdf(
        tenant=tenant,
        document_type="leaving_certificate",
        document_meta={"student": student.admission_number, "status": student.status},
        title="Leaving / Transfer Certificate",
        subtitle=student.full_name,
        build_story=story,
        request=request,
    )


def build_academic_transcript_pdf(*, tenant, student: Student, request=None) -> bytes:
    cards = (
        ReportCard.objects.filter(tenant=tenant, student=student, is_deleted=False, is_latest=True)
        .select_related("term", "school_class", "stream", "academic_year")
        .prefetch_related("subject_lines")
        .order_by("term__start_date")
    )

    def story(ctx, styles):
        bits = [
            p(f"{student.full_name} · {student.admission_number}", styles["Heading"]),
            p(
                f"Nationality: {student.nationality or 'Ugandan'}"
                + (f" · Reg: {student.registration_number}" if student.registration_number else ""),
                styles["Meta"],
            ),
            Spacer(1, 8),
        ]
        for rc in cards:
            bits.append(p(
                f"{rc.term.name if rc.term_id else 'Term'}"
                + (f" · {rc.academic_year.name}" if rc.academic_year_id else "")
                + (f" · {rc.school_class.name}" if rc.school_class_id else "")
                + f" · Avg {rc.average_score} · Rank {rc.rank or '—'}",
                styles["Label"],
            ))
            rows = [[
                p("Subject", styles["Label"]),
                p("CA", styles["Label"]),
                p("Exam", styles["Label"]),
                p("Total", styles["Label"]),
                p("Grade", styles["Label"]),
            ]]
            for ln in rc.subject_lines.filter(is_deleted=False).order_by("sort_order"):
                rows.append([
                    p(ln.subject_name, styles["Small"]),
                    p(str(ln.ca_score) if ln.ca_score is not None else "—", styles["Small"]),
                    p(str(ln.exam_score) if ln.exam_score is not None else "—", styles["Small"]),
                    p(str(ln.total_score), styles["Small"]),
                    p(ln.grade or "—", styles["Small"]),
                ])
            w = ctx.content_width
            t = Table(rows, colWidths=[w * 0.36, w * 0.16, w * 0.16, w * 0.16, w * 0.16])
            t.setStyle(branded_table_style(ctx, header=True))
            bits.append(t)
            bits.append(Spacer(1, 10))
        if not cards:
            bits.append(p("No published/generated report card history available yet.", styles["Body"]))
        bits.append(Spacer(1, 12))
        bits.append(p("Certified true copy of academic record.", styles["Meta"]))
        bits.append(p("Head Teacher ________     DoS ________     Date ________", styles["Meta"]))
        return bits

    return build_branded_pdf(
        tenant=tenant,
        document_type="academic_transcript",
        document_meta={"student": student.admission_number},
        title="Academic Transcript",
        subtitle=student.full_name,
        build_story=story,
        request=request,
    )
