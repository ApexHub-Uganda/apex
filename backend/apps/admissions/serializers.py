from __future__ import annotations

from rest_framework import serializers

from apps.admissions.models import AdmissionApplication, AdmissionVacancy
from apps.core.email_validation import validate_deliverable_email

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class AdmissionVacancySerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    remaining_openings = serializers.IntegerField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = AdmissionVacancy
        fields = [
            "id",
            "title",
            "description",
            "grade_levels",
            "school_class",
            "school_class_name",
            "academic_year",
            "academic_year_name",
            "openings_count",
            "filled_count",
            "remaining_openings",
            "application_deadline",
            "contact_email",
            "contact_phone",
            "is_active",
            "is_published",
            "show_on_landing",
            "show_on_parent_portal",
            "is_open",
            "created_at",
            "updated_at",
        ]
        read_only_fields = READ_ONLY + ["filled_count", "remaining_openings", "is_open"]

    def validate(self, attrs):
        email = attrs.get("contact_email", getattr(self.instance, "contact_email", ""))
        if email:
            error = validate_deliverable_email(email, required=False)
            if error:
                raise serializers.ValidationError({"contact_email": error})
        openings = attrs.get("openings_count", getattr(self.instance, "openings_count", 1))
        filled = getattr(self.instance, "filled_count", 0) if self.instance else 0
        if openings < filled:
            raise serializers.ValidationError(
                {"openings_count": f"Cannot be less than filled count ({filled})."},
            )
        return attrs


class PublicAdmissionVacancySerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source="tenant.name", read_only=True)
    school_code = serializers.CharField(source="tenant.code", read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    remaining_openings = serializers.IntegerField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = AdmissionVacancy
        fields = [
            "id",
            "title",
            "description",
            "grade_levels",
            "school_name",
            "school_code",
            "school_class_name",
            "openings_count",
            "filled_count",
            "remaining_openings",
            "application_deadline",
            "contact_email",
            "contact_phone",
            "is_open",
        ]


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    student_name = serializers.SerializerMethodField()
    student_admission_number = serializers.CharField(
        source="student.admission_number",
        read_only=True,
    )
    vacancy_title = serializers.CharField(source="vacancy.title", read_only=True)
    admitted_class_name = serializers.CharField(source="admitted_class.name", read_only=True)

    class Meta:
        model = AdmissionApplication
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "gender",
            "email",
            "phone",
            "address",
            "parent_name",
            "parent_email",
            "parent_phone",
            "parent_relationship",
            "vacancy",
            "vacancy_title",
            "grade_applied",
            "previous_school",
            "application_date",
            "status",
            "notes",
            "documents",
            "student",
            "student_name",
            "student_admission_number",
            "admission_date",
            "admitted_class",
            "admitted_class_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = READ_ONLY + [
            "student",
            "admission_date",
            "student_name",
            "student_admission_number",
            "full_name",
        ]

    def get_student_name(self, obj: AdmissionApplication) -> str:
        if obj.student_id:
            return obj.student.full_name
        return ""

    def validate(self, attrs):
        for field in ("email", "parent_email"):
            if field in attrs or not self.partial:
                email = attrs.get(field, getattr(self.instance, field, ""))
                if email:
                    error = validate_deliverable_email(email, required=False)
                    if error:
                        raise serializers.ValidationError({field: error})

        status = attrs.get("status", getattr(self.instance, "status", "pending"))
        if self.instance and self.instance.status == "admitted" and status != "admitted":
            raise serializers.ValidationError({"status": "Admitted applications cannot change status here."})
        return attrs


class AdmitApplicationSerializer(serializers.Serializer):
    school_class = serializers.UUIDField(required=False, allow_null=True)
    admission_number = serializers.CharField(required=False, allow_blank=True, max_length=50)