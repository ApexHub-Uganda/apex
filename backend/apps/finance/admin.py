from django.contrib import admin
from apps.finance.models import AccountingEntry, FeePayment, FeeStructure, Invoice
admin.site.register(FeeStructure)
admin.site.register(FeePayment)
admin.site.register(Invoice)
admin.site.register(AccountingEntry)
