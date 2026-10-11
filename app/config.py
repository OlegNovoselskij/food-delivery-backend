import os

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_PUBLIC_ENDPOINT_URL = os.getenv("S3_PUBLIC_ENDPOINT_URL", S3_ENDPOINT_URL)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "rustfsadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "rustfsadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "courses")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

UPLOAD_URL_TTL_SECONDS = 15 * 60
UPLOAD_TICKET_TTL_SECONDS = 6 * 60 * 60
DOWNLOAD_URL_TTL_SECONDS = 60 * 60

VIDEO_MAX_BYTES = 2 * 1024**3
MATERIAL_MAX_BYTES = 100 * 1024**2

VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
MATERIAL_TYPES = {
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379/0")

WS_TICKET_TTL_SECONDS = 60
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]

PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
CERTIFICATE_FONT_PATH = os.getenv("CERTIFICATE_FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
CERTIFICATE_FONT_BOLD_PATH = os.getenv(
    "CERTIFICATE_FONT_BOLD_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
)
