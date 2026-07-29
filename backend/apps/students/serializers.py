from __future__ import annotations

from rest_framework import serializers

from apps.accounts.avatar_service import resolve_avatar_url, user_has_avatar
from apps.core.email_validation import validate_deliverable_email
from apps.core.media_utils import resolve_media_url
from apps.students.models import Admission, Guardian, MedicalRecord, Parent, Student
from apps.students.profile import is_profile_incomplete

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class ParentChildSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    class_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "full_name", "admission_number", "class_name",
            "status", "gender", "boarding_status",
        ]

    def get_class_name(self, obj) -> str | None:
        return obj.school_class.name if obj.school_class else None


class ParentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    children_count = serializers.SerializerMethodField()
    children_names = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    is_dual_role = serializers.SerializerMethodField()
    also_staff = serializers.SerializerMethodField()
    available_roles = serializers.SerializerMethodField()
    dual_role_label = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = [
            "id", "full_name", "first_name", "middle_name", "last_name",
            "email", "phone", "mpesa_phone", "relationship_to_student",
            "county", "is_fee_payer", "has_portal_access", "preferred_contact_method",
            "children_count", "children_names", "avatar_url", "has_avatar",
            "user_id", "is_dual_role", "also_staff", "available_roles", "dual_role_label",
        ]

    def _identity(self, obj):
        if not obj.user_id:
            return None
        if not hasattr(self, "_identity_cache"):
            self._identity_cache = {}
        key = str(obj.user_id)
        if key not in self._identity_cache:
            from apps.accounts.dual_roles import dual_identity_for_user
            self._identity_cache[key] = dual_identity_for_user(obj.user)
        return self._identity_cache[key]

    def get_user_id(self, obj) -> str | None:
        return str(obj.user_id) if obj.user_id else None

    def get_is_dual_role(self, obj) -> bool:
        ident = self._identity(obj)
        return bool(ident and ident.get("is_dual_role"))

    def get_also_staff(self, obj) -> bool:
        ident = self._identity(obj)
        return bool(ident and ident.get("has_staff_profile"))

    def get_available_roles(self, obj) -> list:
        ident = self._identity(obj)
        return list(ident.get("available_roles") or []) if ident else []

    def get_dual_role_label(self, obj) -> str:
        if self.get_also_staff(obj):
            return "Also staff"
        if self.get_is_dual_role(obj):
            return "Dual role"
        return ""

    def get_avatar_url(self, obj) -> str | None:
        if obj.user_id:
            return resolve_avatar_url(obj.user, self.context.get("request"))
        return None

    def get_has_avatar(self, obj) -> bool:
        if obj.user_id:
            return user_has_avatar(obj.user)
        return False

    def get_children_count(self, obj) -> int:
        if hasattr(obj, "_children_count"):
            return obj._children_count
        return obj.children.count()

    def get_children_names(self, obj) -> str:
        children = list(obj.children.all()[:3])
        names = [c.full_name for c in children]
        total = getattr(obj, "_children_count", None) or obj.children.count()
        extra = total - len(names)
        if extra > 0:
            names.append(f"+{extra} more")
        return ", ".join(names) if names else ""


def _validate_optional_emails(attrs: dict, fields: tuple[str, ...]) -> dict:
    errors = {}
    for field in fields:
        value = attrs.get(field)
        if value:
            error = validate_deliverable_email(value)
            if error:
                errors[field] = error
    if errors:
        raise serializers.ValidationError(errors)
    return attrs


class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Parent
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs):
        _validate_optional_emails(attrs, ("email", "alternate_email"))
        if "email" in attrs or self.partial:
            email = attrs.get("email", getattr(self.instance, "email", ""))
            error = validate_deliverable_email(email, required=True)
            if error:
                raise serializers.ValidationError({"email": error})
        return attrs


class ParentDetailSerializer(ParentSerializer):
    children = ParentChildSummarySerializer(many=True, read_only=True)
    child_ids = serializers.PrimaryKeyRelatedField(
        source="children",
        many=True,
        queryset=Student.objects.all(),
        required=False,
        write_only=True,
    )

    class Meta(ParentSerializer.Meta):
        fields = "__all__"
        read_only_fields = READ_ONLY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is None and request and getattr(request.user, "tenant_id", None):
            tenant = request.user.tenant
        if tenant is not None:
            self.fields["child_ids"].queryset = Student.objects.filter(tenant=tenant)


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    class_name = serializers.SerializerMethodField()
    stream_name = serializers.SerializerMethodField()
    parent_names = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()
    is_profile_incomplete = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "full_name", "admission_number", "first_name", "last_name",
            "gender", "date_of_birth", "status", "class_name", "stream_name",
            "boarding_status", "upi_number", "county", "phone", "parent_names",
            "enrollment_date", "photo_url", "avatar_url", "has_avatar",
            "is_profile_incomplete",
        ]

    def get_is_profile_incomplete(self, obj) -> bool:
        return is_profile_incomplete(obj)

    def get_photo_url(self, obj) -> str | None:
        return resolve_media_url(self.context.get("request"), obj.photo)

    def get_avatar_url(self, obj) -> str | None:
        if obj.user_id:
            return resolve_avatar_url(obj.user, self.context.get("request"))
        return self.get_photo_url(obj)

    def get_has_avatar(self, obj) -> bool:
        if obj.photo:
            return True
        if obj.user_id:
            return user_has_avatar(obj.user)
        return False

    def get_class_name(self, obj) -> str | None:
        return obj.school_class.name if obj.school_class else None

    def get_stream_name(self, obj) -> str | None:
        return obj.stream.name if obj.stream else None

    def get_parent_names(self, obj) -> str:
        parents = obj.parents.all()[:2]
        names = [p.full_name for p in parents]
        extra = obj.parents.count() - len(names)
        if extra > 0:
            names.append(f"+{extra} more")
        return ", ".join(names) if names else ""


class StudentDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    class_name = serializers.SerializerMethodField()
    stream_name = serializers.SerializerMethodField()
    parent_ids = serializers.PrimaryKeyRelatedField(
        source="parents", many=True, read_only=True,
    )

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_class_name(self, obj) -> str | None:
        return obj.school_class.name if obj.school_class else None

    def get_stream_name(self, obj) -> str | None:
        return obj.stream.name if obj.stream else None


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    admission_number = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs):
        _validate_optional_emails(attrs, ("email", "alternate_email"))
        admission_number = (attrs.get("admission_number") or "").strip()
        if admission_number:
            attrs["admission_number"] = admission_number
        elif not attrs.get("school_class"):
            raise serializers.ValidationError({
                "admission_number": "Admission number is required when no class is selected.",
            })
        return attrs

    def create(self, validated_data):
        if not (validated_data.get("admission_number") or "").strip() and validated_data.get("school_class"):
            from apps.students.profile import generate_admission_number

            tenant = validated_data.get("tenant")
            if tenant is None:
                request = self.context.get("request")
                tenant = getattr(request.user, "tenant", None) if request else None
            if tenant is not None:
                validated_data["admission_number"] = generate_admission_number(
                    tenant,
                    school_class=validated_data["school_class"],
                )
        return super().create(validated_data)


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs):
        if "email" in attrs or not self.partial:
            email = attrs.get("email", getattr(self.instance, "email", ""))
            error = validate_deliverable_email(email, required=True)
            if error:
                raise serializers.ValidationError({"email": error})
        return attrs


class AdmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = "__all__"
        read_only_fields = READ_ONLY


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = "__all__"
        read_only_fields = READ_ONLY