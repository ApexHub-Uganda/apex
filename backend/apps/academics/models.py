"""Academic structure models."""
from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class AcademicYear(BaseModel):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("tenant", "name")]
        indexes = [models.Index(fields=["tenant", "is_current"])]


class Term(BaseModel):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=50)
    term_number = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1, 2, or 3 for East African term calendars (Uganda default)")
    start_date = models.DateField()
    end_date = models.DateField()
    reporting_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    mid_term_break_start = models.DateField(null=True, blank=True)
    mid_term_break_end = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_date"]
        unique_together = [("tenant", "academic_year", "name")]


class Department(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    head = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, blank=True, related_name="headed_departments")
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("tenant", "code")]
        ordering = ["name"]


class Class(BaseModel):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="classes")
    level_type = models.CharField(
        max_length=30,
        choices=[
            ("pre_primary", "Pre-Primary"),
            ("primary", "Primary"),
            ("junior_secondary", "Junior Secondary"),
            ("senior_secondary", "Senior Secondary"),
            ("tertiary", "Tertiary"),
        ],
        blank=True,
    )
    curriculum = models.CharField(
        max_length=30,
        choices=[
            ("uneb", "UNEB (Uganda)"),
            ("uganda_cbe", "Uganda Competence-Based"),
            ("cbc", "CBC (Kenya)"),
            ("844", "8-4-4"),
            ("igcse", "IGCSE"),
            ("ace", "ACE"),
            ("other", "Other"),
        ],
        default="uneb",
    )
    section = models.CharField(max_length=20, blank=True, help_text="Section label e.g. A, B, East")
    class_teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, blank=True, related_name="classes")
    capacity = models.PositiveIntegerField(default=40)
    room = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "Classes"
        unique_together = [("tenant", "academic_year", "code")]
        ordering = ["name"]


class Stream(BaseModel):
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="streams")
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=40)
    # Stream-level class teacher (e.g. S.1 East). Whole-class heads use Class.class_teacher.
    class_teacher = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_streams",
        help_text="Class teacher for this stream only (optional).",
    )

    class Meta:
        unique_together = [("tenant", "school_class", "name")]
        ordering = ["school_class__name", "name"]


class ClassPrefect(BaseModel):
    """Student leadership role within a class or stream."""

    PREFECT_ROLES = [
        ("head", "Head Prefect"),
        ("deputy", "Deputy Prefect"),
        ("prefect", "Prefect"),
    ]

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="prefect_roles",
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="prefects",
    )
    stream = models.ForeignKey(
        Stream,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="prefects",
    )
    role = models.CharField(max_length=20, choices=PREFECT_ROLES, default="prefect")
    appointed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointed_prefects",
    )

    class Meta:
        ordering = ["role", "student__last_name", "student__first_name"]
        unique_together = [("tenant", "student", "school_class", "stream")]
        indexes = [
            models.Index(fields=["tenant", "school_class"]),
            models.Index(fields=["tenant", "stream"]),
        ]
        verbose_name = "class prefect"


class Subject(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="subjects")
    description = models.TextField(blank=True)
    is_compulsory = models.BooleanField(default=True)

    class Meta:
        unique_together = [("tenant", "code")]
        ordering = ["name"]

    @property
    def has_papers(self) -> bool:
        return self.papers.exists()


class SubjectPaper(BaseModel):
    """Optional exam papers within a subject (e.g. Mathematics M223, M224)."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="papers")
    code = models.CharField(max_length=20, help_text="Paper code e.g. M223")
    name = models.CharField(max_length=100, blank=True, help_text="Optional label e.g. Paper 1")
    sort_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["sort_order", "code"]
        unique_together = [("tenant", "subject", "code")]
        verbose_name = "subject paper"


class TimetableSchedule(BaseModel):
    """Published lesson or exam timetable for a term / examination session."""

    SCHEDULE_LESSON = "lesson"
    SCHEDULE_EXAM = "exam"
    SCHEDULE_TYPE_CHOICES = [
        (SCHEDULE_LESSON, "Lesson timetable"),
        (SCHEDULE_EXAM, "Exam timetable"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"  # legacy alias — treat like published for visibility
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    name = models.CharField(max_length=255)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES, default=SCHEDULE_LESSON, db_index=True)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="timetable_schedules", null=True, blank=True,
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name="timetable_schedules", null=True, blank=True,
    )
    examination_session = models.ForeignKey(
        "examinations.ExaminationSession",
        on_delete=models.CASCADE,
        related_name="timetable_schedules",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    is_locked = models.BooleanField(
        default=False,
        help_text="When true, only school admins may edit or delete entries for this schedule.",
    )
    generation_seed = models.PositiveIntegerField(null=True, blank=True)
    config = models.JSONField(default=dict, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_timetable_schedules",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_timetable_schedules",
    )

    @property
    def is_published(self) -> bool:
        return self.status in (self.STATUS_PUBLISHED, self.STATUS_ACTIVE)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "schedule_type", "status"]),
            models.Index(fields=["tenant", "term", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.schedule_type}/{self.status})"


class TimetableGenerationDraft(BaseModel):
    """Temporary generation output until the user chooses USE IT or discards."""

    schedule_type = models.CharField(max_length=20, choices=TimetableSchedule.SCHEDULE_TYPE_CHOICES)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, null=True, blank=True, related_name="timetable_drafts")
    examination_session = models.ForeignKey(
        "examinations.ExaminationSession",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="timetable_drafts",
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, null=True, blank=True, related_name="timetable_drafts",
    )
    name = models.CharField(max_length=255, blank=True)
    seed = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    slots = models.JSONField(default=list, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "created_by", "schedule_type"])]


class Timetable(BaseModel):
    schedule = models.ForeignKey(
        TimetableSchedule,
        on_delete=models.CASCADE,
        related_name="entries",
        null=True,
        blank=True,
    )
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="timetables")
    stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name="timetables",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="timetable_entries",
        null=True,
        blank=True,
        help_text="Null for break / free periods.",
    )
    teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="timetable_entries")
    period = models.ForeignKey(
        "academics.Period", on_delete=models.SET_NULL, null=True, blank=True, related_name="timetable_entries",
    )
    term = models.ForeignKey(
        Term, on_delete=models.SET_NULL, null=True, blank=True, related_name="timetable_entries",
    )
    examination_session = models.ForeignKey(
        "examinations.ExaminationSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timetable_entries",
    )
    schedule_type = models.CharField(
        max_length=20,
        choices=TimetableSchedule.SCHEDULE_TYPE_CHOICES,
        default=TimetableSchedule.SCHEDULE_LESSON,
        db_index=True,
    )
    day_of_week = models.PositiveSmallIntegerField(choices=[
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"),
        (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ], null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True, help_text="Used for exam timetable slots")
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True)
    is_break_slot = models.BooleanField(
        default=False,
        help_text="True when this cell is a break / free period (no subject).",
    )
    slot_label = models.CharField(
        max_length=80,
        blank=True,
        help_text="Display label for break or free periods (e.g. Break, Assembly).",
    )
    # Denormalized labels for reliable printouts even if FKs are awkward to join
    display_subject = models.CharField(
        max_length=120,
        blank=True,
        help_text="Cached subject name at save time for PDF/print.",
    )
    display_teacher = models.CharField(
        max_length=120,
        blank=True,
        help_text="Cached teacher name at save time for PDF/print.",
    )

    class Meta:
        ordering = ["day_of_week", "exam_date", "start_time"]
        indexes = [
            models.Index(fields=["tenant", "school_class", "day_of_week"]),
            models.Index(fields=["tenant", "schedule", "schedule_type"]),
            models.Index(fields=["tenant", "exam_date"]),
            models.Index(fields=["tenant", "teacher", "day_of_week"]),
        ]


class TeachingAssignment(BaseModel):
    """Authoritative teacher ↔ class ↔ subject staffing link (many-to-many via rows)."""

    teacher = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching_assignments",
        help_text="Optional term scope for mid-year staffing history.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["school_class__name", "subject__code", "teacher__staff__last_name"]
        unique_together = [("tenant", "teacher", "school_class", "subject")]
        indexes = [
            models.Index(fields=["tenant", "teacher", "is_active"]),
            models.Index(fields=["tenant", "school_class", "is_active"]),
            models.Index(fields=["tenant", "subject", "is_active"]),
        ]
        verbose_name = "teaching assignment"

    def __str__(self) -> str:
        return f"{self.teacher_id} → {self.school_class_id} / {self.subject_id}"


class Assignment(BaseModel):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assignments")
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="assignments")
    teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="assignments")
    description = models.TextField()
    due_date = models.DateTimeField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    attachment = models.FileField(upload_to="assignments/", blank=True, null=True)

    class Meta:
        ordering = ["-due_date"]


class Homework(BaseModel):
    """Unified class assignment / homework item (school-created)."""

    KIND_HOMEWORK = "homework"
    KIND_ASSIGNMENT = "assignment"
    KIND_PROJECT = "project"
    KIND_CHOICES = [
        (KIND_HOMEWORK, "Homework"),
        (KIND_ASSIGNMENT, "Assignment"),
        (KIND_PROJECT, "Project"),
    ]

    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_HOMEWORK)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="homework")
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="homework")
    teacher = models.ForeignKey("staff.Teacher", on_delete=models.SET_NULL, null=True, related_name="homework")
    description = models.TextField()
    assigned_date = models.DateField()
    due_date = models.DateField()
    max_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_published = models.BooleanField(default=True)
    requires_parent_ack = models.BooleanField(default=False)

    class Meta:
        ordering = ["-assigned_date"]


class HomeworkSubmission(BaseModel):
    """Student submission + optional parent acknowledgement loop."""

    STATUS_PENDING = "pending"
    STATUS_SUBMITTED = "submitted"
    STATUS_LATE = "late"
    STATUS_GRADED = "graded"
    STATUS_MISSING = "missing"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_LATE, "Late"),
        (STATUS_GRADED, "Graded"),
        (STATUS_MISSING, "Missing"),
    ]

    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="homework_submissions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    parent_acknowledged = models.BooleanField(default=False)
    parent_acknowledged_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at", "student__last_name"]
        unique_together = [("tenant", "homework", "student")]
        indexes = [models.Index(fields=["tenant", "homework", "status"])]


class Period(BaseModel):
    """
    School-wide bell schedule row. Same start/end applies every day (Mon–Sun).
    Creators fill subjects into a day×period grid; breaks are marked here.
    """

    name = models.CharField(max_length=50, help_text="e.g. Period 1, Break, Lunch")
    start_time = models.TimeField(help_text="Start time (same for all weekdays)")
    end_time = models.TimeField(help_text="End time (same for all weekdays)")
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_break = models.BooleanField(
        default=False,
        help_text="Break / assembly / free slot — pre-filled on class grids, no subject required.",
    )

    class Meta:
        ordering = ["sort_order", "start_time"]
        unique_together = [("tenant", "name")]


class Classroom(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    building = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=20, blank=True)
    capacity = models.PositiveIntegerField(default=40)
    room_type = models.CharField(
        max_length=20,
        choices=[
            ("classroom", "Classroom"),
            ("lab", "Laboratory"),
            ("hall", "Hall"),
            ("office", "Office"),
            ("other", "Other"),
        ],
        default="classroom",
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "code")]


class ClassNotice(BaseModel):
    """Notices published to a specific class (class teacher tools)."""

    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="notices")
    title = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_notices",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["tenant", "school_class", "is_published"])]


class DisciplineRemark(BaseModel):
    """Student discipline / pastoral case with optional workflow outcomes."""

    REMARK_TYPES = [
        ("commendation", "Commendation"),
        ("warning", "Warning"),
        ("sanction", "Sanction"),
        ("suspension", "Suspension"),
        ("parent_meeting", "Parent meeting"),
        ("counsellor", "Counsellor referral"),
    ]
    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="discipline_remarks")
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="discipline_remarks")
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discipline_remarks",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discipline_remarks",
    )
    remark_type = models.CharField(max_length=20, choices=REMARK_TYPES, default="warning")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    incident_date = models.DateField()
    suspension_days = models.PositiveSmallIntegerField(null=True, blank=True)
    parent_meeting_on = models.DateField(null=True, blank=True)
    counsellor_referral = models.BooleanField(default=False)
    conduct_points = models.IntegerField(
        default=0,
        help_text="Negative for sanctions, positive for commendations; rolls into report conduct grade.",
    )
    resolution_notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        "staff.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discipline_remarks",
    )

    class Meta:
        ordering = ["-incident_date", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "school_class", "incident_date"]),
            models.Index(fields=["tenant", "student"]),
            models.Index(fields=["tenant", "status"]),
        ]

class StudentAcademicPlacement(BaseModel):
    """Historical class/stream placement for a student within an academic year."""

    STATUS_ACTIVE = "active"
    STATUS_PROMOTED = "promoted"
    STATUS_REPEATED = "repeated"
    STATUS_GRADUATED = "graduated"
    STATUS_TRANSFERRED = "transferred"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_PROMOTED, "Promoted"),
        (STATUS_REPEATED, "Repeated / Held back"),
        (STATUS_GRADUATED, "Graduated"),
        (STATUS_TRANSFERRED, "Transferred"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    ]

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="academic_placements",
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="student_placements",
    )
    school_class = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="student_placements",
    )
    stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_placements",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    is_current = models.BooleanField(default=True, db_index=True)
    enrolled_on = models.DateField(null=True, blank=True)
    ended_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-academic_year__start_date", "student__last_name"]
        unique_together = [("tenant", "student", "academic_year", "school_class", "stream")]
        indexes = [
            models.Index(fields=["tenant", "academic_year", "is_current"]),
            models.Index(fields=["tenant", "student", "is_current"]),
        ]


class PromotionBatch(BaseModel):
    """One controlled promotion run (wizard session) for a source class/stream."""

    STATUS_DRAFT = "draft"
    STATUS_PREVIEWED = "previewed"
    STATUS_COMMITTED = "committed"
    STATUS_UNDONE = "undone"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PREVIEWED, "Previewed"),
        (STATUS_COMMITTED, "Committed"),
        (STATUS_UNDONE, "Undone"),
    ]

    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="promotion_batches",
    )
    target_academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="incoming_promotion_batches",
        null=True, blank=True,
    )
    source_class = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="source_promotion_batches",
    )
    source_stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_promotion_batches",
    )
    default_target_class = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, blank=True, related_name="target_promotion_batches",
    )
    default_target_stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name="target_promotion_batches",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    mapping = models.JSONField(default=dict, blank=True, help_text="student_id → action payload")
    preview = models.JSONField(default=dict, blank=True)
    committed_at = models.DateTimeField(null=True, blank=True)
    committed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="committed_promotions",
    )
    undone_at = models.DateTimeField(null=True, blank=True)
    undone_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="undone_promotions",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status", "academic_year"])]


class PromotionAction(BaseModel):
    """Per-student outcome within a promotion batch."""

    ACTION_PROMOTE = "promote"
    ACTION_HOLD = "hold"
    ACTION_GRADUATE = "graduate"
    ACTION_SKIP = "skip"
    ACTION_CHOICES = [
        (ACTION_PROMOTE, "Promote"),
        (ACTION_HOLD, "Hold back / Repeat"),
        (ACTION_GRADUATE, "Graduate"),
        (ACTION_SKIP, "Skip / No change"),
    ]

    batch = models.ForeignKey(PromotionBatch, on_delete=models.CASCADE, related_name="actions")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="promotion_actions")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_PROMOTE)
    from_class = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    from_stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    to_class = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    to_stream = models.ForeignKey(
        Stream, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    reason = models.CharField(max_length=255, blank=True)
    applied = models.BooleanField(default=False)
    placement = models.ForeignKey(
        StudentAcademicPlacement, on_delete=models.SET_NULL, null=True, blank=True, related_name="promotion_actions",
    )

    class Meta:
        ordering = ["student__last_name", "student__first_name"]
        unique_together = [("tenant", "batch", "student")]


class StudentSubjectRegistration(BaseModel):
    """Subjects a student is registered for in a year/term (electives & combinations)."""

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="subject_registrations",
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="subject_registrations",
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, null=True, blank=True, related_name="subject_registrations",
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="student_registrations")
    combination_code = models.CharField(
        max_length=40, blank=True, help_text="Optional A-level combination e.g. PCM, HEL",
    )
    is_core = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["subject__name"]
        unique_together = [("tenant", "student", "academic_year", "term", "subject")]
        indexes = [models.Index(fields=["tenant", "student", "academic_year", "is_active"])]


class AssessmentScheme(BaseModel):
    """School-defined continuous assessment weights (BOT/MOT/EOT etc.)."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    # components: [{key, label, weight_percent, exam_type_hint}]
    components = models.JSONField(default=list, blank=True)
    paper_aggregation = models.CharField(
        max_length=20,
        choices=[
            ("average", "Average of papers"),
            ("sum", "Sum of papers"),
            ("weighted", "Weighted papers"),
        ],
        default="average",
    )
    use_division_bands = models.BooleanField(
        default=False,
        help_text="When true, total aggregates can map to informal division bands.",
    )
    division_bands = models.JSONField(
        default=list, blank=True,
        help_text="Optional [{min_aggregate, max_aggregate, division, remarks}]",
    )

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "name")]


class SubjectCombination(BaseModel):
    """School-defined subject combination presets (e.g. A-level PCM, HEL)."""

    LEVEL_O = "o_level"
    LEVEL_A = "a_level"
    LEVEL_PRIMARY = "primary"
    LEVEL_CHOICES = [
        (LEVEL_PRIMARY, "Primary"),
        (LEVEL_O, "O-Level"),
        (LEVEL_A, "A-Level"),
    ]

    code = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_A)
    # subjects: [{subject_id or code, is_core, min_papers}]
    subjects = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "code"]
        unique_together = [("tenant", "code")]
