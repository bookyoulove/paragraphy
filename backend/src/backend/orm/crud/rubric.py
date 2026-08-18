from uuid import UUID

from sqlmodel import select

from backend.orm.crud._base import CRUDBase
from backend.orm.models import Rubrics
from backend.schema.rubric import RubricCreate, RubricUpdate


class CRUDRubric(CRUDBase[Rubrics, RubricCreate, RubricUpdate]):
    def get_by_problem(self, problem_id: UUID) -> list[Rubrics]:
        stmt = select(self.model).where(self.model.problem_id == problem_id)
        return list(self.session.exec(stmt).all())

    def delete_by_problem(self, problem_id: UUID) -> None:
        rubrics = self.get_by_problem(problem_id)
        for rubric in rubrics:
            self.session.delete(rubric)
        self.session.commit()
