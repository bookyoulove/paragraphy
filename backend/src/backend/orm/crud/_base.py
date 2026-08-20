from types import get_original_bases
from typing import Annotated, get_args, get_origin
from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

from backend.orm.session import get_session


class CRUDBase[M: SQLModel, C: SQLModel, U: BaseModel]:
    def __init__(self, session: Annotated[Session, Depends(get_session)]):
        self.session = session
        self.model = self._get_model_type()

    @classmethod
    def _get_model_type(cls) -> type[M]:
        for base in get_original_bases(cls):
            if get_origin(base) is CRUDBase:
                args = get_args(base)
                if args and isinstance(args[0], type):
                    return args[0]
        raise TypeError("CRUDBase must be subclassed with a SQLModel type argument.")

    def get(self, id: UUID) -> M | None:
        return self.session.get(self.model, id)

    def get_multi(self, skip: int = 0, limit: int = 100) -> list[M]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.session.exec(stmt).all())

    def create(self, obj_in: C) -> M:
        db_obj = self.model.model_validate(obj_in)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)

        return db_obj

    def create_multi(self, objs_in: list[C]) -> list[M]:
        db_objs = [self.model.model_validate(obj) for obj in objs_in]
        self.session.add_all(db_objs)
        self.session.commit()
        for db_obj in db_objs:
            self.session.refresh(db_obj)
        return db_objs

    def update(self, id: UUID, obj_up: U) -> M | None:
        db_obj = self.session.get(self.model, id)
        if db_obj is None:
            return None
        update_data = obj_up.model_dump(exclude_unset=True)
        db_obj.sqlmodel_update(update_data)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def delete(self, id: UUID):
        db_obj = self.session.get(self.model, id)
        if db_obj is None:
            return
        self.session.delete(db_obj)
        self.session.commit()
