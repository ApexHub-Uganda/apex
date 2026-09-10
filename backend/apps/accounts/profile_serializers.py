"""Extended profile serializers — self-service vs admin-only fields."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.avatar_serializers import AvatarFieldsMixin
from apps.accounts.models import User
from apps.accounts.profile_service import (
    PARENT_SELF_EDITABLE,
    STAFF_SELF_EDITABLE,
    USER_SELF_EDITABLE,
    build_profile_completion,
    get_user_self_editable_fields,
)
from apps.core.email_validation import validate_deliverable_email
from apps.staff.models import Staff
from apps.students.models import Parent


class StaffSelfProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = [
            "id", "employee_id", "first_name", "middle_name", "last_name", "full_name",
            "email", "personal_email", "phone", "alternate_phone", "gender", "address",
            "emergency_contact", "emergency_phone", "emergency_relationship",
            "portal_role", "designation", "staff_category", "department",
            "employment_type", "status", "date_joined", "national_id", "nationality",
            "qualification_summary", "has_portal_access",
        ]
        read_only_fields = [
            "id", "employee_id", "first_name", "last_name", "full_name", "email",
            "portal_role", "designation", "staff_category", "department",
            "employment_type", "status", "date_joined", "national_id", "nationality",
            "qualification_summary", "has_portal_access",
        ]


class StaffSelfProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = list(STAFF_SELF_EDITABLE)

    def validate_personal_email(self, value: str) -> str:
        if not value:
            return value
        error = validate_deliverable_email(value, required=False)
        if error:
            raise serializers.ValidationError(error)
        return value

    def update(self, instance: Staff, validated_data: dict) -> Staff:
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        user = instance.user
        if user:
            sync_fields = {}
            if "phone" in validated_data:
                sync_fields["phone"] = validated_data["phone"]
            if "middle_name" in validated_data and hasattr(user, "first_name"):
                pass
            if sync_fields:
                for k, v in sync_fields.items():
                    setattr(user, k, v)
                user.save(update_fields=[*sync_fields.keys(), "updated_at"])
        return instance


class ParentSelfProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Parent
        fields = [
            "id", "first_name", "middle_name", "last_name", "full_name", "email",
            "alternate_email", "phone", "alternate_phone", "address", "city", "country",
            "occupation", "employer", "relationship_to_student", "preferred_contact_method",
            "national_id", "has_portal_access",
        ]
        read_only_fields = [
            "id", "first_name", "last_name", "full_name", "email", "relationship_to_student",
            "national_id", "has_portal_access",
        ]


class ParentSelfProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = list(PARENT_SELF_EDITABLE)

    def validate_alternate_email(self, value: str) -> str:
        if not value:
            return value
        error = validate_deliverable_email(value, required=False)
        if error:
            raise serializers.ValidationError(error)
        return value


class MeProfileUpdateSerializer(serializers.ModelSerializer):
    staff_profile = StaffSelfProfileUpdateSerializer(required=False)
    parent_profile = ParentSelfProfileUpdateSerializer(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "staff_profile", "parent_profile"]

    def validate(self, attrs: dict) -> dict:
        allowed = get_user_self_editable_fields(self.instance) | {"staff_profile", "parent_profile"}
        extra = set(self.initial_data.keys()) - allowed
        if extra:
            raise serializers.ValidationError(
                {k: "This field cannot be changed from your profile." for k in extra}
            )
        return attrs

    def update(self, instance: User, validated_data: dict) -> User:
        staff_data = validated_data.pop("staff_profile", None)
        parent_data = validated_data.pop("parent_profile", None)

        for key in get_user_self_editable_fields(instance):
            if key in validated_data:
                setattr(instance, key, validated_data[key])
        instance.save()

        staff = getattr(instance, "staff_profile", None)
        if staff and staff_data:
            StaffSelfProfileUpdateSerializer().update(staff, staff_data)

        parent = getattr(instance, "parent_profile", None)
        if parent and parent_data:
            ParentSelfProfileUpdateSerializer().update(parent, parent_data)

        return instance


class MeProfileSerializer(AvatarFieldsMixin, serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    effective_role = serializers.SerializerMethodField()
    tenant_is_suspended = serializers.BooleanField(source="tenant.is_suspended", read_only=True, allow_null=True)
    tenant_is_verified = serializers.BooleanField(source="tenant.is_verified", read_only=True, allow_null=True)
    staff_profile = serializers.SerializerMethodField()
    parent_profile = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()
    editable_fields = serializers.SerializerMethodField()
    admin_only_fields = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "phone",
            "avatar", "avatar_url", "has_avatar",
            "role", "effective_role", "tenant", "is_email_verified",
            "must_change_password",
            "tenant_is_verified", "tenant_is_suspended",
            "staff_profile", "parent_profile", "profile_completion",
            "editable_fields", "admin_only_fields",
        ]

    def get_effective_role(self, obj: User) -> str:
        from apps.core.constants import normalize_role
        return normalize_role(obj.role)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        try:
            from apps.accounts.dual_roles import ensure_primary_assignment, role_payload

            ensure_primary_assignment(instance)
            dual = role_payload(instance)
            data["available_roles"] = dual["available_roles"]
            data["can_switch_role"] = dual["can_switch_role"]
            data["primary_role"] = dual["primary_role"]
            data["active_role"] = dual["active_role"]
            data["role_labels"] = dual["role_labels"]
        except Exception:
            pass
        return data

    def get_staff_profile(self, obj: User) -> dict | None:
        try:
            staff = obj.staff_profile
        except Exception:
            staff = None
        if not staff or getattr(staff, "is_deleted", False):
            return None
        return StaffSelfProfileSerializer(staff).data

    def get_parent_profile(self, obj: User) -> dict | None:
        try:
            parent = obj.parent_profile
        except Exception:
            parent = None
        if not parent or getattr(parent, "is_deleted", False):
            return None
        return ParentSelfProfileSerializer(parent).data

    def get_profile_completion(self, obj: User) -> dict:
        return build_profile_completion(obj)

    def get_editable_fields(self, obj: User) -> dict:
        fields = {"user": sorted(get_user_self_editable_fields(obj))}
        try:
            if obj.staff_profile:
                fields["staff_profile"] = sorted(STAFF_SELF_EDITABLE)
        except Exception:
            pass
        try:
            if obj.parent_profile:
                fields["parent_profile"] = sorted(PARENT_SELF_EDITABLE)
        except Exception:
            pass
        return fields

    def get_admin_only_fields(self, obj: User) -> dict:
        from apps.accounts.profile_service import STAFF_ADMIN_ONLY, PARENT_ADMIN_ONLY

        result = {"user": ["email", "role", "is_active"]}
        try:
            if obj.staff_profile:
                result["staff_profile"] = sorted(STAFF_ADMIN_ONLY)
        except Exception:
            pass
        try:
            if obj.parent_profile:
                result["parent_profile"] = sorted(PARENT_ADMIN_ONLY)
        except Exception:
            pass
        return result