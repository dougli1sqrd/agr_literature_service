"""
person_orcid_cross_reference_link_model.py
==========================================
"""

from sqlalchemy import Column, ForeignKey, Integer, String

from literature.database.base import Base


class PersonOrcidCrossReferenceLinkModel(Base):
    __tablename__ = "person_orcid_cross_reference_link"

    person_id = Column(
        Integer,
        ForeignKey("people.person_id"),
        primary_key=True
    )

    cross_reference_curie = Column(
        String,
        ForeignKey("cross_references.curie"),
        primary_key=True
    )
