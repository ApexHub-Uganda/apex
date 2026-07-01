from django.contrib import admin
from apps.hostel.models import Allocation, Hostel, Room
admin.site.register(Hostel)
admin.site.register(Room)
admin.site.register(Allocation)
