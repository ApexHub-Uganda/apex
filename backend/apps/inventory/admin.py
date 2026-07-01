from django.contrib import admin
from apps.inventory.models import Item, Procurement, StockMovement
admin.site.register(Item)
admin.site.register(StockMovement)
admin.site.register(Procurement)
