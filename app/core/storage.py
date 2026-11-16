import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
import logging

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


# Voice, Image Or Video to Cloudinary for Querry

logger = logging.getLogger(__name__)

# kind → (allowed content types, Cloudinary resource type). Cloudinary stores audio as "video".
MEDIA_RULES = {
    "image": ({"image/jpeg", "image/png", "image/webp"}, "image"),
    "voice": ({"audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/aac", "audio/ogg", "audio/wav", "audio/webm"}, "video"),
    "video": ({"video/mp4", "video/quicktime", "video/webm"}, "video"),
}
MAX_MEDIA_BYTES = 4 * 1024 * 1024  # Vercel rejects request bodies over ~4.5 MB


async def upload_media(file: UploadFile, folder: str, kind: str) -> str:
    """Validate and upload one image / voice note / video. Returns its HTTPS URL."""
    allowed, resource_type = MEDIA_RULES[kind]
    if file.content_type not in allowed:
        raise HTTPException(400, {kind: [f"Unsupported {kind} type: {file.content_type}."]})

    data = await file.read(MAX_MEDIA_BYTES + 1)
    if len(data) > MAX_MEDIA_BYTES:
        raise HTTPException(400, {kind: ["File must be 4 MB or smaller."]})

    try:
        result = await run_in_threadpool(
            cloudinary.uploader.upload, data, folder=folder, resource_type=resource_type
        )
    except Exception as exc:
        logger.exception("Cloudinary %s upload failed", kind)
        raise HTTPException(502, {kind: ["Upload failed, please try again."]}) from exc
    return result["secure_url"]
