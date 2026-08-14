from backend.orm.crud._base import CRUDBase
from backend.orm.models import AnalysisResults
from backend.schema.analysis_result import AnalysisResultCreate, AnalysisResultUpdate


class CRUDAnalysisResult(
    CRUDBase[AnalysisResults, AnalysisResultCreate, AnalysisResultUpdate]
): ...
