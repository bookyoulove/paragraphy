from uuid import UUID

from shared.schema.rubric import Rubric as RubricBase


class RubricPublic(RubricBase):
    id: UUID
