from datetime import datetime
import pytz

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ARRAY
from sqlalchemy import Enum

from sqlalchemy.orm import relationship

from literature.database.base import Base

from literature.schemas import TagName
from literature.schemas import TagSource

class MeshDetail(Base):
    __tablename__ = 'Mesh_details'
    __versioned__ = {}

    mesh_detail_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    reference_id = Column(
         Integer,
         ForeignKey('references.reference_id',
                    ondelete='CASCADE')
    )

    reference = relationship(
        'Reference',
        back_populates="mesh_terms"
    )


    heading_term = Column(
        String,
        unique=False,
        nullable=False
    )

    qualifier_term = Column(
        String,
        unique=False,
        nullable=True
    )
