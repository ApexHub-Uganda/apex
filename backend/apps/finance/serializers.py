from rest_framework import serializers

from apps.finance.models import AccountingEntry, FeePayment, FeeStructure, Invoice


READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class FeeStructureSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = READ_ONLY


class FeePaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_admission = serializers.CharField(source="student.admission_number", read_only=True)
    fee_name = serializers.CharField(source="fee_structure.name", read_only=True)
    class_name = serializers.CharField(source="student.school_class.name", read_only=True, allow_null=True)

    class Meta:
        model = FeePayment
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_student_name(self, obj) -> str:
        return obj.student.full_name if obj.student else ""


class InvoiceSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    def get_balance(self, obj):
        return obj.total_amount - obj.amount_paid

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = READ_ONLY


class AccountingEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingEntry
        fields = "__all__"
        read_only_fields = READ_ONLY