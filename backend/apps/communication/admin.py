from django.contrib import admin
from apps.communication.models import Announcement, Broadcast, EmailMessage, Notification, SMSMessage, SupportTicket
for m in [Announcement, Notification, SMSMessage, EmailMessage, Broadcast, SupportTicket]:
    admin.site.register(m)
