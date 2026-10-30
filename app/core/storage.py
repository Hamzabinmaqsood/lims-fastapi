import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


async def upload_image(file: UploadFile, folder: str) -> str:
    """Validate an image and upload it to Cloudinary. Returns its HTTPS URL."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, {"profile_picture": ["Only JPG, PNG or WEBP images are allowed."]})

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(400, {"profile_picture": ["Image must be 2 MB or smaller."]})

    # The Cloudinary SDK is blocking (sync), so run it in a thread
    # instead of freezing the event loop.
    result = await run_in_threadpool(
        cloudinary.uploader.upload, data, folder=folder, resource_type="image"
    )
    return result["secure_url"]
