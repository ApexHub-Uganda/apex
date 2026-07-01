from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.library.views import BookViewSet, BorrowRecordViewSet

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("borrows", BorrowRecordViewSet, basename="borrow")

urlpatterns = [path("", include(router.urls))]
