from django.contrib import admin

from apps.platform.models import (
    APIKey, CallSetting, EmailSetting, GlobalSetting, PlatformBroadcast, PlatformMetrics,
    PlatformNews, PlatformNotification, PlatformNotificationReceipt, SMSSetting, SystemHealthLog,
)

for model in [
    GlobalSetting, EmailSetting, SMSSetting, CallSetting, APIKey,
    PlatformNews, PlatformBroadcast, PlatformNotification, PlatformNotificationReceipt,
    SystemHealthLog, PlatformMetrics,
]:
    admin.site.register(model)