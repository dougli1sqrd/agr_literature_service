"""
file_model.py
============
"""

from datetime import datetime
from typing import Dict

from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Enum, ForeignKey,
                        Integer, String)
from sqlalchemy.orm import relationship

from literature.database.base import Base
from literature.schemas import FileCategories


class FileModel(Base):
    __tablename__ = "files"
    __versioned__: Dict = {}

    file_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    s3_filename = Column(
        String,
        unique=True,
        nullable=False
    )

    reference_id = Column(
        Integer,
        ForeignKey("references.reference_id",
                   ondelete="CASCADE"),
        index=True
    )

    reference = relationship(
        "ReferenceModel",
        back_populates="files"
    )

    extension = Column(
        String,
        nullable=True
    )

    language = Column(
        String
    )

    content_type = Column(
        String,
        nullable=True
    )

    category = Column(
        Enum(FileCategories),
        nullable=True
    )

    folder = Column(
        String(),
        unique=False,
        nullable=False
    )

    md5sum = Column(
        String(),
        unique=False,
        nullable=False,
        index=True
    )

    size = Column(
        Integer,
        nullable=False
    )

    display_name = Column(
        String(),
        unique=False,
        nullable=True
    )

    upload_date = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    public = Column(
        Boolean,
        nullable=False
    )

    mod_submitted = Column(
        String,
        nullable=True
    )

    mods_permitted = Column(
        ARRAY(String()),
        nullable=True
    )

    institutes_permitted = Column(
        ARRAY(String()),
        nullable=True
    )
