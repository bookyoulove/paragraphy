from uuid import UUID

from sqlmodel import col, select

from backend.orm.crud._base import CRUDBase
from backend.orm.models import Problems
from backend.schema.problem.input import Criteria, ProblemCreate, ProblemUpdate


class CRUDProblem(CRUDBase[Problems, ProblemCreate, ProblemUpdate]):
    def get_criteria(self, user_id: UUID, criteria: Criteria) -> list[Problems]:
        stmt = select(self.model)
        if criteria.created_by_user is None:
            stmt = stmt.where(
                (col(self.model.user_id) == user_id)
                | (col(self.model.created_by_user).is_(False))
            )
        elif criteria.created_by_user:
            stmt = stmt.where(col(self.model.user_id) == user_id)
        else:
            stmt = stmt.where(col(self.model.created_by_user).is_(False))

        if criteria.created_by_user is None or not criteria.created_by_user:
            if criteria.university:
                stmt = stmt.where(
                    (col(self.model.university).is_not(None))
                    & (col(self.model.university).like(f"%{criteria.university}%"))
                )
            if criteria.year:
                stmt = stmt.where(
                    (col(self.model.year).is_not(None))
                    & (self.model.year == criteria.year)
                )

        res = self.session.exec(stmt)
        return list(res.all())

    def get_by_details(
        self,
        title: str,
        university: str | None = None,
        year: int | None = None,
        created_by_user: bool | None = None,
    ) -> Problems | None:
        stmt = select(self.model).where(self.model.title == title)
        if university is not None:
            stmt = stmt.where(self.model.university == university)
        if year is not None:
            stmt = stmt.where(self.model.year == year)
        if created_by_user is not None:
            stmt = stmt.where(self.model.created_by_user == created_by_user)
        return self.session.exec(stmt).first()
