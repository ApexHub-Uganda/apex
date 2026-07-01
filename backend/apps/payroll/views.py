from apps.core.permissions import HasRole, TenantActivePermission
from apps.core.constants import UserRole
from apps.core.views import BaseModelViewSet
from apps.payroll.models import PayrollRun, Payslip, SalaryStructure
from apps.payroll.serializers import PayrollRunSerializer, PayslipSerializer, SalaryStructureSerializer

class SalaryStructureViewSet(BaseModelViewSet):
    required_feature_key = "salary_structures"
    queryset = SalaryStructure.objects.select_related("staff")
    serializer_class = SalaryStructureSerializer
    permission_classes = [HasRole([UserRole.HR_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["staff", "is_active"]

class PayrollRunViewSet(BaseModelViewSet):
    required_feature_key = "payroll_runs"
    queryset = PayrollRun.objects.select_related("processed_by")
    serializer_class = PayrollRunSerializer
    permission_classes = [HasRole([UserRole.HR_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["status"]

class PayslipViewSet(BaseModelViewSet):
    required_feature_key = "payslips"
    queryset = Payslip.objects.select_related("payroll_run", "staff")
    serializer_class = PayslipSerializer
    permission_classes = [HasRole([UserRole.HR_OFFICER, UserRole.SCHOOL_ADMIN]), TenantActivePermission]
    filterset_fields = ["payroll_run", "staff", "is_paid"]
