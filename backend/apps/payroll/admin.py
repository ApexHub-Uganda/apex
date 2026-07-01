from django.contrib import admin
from apps.payroll.models import PayrollRun, Payslip, SalaryStructure
admin.site.register(SalaryStructure)
admin.site.register(PayrollRun)
admin.site.register(Payslip)
