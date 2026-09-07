"""Profile picture upload, validation, and URL resolution."""
from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserProfilePicture

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile
    from rest_framework.request import Request

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _max_avatar_bytes() -> int:
    return int(getattr(settings, "MAX_UPLOAD_SIZE_MB", 10)) * 1024 * 1024


def avatar_upload_path(user_id: uuid.UUID, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        ext = ".jpg"
    return f"{user_id}{ext}"


def validate_avatar_file(uploaded: UploadedFile) -> None:
    if not uploaded:
        raise ValueError("No image file provided.")
    content_type = (getattr(uploaded, "content_type", "") or "").lower()
    ext = os.path.splitext(getattr(uploaded, "name", "") or "")[1].lower()
    if content_type not in ALLOWED_AVATAR_CONTENT_TYPES and ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError("Unsupported image type. Use JPEG, PNG, WebP, or GIF.")
    size = getattr(uploaded, "size", 0) or 0
    if size > _max_avatar_bytes():
        raise ValueError(
            f"Image exceeds maximum size of {getattr(settings, 'MAX_UPLOAD_SIZE_MB', 10)} MB.",
        )


def resolve_avatar_url(user: User, request: Request | None = None) -> str | None:
    url: str | None = None
    updated_at = getattr(user, "avatar_updated_at", None)

    try:
        record = user.profile_picture
        if record and record.image:
            url = record.image.url
            updated_at = getattr(record, "updated_at", None) or updated_at
    except UserProfilePicture.DoesNotExist:
        pass

    if not url and user.avatar:
        url = user.avatar.url

    if not url:
        return None

    # Append cache-busting timestamp so new uploads display immediately in client browsers
    if updated_at:
        timestamp = int(updated_at.timestamp())
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}v={timestamp}"

    if request is not None and not url.startswith("http"):
        return request.build_absolute_uri(url)
    return url


def user_has_avatar(user: User) -> bool:
    try:
        record = user.profile_picture
        return bool(record and record.image)
    except UserProfilePicture.DoesNotExist:
        return bool(user.avatar)


def _delete_file_field(file_field) -> None:
    if file_field and getattr(file_field, "name", None):
        file_field.delete(save=False)


def _sync_staff_photo(user: User, image_file) -> None:
    try:
        staff = user.staff_profile
    except Exception:
        return
    if not staff:
        return
    _delete_file_field(staff.photo)
    image_file.seek(0)
    ext = os.path.splitext(image_file.name)[1].lower() or ".jpg"
    staff.photo.save(f"{staff.id}{ext}", ContentFile(image_file.read()), save=True)


@transaction.atomic
def upload_user_avatar(user: User, uploaded: UploadedFile) -> UserProfilePicture:
    validate_avatar_file(uploaded)

    try:
        record = user.profile_picture
    except UserProfilePicture.DoesNotExist:
        record = None

    if record is None:
        record = UserProfilePicture(user=user)

    _delete_file_field(record.image)
    _delete_file_field(user.avatar)

    uploaded.seek(0)
    ext = os.path.splitext(uploaded.name or "")[1].lower() or ".jpg"
    filename = avatar_upload_path(user.id, f"avatar{ext}")
    record.image.save(filename, uploaded, save=False)
    record.original_filename = os.path.basename(uploaded.name or filename)
    record.file_size = uploaded.size or 0
    record.content_type = (getattr(uploaded, "content_type", "") or "image/jpeg").lower()
    record.save()

    uploaded.seek(0)
    user.avatar.save(filename, ContentFile(uploaded.read()), save=False)
    user.avatar_updated_at = timezone.now()
    user.save(update_fields=["avatar", "avatar_updated_at", "updated_at"])

    uploaded.seek(0)
    _sync_staff_photo(user, uploaded)

    return record


@transaction.atomic
def delete_user_avatar(user: User) -> None:
    try:
        record = user.profile_picture
    except UserProfilePicture.DoesNotExist:
        record = None

    if record:
        _delete_file_field(record.image)
        record.delete()

    if user.avatar:
        _delete_file_field(user.avatar)
        user.avatar = None
        user.avatar_updated_at = None
        user.save(update_fields=["avatar", "avatar_updated_at", "updated_at"])

    try:
        staff = user.staff_profile
    except Exception:
        staff = None
    if staff and staff.photo:
        _delete_file_field(staff.photo)
        staff.photo = None
        staff.save(update_fields=["photo", "updated_at"])