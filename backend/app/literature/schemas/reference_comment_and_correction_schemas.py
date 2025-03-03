from typing import Optional

from pydantic import BaseModel, validator

from literature.schemas import ReferenceCommentAndCorrectionType


class ReferenceCommentAndCorrectionSchemaPost(BaseModel):
    reference_curie_from: str
    reference_curie_to: str
    reference_comment_and_correction_type: ReferenceCommentAndCorrectionType

    @validator('reference_curie_from')
    def from_must_be_alliance_reference_curie(cls, v):
        if not v.startswith("AGR:AGR-Reference-"):
            raise ValueError('must start with AGR:AGR-Reference-<number>')
        return v

    @validator('reference_curie_to')
    def to_must_be_alliance_reference_curie(cls, v):
        if not v.startswith("AGR:AGR-Reference-"):
            raise ValueError('must start with AGR:AGR-Reference-<number>')
        return v

    class Config():
        orm_mode = True
        extra = "forbid"


class ReferenceCommentAndCorrectionSchemaShow(ReferenceCommentAndCorrectionSchemaPost):
    reference_comment_and_correction_id: int

    class Config():
        orm_mode = True
        extra = "forbid"


class ReferenceCommentAndCorrectionSchemaPatch(BaseModel):
    reference_curie_from: Optional[str] = None
    reference_curie_to: Optional[str] = None
    reference_comment_and_correction_type: Optional[ReferenceCommentAndCorrectionType] = None

    class Config():
        orm_mode = True
        extra = "forbid"


class ReferenceCommentAndCorrectionSchemaRelated(BaseModel):
    reference_comment_and_correction_id: Optional[int] = None
    reference_curie_from: Optional[str] = None
    reference_curie_to: Optional[str] = None
    reference_comment_and_correction_type: Optional[ReferenceCommentAndCorrectionType] = None

    class Config():
        orm_mode = True
        extra = "forbid"
