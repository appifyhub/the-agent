from tempfile import NamedTemporaryFile

from pyuploadcare import Uploadcare

from util import log
from util.config import config
from util.error_codes import FILE_UPLOAD_FAILED, MISSING_CONTENT, MISSING_FILENAME
from util.errors import ExternalServiceError, ValidationError


class FileUploader:

    __content: bytes
    __filename: str

    def __init__(
        self,
        content: bytes,
        filename: str,
    ):
        if not content:
            raise ValidationError("Content must be provided", MISSING_CONTENT)
        if not filename:
            raise ValidationError("Filename must be provided", MISSING_FILENAME)
        self.__content = content
        self.__filename = filename
        log.t(f"Ready to upload file! Size: {len(self.__content) / 1024:.2f} KB")

    def execute(self) -> str:
        try:
            log.t("Uploading file now...")
            cdn_base = f"https://{config.uploadcare_cdn_id}.ucarecd.net/"
            uploadcare = Uploadcare(
                public_key = config.uploadcare_public_key,
                secret_key = config.uploadcare_private_key.get_secret_value(),
                cdn_base = cdn_base,
            )
            with NamedTemporaryFile(suffix = self.__filename) as tmp_file:
                tmp_file.write(self.__content)
                tmp_file.flush()
                tmp_file.name = self.__filename
                ucare_file = uploadcare.upload(tmp_file, store = True)
            log.t("File uploaded successfully!")
            file_url = f"{ucare_file.cdn_url}{ucare_file.filename}"
            return file_url
        except Exception as e:
            log.w("File upload failed", e)
            raise ExternalServiceError("File upload failed", FILE_UPLOAD_FAILED) from e
