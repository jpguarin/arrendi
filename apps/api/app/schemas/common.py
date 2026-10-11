from typing import Annotated, Any, ClassVar, Self

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints, model_validator

# A short text the owner must fill in, like a name.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


# Only the shape: whether the address exists is found out when a bill bounces.
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]

# Money is whole pesos. `strict` rejects decimals and numbers sent as text.
Pesos = Annotated[int, Field(strict=True, ge=0, le=10**12)]
PositivePesos = Annotated[int, Field(strict=True, gt=0, le=10**12)]


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


# A text the owner may leave empty; an empty field is stored as null.
OptionalText = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None,
    BeforeValidator(_blank_to_none),
]


class PatchModel(BaseModel):
    """Body of a PATCH: only the fields that were sent change.

    Every field has a default so it can be left out, which also lets `null` through.
    `not_nullable` names the fields that can be left out but not cleared.
    """

    not_nullable: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _check_not_nullable(self) -> Self:
        for field in self.not_nullable:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
