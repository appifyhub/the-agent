# Support is based on popularity and support in AI models

KNOWN_IMAGE_FORMATS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
}

SUPPORTED_AUDIO_FORMATS = {
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "mpeg": "video/mpeg",
    "mpga": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "webm": "video/webm",
}

# File extension -> Audio format
EXTENSION_FORMAT_MAP = {
    **{ext: ext for ext in SUPPORTED_AUDIO_FORMATS.keys()},
    "oga": "ogg",
    "ogg": "ogg",
}

# Formats we know how to convert from
CONVERTIBLE_AUDIO_FORMATS = {
    "oga": "audio/ogg",
    "ogg": "audio/ogg",
}

KNOWN_AUDIO_FORMATS = SUPPORTED_AUDIO_FORMATS | CONVERTIBLE_AUDIO_FORMATS

TARGET_AUDIO_FORMAT = "wav"

KNOWN_DOCS_FORMATS = {
    "pdf": "application/pdf",
}

KNOWN_FILE_FORMATS = KNOWN_IMAGE_FORMATS | KNOWN_AUDIO_FORMATS | KNOWN_DOCS_FORMATS
