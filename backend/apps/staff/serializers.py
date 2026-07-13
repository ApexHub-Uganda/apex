from __future__ import annotations

from rest_framework import serializers

from apps.accounts.avatar_service import resolve_avatar_url, user_has_avatar
from apps.core.constants import UserRole
from apps.core.serializer_fields import DeliverableEmailField
from apps.core.media_utils import resolve_media_url
from apps.academics.models import Department
from apps.staff.models import Staff, Teacher
from apps.tenants.context import TenantContext
from apps.staff.services import StaffOnboardingError, onboard_staff, update_staff_record
from apps.staff.staff_roles import get_role_definition, list_staff_role_options


def _tenant_department_queryset(context: dict):
    request = context.get("request")
    tenant = TenantContext.get_tenant()
    if tenant is None and request and getattr(request.user, "tenant_id", None):
        tenant = request.user.tenant
    if tenant is None:
        return Department.objects.none()
    return Department.objects.filter(tenant=tenant, is_deleted=False)


def _tenant_staff_queryset(context: dict):
    request = context.get("request")
    tenant = TenantContext.get_tenant()
    if tenant is None and request and getattr(request.user, "tenant_id", None):
        tenant = request.user.tenant
    if tenant is None:
        return Staff.objects.none()
    return Staff.objects.filter(tenant=tenant, is_deleted=False)


class TeacherNestedSerializer(serializers.ModelSerializer):
    subject_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Teacher
        fields = [
            "qualification", "specialization", "years_experience",
            "is_class_teacher", "subject_ids",
        ]


class StaffListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, allow_null=True)
    role_label = serializers.SerializerMethodField()
    has_user_account = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "id", "employee_id", "full_name", "first_name", "middle_name", "last_name",
            "email", "personal_email", "phone", "staff_category", "portal_role", "role_label",
            "designation", "department", "department_name", "employment_type", "status",
            "has_portal_access", "has_user_account", "date_joined", "photo",
            "photo_url", "avatar_url", "has_avatar",
        ]

    def get_photo_url(self, obj: Staff) -> str | None:
        return resolve_media_url(self.context.get("request"), obj.photo)

    def get_avatar_url(self, obj: Staff) -> str | None:
        if obj.user_id:
            url = resolve_avatar_url(obj.user, self.context.get("request"))
            if url:
                return url
        return self.get_photo_url(obj)

    def get_has_avatar(self, obj: Staff) -> bool:
        if obj.photo:
            return True
        if obj.user_id:
            return user_has_avatar(obj.user)
        return False

    def get_role_label(self, obj: Staff) -> str:
        return get_role_definition(obj.portal_role).get("label", obj.portal_role)

    def get_has_user_account(self, obj: Staff) -> bool:
        return obj.user_id is not None


class StaffDetailSerializer(StaffListSerializer):
    teacher_profile = serializers.SerializerMethodField()
    supervisor_name = serializers.CharField(source="supervisor.full_name", read_only=True, allow_null=True)

    def get_teacher_profile(self, obj: Staff) -> dict | None:
        try:
            teacher = obj.teacher_profile
        except Exception:
            return None
        return TeacherNestedSerializer(teacher).data

    class Meta(StaffListSerializer.Meta):
        fields = StaffListSerializer.Meta.fields + [
            "alternate_phone", "gender", "date_of_birth", "national_id", "nationality",
            "address", "emergency_contact", "emergency_phone", "emergency_relationship",
            "qualification_summary", "notes", "supervisor", "supervisor_name",
            "date_left", "user", "teacher_profile", "created_at", "updated_at",
        ]


class StaffOnboardSerializer(serializers.Serializer):
    employee_id = serializers.CharField(required=False, allow_blank=True, max_length=50)
    first_name = serializers.CharField(max_length=100)
    middle_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = DeliverableEmailField()
    personal_email = DeliverableEmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20)
    alternate_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    gender = serializers.ChoiceField(
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        required=False,
        allow_blank=True,
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    national_id = serializers.CharField(required=False, allow_blank=True, max_length=50)
    nationality = serializers.CharField(required=False, allow_blank=True, max_length=100)
    staff_category = serializers.ChoiceField(
        choices=[c[0] for c in [
            ("management", "Management"),
            ("teaching", "Teaching"),
            ("administrative", "Administrative"),
            ("support", "Support"),
            ("finance", "Finance"),
        ]],
        required=False,
    )
    portal_role = serializers.ChoiceField(choices=UserRole.CHOICES)
    designation = serializers.CharField(required=False, allow_blank=True, max_length=100)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.none(),
        required=False,
        allow_null=True,
    )
    supervisor = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.none(),
        required=False,
        allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = _tenant_department_queryset(self.context)
        self.fields["supervisor"].queryset = _tenant_staff_queryset(self.context)
    date_joined = serializers.DateField(required=False)
    employment_type = serializers.ChoiceField(
        choices=[("full_time", "Full Time"), ("part_time", "Part Time"), ("contract", "Contract"), ("intern", "Intern")],
        required=False,
    )
    status = serializers.ChoiceField(
        choices=[("active", "Active"), ("on_leave", "On Leave"), ("suspended", "Suspended"), ("terminated", "Terminated")],
        required=False,
    )
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True, max_length=100)
    emergency_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    emergency_relationship = serializers.CharField(required=False, allow_blank=True, max_length=50)
    qualification_summary = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    has_portal_access = serializers.BooleanField(required=False, default=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, min_length=8)
    mark_email_verified = serializers.BooleanField(required=False, default=False)
    create_teacher_profile = serializers.BooleanField(required=False, default=False)
    teacher = TeacherNestedSerializer(required=False)
    subject_ids = serializers.ListField(child=serializers.UUIDField(), required=False)

    def validate_portal_role(self, value: str) -> str:
        if value in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.PARENT, UserRole.STUDENT):
            raise serializers.ValidationError("Select a staff dashboard role for employees.")
        return value

    def create(self, validated_data: dict):
        request = self.context.get("request")
        tenant = getattr(request.user, "tenant", None) if request else None
        if tenant is None:
            raise serializers.ValidationError("No school tenant linked to this account.")

        teacher_payload = validated_data.pop("teacher", None) or {}
        subject_ids = validated_data.pop("subject_ids", None)
        if subject_ids:
            teacher_payload["subject_ids"] = subject_ids
        if teacher_payload:
            validated_data["teacher"] = teacher_payload

        try:
            staff = onboard_staff(tenant, actor=request.user, data=validated_data)
        except StaffOnboardingError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        return staff


class StaffUpdateSerializer(serializers.ModelSerializer):
    teacher = TeacherNestedSerializer(required=False)
    email = DeliverableEmailField()
    personal_email = DeliverableEmailField(required=False, allow_blank=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.none(),
        required=False,
        allow_null=True,
    )
    supervisor = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.none(),
        required=False,
        allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = _tenant_department_queryset(self.context)
        self.fields["supervisor"].queryset = _tenant_staff_queryset(self.context)

    class Meta:
        model = Staff
        fields = [
            "employee_id", "first_name", "middle_name", "last_name", "email", "personal_email",
            "phone", "alternate_phone", "gender", "date_of_birth", "national_id", "nationality",
            "staff_category", "portal_role", "designation", "department", "supervisor",
            "date_joined", "date_left", "employment_type", "status", "address",
            "emergency_contact", "emergency_phone", "emergency_relationship",
            "qualification_summary", "notes", "has_portal_access", "teacher",
        ]
        read_only_fields = []

    def update(self, instance: Staff, validated_data: dict) -> Staff:
        teacher_data = validated_data.pop("teacher", None)
        request = self.context.get("request")
        try:
            staff = update_staff_record(instance, actor=request.user, data=validated_data)
        except StaffOnboardingError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        if teacher_data and hasattr(staff, "teacher_profile"):
            teacher = staff.teacher_profile
            subject_ids = teacher_data.pop("subject_ids", None)
            for key, value in teacher_data.items():
                setattr(teacher, key, value)
            teacher.save()
            if subject_ids is not None:
                teacher.subjects.set(subject_ids)
        return staff


class StaffOnboardResponseSerializer(StaffDetailSerializer):
    temporary_password = serializers.SerializerMethodField()

    class Meta(StaffDetailSerializer.Meta):
        fields = StaffDetailSerializer.Meta.fields + ["temporary_password"]

    def get_temporary_password(self, obj: Staff) -> str | None:
        return getattr(obj, "_onboarding_temp_password", None)


class StaffRoleOptionSerializer(serializers.Serializer):
    role = serializers.CharField()
    label = serializers.CharField()
    category = serializers.CharField()
    default_designation = serializers.CharField()
    requires_teacher_profile = serializers.BooleanField()
    portal_access_default = serializers.BooleanField()
    description = serializers.CharField()


class TeacherSerializer(serializers.ModelSerializer):
    staff_detail = StaffListSerializer(source="staff", read_only=True)

    class Meta:
        model = Teacher
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


def serialize_role_options() -> list[dict]:
    return list_staff_role_options()