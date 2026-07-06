from __future__ import annotations

from rest_framework import serializers

from apps.accounts.avatar_service import resolve_avatar_url, user_has_avatar
from apps.core.email_validation import validate_deliverable_email
from apps.core.media_utils import resolve_media_url
from apps.students.models import Admission, Guardian, MedicalRecord, Parent, Student

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

    class Meta:
        model = Parent
        fields = [
            "id", "full_name", "first_name", "middle_name", "last_name",
            "email", "phone", "mpesa_phone", "relationship_to_student",
            "county", "is_fee_payer", "has_portal_access", "preferred_contact_method",
            "children_count", "children_names", "avatar_url", "has_avatar",
        ]

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

    class Meta:
        model = Student
        fields = [
            "id", "full_name", "admission_number", "first_name", "last_name",
            "gender", "date_of_birth", "status", "class_name", "stream_name",
            "boarding_status", "upi_number", "county", "phone", "parent_names",
            "enrollment_date", "photo_url", "avatar_url", "has_avatar",
        ]

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

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = READ_ONLY

    def validate(self, attrs):
        _validate_optional_emails(attrs, ("email", "alternate_email"))
        return attrs


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