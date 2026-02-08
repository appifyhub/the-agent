from pydantic import BaseModel


class BindLicenseKeyPayload(BaseModel):
    license_key: str
