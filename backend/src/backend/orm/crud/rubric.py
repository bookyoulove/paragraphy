from backend.orm.crud._base import CRUDBase
from backend.orm.models import Rubrics
from backend.schema.rubric import RubricCreate, RubricUpdate


class CRUDRubric(CRUDBase[Rubrics, RubricCreate, RubricUpdate]): ...
