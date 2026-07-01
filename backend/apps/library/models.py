"""Library models."""
from django.db import models
from apps.core.models import BaseModel

class Book(BaseModel):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, blank=True, db_index=True)
    category = models.CharField(max_length=100, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    shelf_location = models.CharField(max_length=50, blank=True)
    cover_image = models.ImageField(upload_to="library/", blank=True, null=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["tenant", "isbn"])]

class BorrowRecord(BaseModel):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrow_records")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="borrowed_books")
    borrowed_date = models.DateField()
    due_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("borrowed","Borrowed"),("returned","Returned"),("overdue","Overdue"),("lost","Lost")], default="borrowed")
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-borrowed_date"]
