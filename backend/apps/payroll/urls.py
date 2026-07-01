from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payroll.views import SalaryStructureViewSet, PayrollRunViewSet, PayslipViewSet

router = DefaultRouter()
router.register("salary-structures", SalaryStructureViewSet, basename="salary-structure")
router.register("runs", PayrollRunViewSet, basename="payroll-run")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = [path("", include(router.urls))]
