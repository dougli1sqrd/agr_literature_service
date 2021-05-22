from typing import List
from typing import Optional

from pydantic import BaseModel


class ModReferenceType(BaseModel):
    reference_type: str
    source: Optional[str] = None

    class Config():
        orm_mode = True
        extra = "forbid"


class ModReferenceTypeShow(ModReferenceType):
    mod_reference_type_id = int

    class Config():
        orm_mode = True
        extra = "forbid"
