from django.contrib import admin
from apps.transport.models import Driver, Route, StudentTransport, Vehicle
admin.site.register(Vehicle)
admin.site.register(Driver)
admin.site.register(Route)
admin.site.register(StudentTransport)
