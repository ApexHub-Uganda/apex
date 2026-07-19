"""Branded multi-class timetable printouts (portrait / landscape)."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from apps.academics.models import Class, Period, Stream, Term, Timetable, TimetableSchedule
from apps.academics.singleton import get_active_term
from apps.academics.timetable_generator import DAY_LABELS
from apps.core.exports import escape_pdf_text
from apps.core.pdf_template import branded_table_style, build_branded_pdf, p


def _fmt_time(t) -> str:
    if t is None:
        return ""
    return t.strftime("%H:%M")


def _p_lines(*parts, style) -> Paragraph:
    """Paragraph from multiple lines (subject / teacher) without escaping <br/>."""
    safe = [escape_pdf_text(x) for x in parts if x]
    if not safe:
        return Paragraph(escape_pdf_text("—"), style)
    return Paragraph("<br/>".join(safe), style)


def _cell_parts(entry: Timetable | None, *, break_name: str = "") -> list[str]:
    """Return display lines for a cell (subject, teacher) or break label."""
    if entry is None:
        return [break_name] if break_name else []
    if entry.is_break_slot or (
        not entry.subject_id
        and not getattr(entry, "display_subject", "")
        and (entry.slot_label or break_name)
    ):
        label = (entry.slot_label or break_name or "Break").strip()
        return [label] if label else []

    # Prefer denormalized labels (saved at write time) — most reliable for print
    subj = (getattr(entry, "display_subject", None) or "").strip()
    teacher = (getattr(entry, "display_teacher", None) or "").strip()

    if not subj and entry.subject_id:
        subj_obj = entry.subject
        if subj_obj is not None:
            subj = (subj_obj.name or subj_obj.code or "").strip()
    if not teacher and entry.teacher_id and getattr(entry.teacher, "staff", None):
        staff = entry.teacher.staff
        teacher = (getattr(staff, "full_name", None) or staff.last_name or "").strip()

    lines = []
    if subj:
        lines.append(subj)
    if teacher:
        lines.append(teacher)
    return lines


def _load_entries(*, tenant, term, class_ids: list[str] | None) -> list[Timetable]:
    """
    Load all non-deleted lesson slots for the term.

    Broaden filters: match by term_id OR by schedule.term_id so draft/publish
    and historical rows still print.
    """
    from django.db.models import Q

    qs = (
        Timetable.objects.filter(
            tenant=tenant,
            is_deleted=False,
            schedule_type=TimetableSchedule.SCHEDULE_LESSON,
        )
        .filter(Q(term=term) | Q(schedule__term=term) | Q(term__isnull=True, schedule__isnull=True))
        .select_related(
            "school_class", "subject", "teacher", "teacher__staff", "period", "stream", "schedule",
        )
    )
    if class_ids:
        qs = qs.filter(school_class_id__in=class_ids)
    return list(qs)


def _index_entries(entries: list[Timetable]) -> dict[str, Any]:
    """
    Multi-key index so print survives period re-saves and stream variants:
      by_period[(class, day, period_id, stream_id)]
      by_time[(class, day, HH:MM-HH:MM, stream_id)]
      by_period_any_stream[(class, day, period_id)] -> list
    """
    by_period: dict[tuple, Timetable] = {}
    by_time: dict[tuple, Timetable] = {}
    by_period_any: dict[tuple, list[Timetable]] = defaultdict(list)

    def prefer(bucket: dict, key, entry: Timetable):
        prev = bucket.get(key)
        if prev is None:
            bucket[key] = entry
            return
        # Prefer rows that actually have a subject
        if not prev.subject_id and entry.subject_id:
            bucket[key] = entry
        elif prev.is_break_slot and not entry.is_break_slot and entry.subject_id:
            bucket[key] = entry

    for e in entries:
        if e.day_of_week is None:
            continue
        cid = str(e.school_class_id)
        day = int(e.day_of_week)
        sid = str(e.stream_id) if e.stream_id else ""
        pid = str(e.period_id) if e.period_id else ""

        if pid:
            prefer(by_period, (cid, day, pid, sid), e)
            by_period_any[(cid, day, pid)].append(e)

        st = e.start_time or (e.period.start_time if e.period_id else None)
        et = e.end_time or (e.period.end_time if e.period_id else None)
        if st and et:
            prefer(
                by_time,
                (cid, day, st.strftime("%H:%M"), et.strftime("%H:%M"), sid),
                e,
            )
            # also index without stream for fallback
            prefer(
                by_time,
                (cid, day, st.strftime("%H:%M"), et.strftime("%H:%M"), ""),
                e,
            )

    return {
        "by_period": by_period,
        "by_time": by_time,
        "by_period_any": by_period_any,
    }


def _lookup_entry(
    index: dict,
    class_id: str,
    day: int,
    period: Period,
    stream_id: str = "",
    *,
    allow_cross_stream: bool = False,
) -> Timetable | None:
    """
    Resolve the entry for a printed cell.

    Strict order (no stealing another stream's subject unless allow_cross_stream):
      1) exact period_id + stream_id
      2) exact period_id + empty stream (class-level master)
      3) same start/end times + stream_id (survives period re-create with new id)
      4) same start/end + empty stream
    Never return a different stream's subject for a multi-stream row.
    """
    cid = str(class_id)
    sid = stream_id or ""
    pid = str(period.id)
    by_period = index["by_period"]
    by_time = index["by_time"]

    hit = by_period.get((cid, day, pid, sid))
    if hit is not None:
        return hit
    if not sid:
        hit = by_period.get((cid, day, pid, ""))
        if hit is not None:
            return hit

    t0, t1 = period.start_time.strftime("%H:%M"), period.end_time.strftime("%H:%M")
    hit = by_time.get((cid, day, t0, t1, sid))
    if hit is not None:
        # Guard: entry's period times must match; prefer period_id when set
        return hit
    if not sid:
        hit = by_time.get((cid, day, t0, t1, ""))
        if hit is not None:
            return hit

    if allow_cross_stream:
        candidates = index["by_period_any"].get((cid, day, pid)) or []
        for c in candidates:
            if c.subject_id:
                return c
        return candidates[0] if candidates else None
    return None


def build_timetable_pdf(
    *,
    tenant,
    term_id: str | None = None,
    class_ids: list[str] | None = None,
    orientation: str = "landscape",
    working_days: list[int] | None = None,
    schedule_id: str | None = None,
    request=None,
    teacher_mode: str | None = None,
    teacher_id: str | None = None,
) -> bytes:
    """
    Build a branded lesson timetable PDF.

    teacher_mode:
      - None / "" / "all" — full timetable
      - "highlight" — full grid; viewer's periods highlighted
      - "mine_only" — full grid structure; only viewer's lessons shown (others blank)
    """
    mode = (teacher_mode or "").strip().lower()
    if mode in ("", "all", "none", "off"):
        mode = ""
    if mode not in ("", "highlight", "mine_only"):
        mode = ""

    # Resolve teacher for personal views (prefer explicit id, else logged-in staff teacher)
    focus_teacher_id = str(teacher_id) if teacher_id else ""
    if mode and not focus_teacher_id and request is not None:
        from apps.academics.scoping import get_teacher_for_user
        viewer = get_teacher_for_user(getattr(request, "user", None))
        if viewer is not None:
            focus_teacher_id = str(viewer.id)
    if mode and not focus_teacher_id:
        mode = ""  # cannot personalize without a teacher

    schedule = None
    if schedule_id:
        schedule = TimetableSchedule.objects.filter(
            tenant=tenant, pk=schedule_id, is_deleted=False,
        ).select_related("term", "academic_year", "created_by", "published_by").first()
        if schedule is None:
            raise ValueError("Timetable schedule not found.")
        if schedule.term_id and not term_id:
            term_id = str(schedule.term_id)

    term = (
        Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
        if term_id
        else get_active_term(tenant)
    )
    if term is None:
        raise ValueError("No academic term selected.")

    periods = list(
        Period.objects.filter(tenant=tenant, is_deleted=False).order_by("sort_order", "start_time"),
    )
    if not periods:
        raise ValueError("Define periods before printing a timetable.")

    days = working_days or [0, 1, 2, 3, 4]
    days = [d for d in days if d in DAY_LABELS]

    classes_qs = Class.objects.filter(tenant=tenant, is_deleted=False).order_by("name")
    if class_ids:
        classes_qs = classes_qs.filter(pk__in=class_ids)
    classes = list(classes_qs)
    if not classes:
        raise ValueError("No classes selected for print.")

    if schedule is not None:
        entries = list(
            Timetable.objects.filter(
                tenant=tenant, schedule=schedule, is_deleted=False,
            ).select_related(
                "school_class", "subject", "teacher", "teacher__staff", "period", "stream", "schedule",
            )
        )
        if class_ids:
            idset = {str(x) for x in class_ids}
            entries = [e for e in entries if str(e.school_class_id) in idset]
        # Only print classes that actually have rows in this schedule
        schedule_class_ids = {e.school_class_id for e in entries if e.school_class_id}
        if schedule_class_ids:
            classes = [c for c in classes if c.id in schedule_class_ids] or classes
    else:
        entries = _load_entries(tenant=tenant, term=term, class_ids=[str(c.id) for c in classes])

    # Mine only: prefer classes where this teacher has at least one lesson
    if mode == "mine_only" and focus_teacher_id:
        mine_class_ids = {
            e.school_class_id
            for e in entries
            if e.teacher_id and str(e.teacher_id) == focus_teacher_id and e.school_class_id
        }
        if mine_class_ids:
            classes = [c for c in classes if c.id in mine_class_ids] or classes

    index = _index_entries(entries)

    def _is_mine(entry: Timetable | None) -> bool:
        if not focus_teacher_id or entry is None or not entry.teacher_id:
            return False
        return str(entry.teacher_id) == focus_teacher_id

    # Periods to print: prefer only those referenced by this schedule (stable order by time)
    used_period_ids = {e.period_id for e in entries if e.period_id}
    if used_period_ids:
        periods = [p for p in periods if p.id in used_period_ids] or periods

    # Debug-friendly: how many teaching slots exist for this print
    teaching_count = sum(1 for e in entries if e.subject_id and not e.is_break_slot)

    all_class_count = Class.objects.filter(tenant=tenant, is_deleted=False).count()
    if len(classes) <= 1:
        scope_kind = "class"
        scope_label = classes[0].name if classes else "Class"
    elif len(classes) < all_class_count:
        scope_kind = "selected_classes"
        scope_label = f"{len(classes)} classes"
    else:
        scope_kind = "whole_school"
        scope_label = "Whole school"
    if teaching_count:
        scope_label = f"{scope_label} · {teaching_count} lesson slot(s)"
    if mode == "highlight":
        scope_label = f"{scope_label} · Your periods highlighted"
    elif mode == "mine_only":
        scope_label = f"{scope_label} · Your periods only"

    # Compact professional QR: school (in envelope) + name, status, term, class
    doc_name = (schedule.name if schedule else f"Timetable — {term.name}").strip()[:80]
    status = (schedule.status if schedule else "draft") or "draft"
    if len(classes) == 1:
        class_label = classes[0].name
    elif len(classes) <= 3:
        class_label = ", ".join(c.name for c in classes)
    elif scope_kind == "whole_school":
        class_label = "Whole school"
    else:
        class_label = f"{len(classes)} classes"
    qr_meta = {
        "name": doc_name,
        "status": status,
        "term": term.name,
        "class": class_label[:80],
    }

    MINE_BG = colors.HexColor("#FEF3C7")  # amber highlight for teacher's cells

    def story(ctx, styles):
        flow: list = []
        if mode == "highlight":
            flow.append(p("Highlighted cells are your teaching periods.", styles["Meta"]))
            flow.append(Spacer(1, 4))
        elif mode == "mine_only":
            flow.append(p("Showing only your teaching periods; other slots are blank.", styles["Meta"]))
            flow.append(Spacer(1, 4))

        for school_class in classes:
            cid = str(school_class.id)
            flow.append(p(f"{school_class.name} ({school_class.code})", styles["Heading"]))
            if school_class.room:
                flow.append(p(f"Room: {school_class.room}", styles["Meta"]))
            flow.append(Spacer(1, 4))

            class_streams = list(
                Stream.objects.filter(
                    tenant=tenant, school_class=school_class, is_deleted=False,
                ).order_by("name")
            )
            # Multi-stream only if this class has streams AND any saved entry uses streams
            multi = bool(class_streams) and any(
                e.stream_id and str(e.school_class_id) == cid for e in entries
            )
            # If class has streams but entries are class-level only, still print single-level
            if not multi and class_streams and any(
                str(e.school_class_id) == cid and e.subject_id for e in entries
            ):
                multi = False

            header = [p("Time", styles["Label"])]
            if multi:
                header.append(p("Stream", styles["Label"]))
            header += [p(DAY_LABELS[d][:3], styles["Label"]) for d in days]
            rows = [header]
            span_cmds = []  # ReportLab SPAN for time / break rows
            shade_rows = []  # break row indexes (1-based data rows)
            mine_cells: list[tuple[int, int]] = []  # (col, row) for highlight

            day_col0 = 1 + (1 if multi else 0)  # first day column index
            row_i = 0  # data row index after header (1..)
            for period in periods:
                time_label = f"{_fmt_time(period.start_time)}–{_fmt_time(period.end_time)}"

                if period.is_break:
                    # ONE row for the whole class: time once, break name across days
                    row_i += 1
                    shade_rows.append(row_i)
                    row = [p(time_label, styles["Small"])]
                    if multi:
                        row.append(p("", styles["Small"]))  # no stream split for breaks
                    for d in days:
                        # Prefer any stream's break label for this period
                        entry = None
                        if multi:
                            for st in class_streams:
                                entry = _lookup_entry(index, cid, d, period, stream_id=str(st.id))
                                if entry:
                                    break
                        if entry is None:
                            entry = _lookup_entry(index, cid, d, period, stream_id="")
                        parts = _cell_parts(entry, break_name=period.name or "Break")
                        row.append(_p_lines(*parts, style=styles["Small"]) if parts else p("—", styles["Small"]))
                    rows.append(row)
                    continue

                # Teaching period: one row per stream when multi, else single row
                stream_list = class_streams if multi else [None]
                start_row = row_i + 1
                for si, st in enumerate(stream_list):
                    row_i += 1
                    # Time only on first stream row; empty on subsequent (SPAN applied later)
                    row = [p(time_label if si == 0 else "", styles["Small"])]
                    if multi:
                        row.append(p(st.name if st else "—", styles["Small"]))
                    for di, d in enumerate(days):
                        sid = str(st.id) if st else ""
                        entry = _lookup_entry(index, cid, d, period, stream_id=sid)
                        is_mine = _is_mine(entry)
                        if mode == "mine_only" and entry is not None and not is_mine and not (
                            entry.is_break_slot if entry else False
                        ):
                            # Blank other teachers' lessons; keep structure
                            parts = []
                        else:
                            parts = _cell_parts(entry)
                        row.append(
                            _p_lines(*parts, style=styles["Small"]) if parts else p("—", styles["Small"])
                        )
                        if mode == "highlight" and is_mine:
                            mine_cells.append((day_col0 + di, row_i))
                        if mode == "mine_only" and is_mine:
                            mine_cells.append((day_col0 + di, row_i))
                    rows.append(row)
                end_row = row_i
                if multi and end_row > start_row:
                    # Time column spans all stream rows for this period
                    span_cmds.append(("SPAN", (0, start_row), (0, end_row)))

            w = ctx.content_width
            first_w = min(w * 0.12, 64)
            stream_w = min(w * 0.10, 52) if multi else 0
            day_w = (w - first_w - stream_w) / max(len(days), 1)
            col_widths = [first_w] + ([stream_w] if multi else []) + [day_w] * len(days)
            table = Table(rows, colWidths=col_widths, repeatRows=1)
            style_cmds = list(branded_table_style(ctx, header=True).getCommands())
            style_cmds.extend([
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ])
            style_cmds.extend(span_cmds)
            for bri in shade_rows:
                style_cmds.append(
                    ("BACKGROUND", (0, bri), (-1, bri), colors.HexColor("#F1F5F9")),
                )
            for col, ridx in mine_cells:
                style_cmds.append(("BACKGROUND", (col, ridx), (col, ridx), MINE_BG))
            table.setStyle(TableStyle(style_cmds))
            flow.append(table)
            flow.append(Spacer(1, 14))

        if teaching_count == 0:
            flow.append(p(
                "No lesson subjects found for this print. "
                "Open the class grid, assign subjects, click Save draft, then print again.",
                styles["Meta"],
            ))
        else:
            flow.append(p(
                "Breaks are shaded (one row). Time is shown once per period across streams. "
                "Cells show subject and teacher when assigned."
                + (" Amber cells are yours." if mode in ("highlight", "mine_only") else ""),
                styles["Meta"],
            ))
        return flow

    return build_branded_pdf(
        tenant=tenant,
        document_type="timetable",
        document_meta=qr_meta,
        title=f"Timetable — {term.name}",
        subtitle=scope_label,
        build_story=story,
        request=request,
        orientation=orientation if orientation in ("portrait", "landscape") else "landscape",
    )
