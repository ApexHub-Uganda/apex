from django.contrib import admin

from apps.platform.models import (
    APIKey, CallSetting, EmailSetting, GlobalSetting, PlatformBroadcast,
    PlatformBroadcastDelivery, PlatformMetrics, PlatformNews, PlatformNotification,
    PlatformNotificationReceipt, SMSSetting, SystemHealthLog, WhatsAppSetting,
)

for model in [
    GlobalSetting, EmailSetting, SMSSetting, WhatsAppSetting, CallSetting, APIKey,
    PlatformNews, PlatformBroadcast, PlatformBroadcastDelivery,
    PlatformNotification, PlatformNotificationReceipt,
    SystemHealthLog, PlatformMetrics,
]:
    admin.site.register(model)