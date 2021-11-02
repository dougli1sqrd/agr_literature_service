import pytest
# NOTE: updtae here not patch?
from literature.crud.resource_descriptor_crud import show, update
from sqlalchemy import create_engine
from sqlalchemy import MetaData

from literature.models import (
    Base, ResourceDescriptorModel
)
from literature.database.config import SQLALCHEMY_DATABASE_URL
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
metadata = MetaData()

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"options": "-c timezone=utc"})
SessionLocal = sessionmaker(bind=engine, autoflush=True)
db = SessionLocal()

# Add tables/schema if not already there.
Base.metadata.create_all(engine)

# Exit if this is not a test database, Exit.
if "literature-test" not in SQLALCHEMY_DATABASE_URL:
    exit(-1)


def test_get_res_des():
    res = show(db)
    assert res
