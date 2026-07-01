from apps.core.permissions import IsStaffMember, TenantActivePermission
from apps.core.views import BaseModelViewSet
from apps.library.models import Book, BorrowRecord
from apps.library.serializers import BookSerializer, BorrowRecordSerializer

class BookViewSet(BaseModelViewSet):
    required_feature_key = "library_management"
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    search_fields = ["title", "author", "isbn"]
    filterset_fields = ["category"]

class BorrowRecordViewSet(BaseModelViewSet):
    required_feature_key = "borrowing"
    queryset = BorrowRecord.objects.select_related("book", "student")
    serializer_class = BorrowRecordSerializer
    permission_classes = [IsStaffMember, TenantActivePermission]
    filterset_fields = ["status", "student", "book"]
