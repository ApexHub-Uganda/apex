from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.communication.views import AnnouncementViewSet, NotificationViewSet, SMSMessageViewSet, EmailMessageViewSet, BroadcastViewSet, SupportTicketViewSet

router = DefaultRouter()
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("sms", SMSMessageViewSet, basename="sms")
router.register("emails", EmailMessageViewSet, basename="email")
router.register("broadcasts", BroadcastViewSet, basename="broadcast")
router.register("support-tickets", SupportTicketViewSet, basename="support-ticket")

urlpatterns = [path("", include(router.urls))]
