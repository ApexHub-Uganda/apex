from rest_framework import serializers

from apps.finance.models import (
    AccountingEntry,
    AccountingPeriod,
    Budget,
    FeeCategory,
    FeeDiscount,
    FeePayment,
    FeeStructure,
    FinanceNote,
    FinancialAccount,
    Invoice,
    MiscIncome,
    Refund,
    StudentFeeBalance,
)

READ_ONLY = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]


class FeeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCategory
        fields = "__all__"
        read_only_fields = READ_ONLY


class FeeStructureSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="school_class.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)

    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = READ_ONLY


class StudentFeeBalanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    class_name = serializers.CharField(source="student.school_class.name", read_only=True, allow_null=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = StudentFeeBalance
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
        read_only_fields = READ_ONLY + ["approved_by", "approved_at"]

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


class FeeDiscountSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = FeeDiscount
        fields = "__all__"
        read_only_fields = READ_ONLY + ["approved_by", "approved_at"]


class RefundSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="fee_payment.student.full_name", read_only=True)

    class Meta:
        model = Refund
        fields = "__all__"
        read_only_fields = READ_ONLY + ["approved_by", "approved_at"]


class MiscIncomeSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True, allow_null=True)

    class Meta:
        model = MiscIncome
        fields = "__all__"
        read_only_fields = READ_ONLY


class FinanceNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = FinanceNote
        fields = "__all__"
        read_only_fields = READ_ONLY

    def get_author_name(self, obj) -> str:
        return obj.author.full_name if obj.author else ""


class FinancialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialAccount
        fields = "__all__"
        read_only_fields = READ_ONLY


class BudgetSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True, allow_null=True)

    class Meta:
        model = Budget
        fields = "__all__"
        read_only_fields = READ_ONLY


class AccountingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingPeriod
        fields = "__all__"
        read_only_fields = READ_ONLY + ["closed_by", "closed_at"]


class AccountingEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingEntry
        fields = "__all__"
        read_only_fields = READ_ONLY + ["approved_by"]