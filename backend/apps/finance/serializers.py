from rest_framework import serializers
from apps.finance.models import AccountingEntry, FeePayment, FeeStructure, Invoice
class FeeStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class FeePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeePayment
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class InvoiceSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    def get_balance(self, obj):
        return obj.total_amount - obj.amount_paid
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class AccountingEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingEntry
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
