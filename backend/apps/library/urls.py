from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.library.report_views import LibraryReportsView
from apps.library.views import BookViewSet, BorrowRecordViewSet

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("borrows", BorrowRecordViewSet, basename="borrow")

urlpatterns = [
    path("reports/", LibraryReportsView.as_view(), name="library-reports"),
    path("", include(router.urls)),
]
