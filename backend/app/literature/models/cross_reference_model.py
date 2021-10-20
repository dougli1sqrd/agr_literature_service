from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import ARRAY

from sqlalchemy.orm import relationship

from literature.database.base import Base


class CrossReferenceModel(Base):
    __tablename__ = 'cross_references'
    __versioned__ = {}

    curie = Column(
        String,
        primary_key=True
    )

    is_obsolete = Column(
        Boolean,
        unique=False,
        default=False
    )

    reference_id = Column(
        Integer,
        ForeignKey('references.reference_id'),
        index=True
    )

    reference = relationship(
        'ReferenceModel',
        back_populates="cross_references"
    )

    resource_id = Column(
        Integer,
        ForeignKey('resources.resource_id'),
        index=True
    )

    resource = relationship(
        'ResourceModel',
        back_populates='cross_references'
    )

    authors = relationship(
        'AuthorModel',
        back_populates='orcid_cross_reference'
    )

    editors = relationship(
        'EditorModel',
        back_populates='orcid_cross_reference'
    )

    people = relationship(
        'PersonModel',
        secondary='person_orcid_cross_reference_link'
    )

    pages = Column(
        ARRAY(String()),
        nullable=True
    )

    def __str__(self):
        """Over write the default output."""
        return "CrossReference: curie='{}' is_obsolete='{}' reference_id='{}', resource_id='{}' pages={}".\
            format(self.curie, self.is_obsolete, self.reference_id, self.resource_id, self.pages)
