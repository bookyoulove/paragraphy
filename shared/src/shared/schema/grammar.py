from enum import Enum

from pydantic import BaseModel


class RevisionCategory(Enum):
    UNKNOWN = 0
    GRAMMER = 1
    WORD = 2
    SPACING = 3
    STANDARD = 8
    TYPO = 9
    FOREIGN_WORD = 10
    CONFUSABLE_WORDS = 11
    SENTENCE = 12
    CONFIRM = 13
    THINKING = 14


class Revision(BaseModel):
    revised: str
    score: float
    category: RevisionCategory
    help_id: str


class CustomDictPos(Enum):
    POS_UNK = 0
    POS_NNG = 1
    POS_NNP = 2
    POS_NNG_CARET = 3
    POS_VV = 4
    POS_VA = 5
    POS_MM = 6
    POS_IC = 7


class RevisedBlock(BaseModel):
    origin: str
    revised: str
    revisions: list[Revision]
    nested: list[RevisedBlock]
    lemma: str
    pos: CustomDictPos


class CleanUpPosition(Enum):
    START = 0
    END = 1
    MIDDLE = 2


class CleanUpRange(BaseModel):
    offset: int
    length: int
    position: CleanUpPosition


class RevisedSentence(BaseModel):
    origin: str
    revised: str


class ReviseHelp(BaseModel):
    id: str
    category: RevisionCategory
    comment: str
    examples: list[str]
    rule_article: str


class GrammarResult(BaseModel):
    origin: str
    revised: str
    revised_blocks: list[RevisedBlock]
    whitespace_cleanup_ranges: list[CleanUpRange]
    revised_sentences: list[RevisedSentence]
    helps: dict[str, ReviseHelp]

    language: str
    tokens_count: int
