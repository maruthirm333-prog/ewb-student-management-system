"""Request and response models with beginner-friendly input validation."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean_optional_text(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


class StudentFields(BaseModel):
    """Fields shared by student create/replace requests."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100, description="Student's full name")
    date_of_birth: date = Field(description="Date of birth in YYYY-MM-DD format")
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    course: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    enrollment_date: date | None = None

    @field_validator("name", mode="before")
    @classmethod
    def name_must_not_be_blank(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Name cannot be blank")
        return value

    @field_validator("email", "phone", "course", "address", mode="before")
    @classmethod
    def trim_optional_text(cls, value: Any) -> Any:
        return clean_optional_text(value)

    @field_validator("email")
    @classmethod
    def email_must_look_valid(cls, value: str | None) -> str | None:
        if value is not None and not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address, for example name@example.com")
        return value

    @model_validator(mode="after")
    def require_contact_method(self) -> "StudentFields":
        if not self.email and not self.phone:
            raise ValueError("Provide at least one contact method: email or phone")
        return self


class StudentCreate(StudentFields):
    """Body for POST /students and full replacement with PUT."""


class StudentUpdate(BaseModel):
    """Body for PATCH /students/{student_id}; every field is optional."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    course: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    enrollment_date: date | None = None

    @field_validator("name", mode="before")
    @classmethod
    def update_name_must_not_be_blank(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Name cannot be blank")
        return value

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def update_date_of_birth_cannot_be_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Date of birth cannot be null")
        return value

    @field_validator("email", "phone", "course", "address", mode="before")
    @classmethod
    def trim_update_text(cls, value: Any) -> Any:
        return clean_optional_text(value)

    @field_validator("email")
    @classmethod
    def update_email_must_look_valid(cls, value: str | None) -> str | None:
        if value is not None and not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address, for example name@example.com")
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "StudentUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class StudentRead(BaseModel):
    """Student object returned by the API."""

    id: int
    name: str
    date_of_birth: date
    email: str | None
    phone: str | None
    course: str | None
    address: str | None
    enrollment_date: date | None
    created_at: str
    updated_at: str


class AskQuestionRequest(BaseModel):
    """Body for the optional local-AI endpoint."""

    question: str = Field(min_length=3, max_length=1000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Question must contain at least 3 non-space characters")
        return value


class AskQuestionResponse(BaseModel):
    answer: str
    model: str
    records_used: int
    note: str
