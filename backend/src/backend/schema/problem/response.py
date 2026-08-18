from backend.schema.problem.public import ProblemPublic
from backend.schema.rubric.public import RubricPublic


class ProblemPublicWithRubrics(ProblemPublic):
    rubrics: list[RubricPublic]
