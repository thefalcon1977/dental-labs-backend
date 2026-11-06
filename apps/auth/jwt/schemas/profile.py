"""Schemas for local user profiles."""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

PHONE_PATTERN = r"^\+?[0-9 ()-]{6,32}$"
LOCALE_PATTERN = r"^[A-Za-z]{2,3}([-_][A-Za-z0-9]{2,8})*$"


class ProfileUpdate(BaseModel):
    """Partial profile update; only fields sent are changed, ``null`` clears one."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "phone_number": "+98 912 000 0000",
                "avatar_url": "https://cdn.example.com/avatars/jane.png",
                "bio": "Backend engineer",
                "birth_date": "1990-04-21",
                "locale": "en-US",
                "timezone": "Asia/Tehran",
            }
        },
    )

    phone_number: str | None = Field(None, pattern=PHONE_PATTERN)
    avatar_url: HttpUrl | None = Field(None, max_length=500)
    bio: str | None = Field(None, max_length=500)
    birth_date: date | None = None
    locale: str | None = Field(None, max_length=16, pattern=LOCALE_PATTERN)
    timezone: str | None = Field(None, max_length=64)

    @field_validator("birth_date")
    @classmethod
    def birth_date_not_in_future(cls, value: date | None) -> date | None:
        """Reject birth dates after today.

        Args:
            value: Submitted birth date.

        Returns:
            The unchanged value.

        Raises:
            ValueError: If the date is in the future.
        """
        if value is not None and value > date.today():
            raise ValueError("birth_date cannot be in the future")
        return value

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        """Require an IANA timezone name such as ``Europe/Berlin``.

        Args:
            value: Submitted timezone.

        Returns:
            The unchanged value.

        Raises:
            ValueError: If the timezone is unknown.
        """
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError("timezone must be a valid IANA name") from e
        return value


class ProfileResponse(BaseModel):
    """Current user's profile."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    phone_number: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    birth_date: date | None = None
    locale: str | None = None
    timezone: str | None = None
    updated_at: datetime | None = None
