from rest_framework import serializers
from apps.payroll.models import PayrollRun, Payslip, SalaryStructure
class SalaryStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
class PayslipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payslip
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "created_by", "updated_by", "is_deleted"]
