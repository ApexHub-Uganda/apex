from django.contrib import admin
from apps.library.models import Book, BorrowRecord
admin.site.register(Book)
admin.site.register(BorrowRecord)
