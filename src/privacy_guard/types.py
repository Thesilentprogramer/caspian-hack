from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Category(StrEnum):
    EMAIL = "EMAIL"
    IP_ADDRESS = "IP_ADDRESS"
    CREDIT_CARD = "CREDIT_CARD"
    API_KEY = "API_KEY"
    PHONE = "PHONE"
    PERSON = "PERSON"
    ORG = "ORG"


# Higher wins when two Sensitive Spans overlap.
CATEGORY_PRIORITY: dict[Category, int] = {
    Category.API_KEY: 100,
    Category.CREDIT_CARD: 90,
    Category.EMAIL: 80,
    Category.IP_ADDRESS: 70,
    Category.PHONE: 60,
    Category.PERSON: 50,
    Category.ORG: 50,
}


@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int
    value: str
    category: Category

    def overlaps(self, other: Span) -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True, slots=True)
class SanitizeResult:
    safe_text: str
    mapping_id: str


class MappingExpired(LookupError):
    """The Mapping Id is unknown or its TTL has elapsed."""


class MappingError(Exception):
    """The Mapping store refused an operation."""
