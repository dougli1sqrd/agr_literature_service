"""
author_crud.py
==============
"""

from datetime import datetime

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from literature.crud.reference_resource import add, create_obj, stripout
from literature.models import (
    AuthorModel,
    CrossReferenceModel,
    ReferenceModel,
    ResourceModel,
)
from literature.schemas import AuthorSchemaCreate, AuthorSchemaPost


def create(db: Session, author: AuthorSchemaPost):
    """
    Create a new author
    :param db:
    :param author:
    :return:
    """

    author_data = jsonable_encoder(author)

    orcid = None
    if "orcid" in author_data:
        orcid = author_data["orcid"]
        del author_data["orcid"]

    author_model = create_obj(db, AuthorModel, author_data)  # type: AuthorModel
    if orcid:
        cross_reference_obj = db.query(CrossReferenceModel).filter(CrossReferenceModel.curie == orcid).first()
        if not cross_reference_obj:
            cross_reference_obj = CrossReferenceModel(curie=orcid)
            db.add(cross_reference_obj)
        author_model.orcid_cross_reference = cross_reference_obj

    db.add(author_model)
    db.commit()
    db.refresh(author_model)

    return author_model.author_id


def destroy(db: Session, author_id: int):
    """

    :param db:
    :param author_id:
    :return:
    """

    author = db.query(AuthorModel).filter(AuthorModel.author_id == author_id).first()
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Author with author_id {author_id} not found")
    db.delete(author)
    db.commit()

    return None


def patch(db: Session, author_id: int, author_patch: AuthorSchemaCreate) -> dict:
    """
    Update an author
    :param db:
    :param author_id:
    :param author_patch:
    :return:
    """

    author_data = jsonable_encoder(author_patch)

    if "resource_curie" in author_data and author_data["resource_curie"] and \
            "reference_curie" in author_data and author_data["reference_curie"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Only supply either resource_curie or reference_curie")

    author_db_obj = db.query(AuthorModel).filter(AuthorModel.author_id == author_id).first()
    if not author_db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Author with author_id {author_id} not found")
    res_ref = stripout(db, author_data, non_fatal=True)
    add(res_ref, author_db_obj)

    for field, value in author_data.items():
        if field == "orcid" and value:
            orcid = value
            cross_reference_obj = db.query(CrossReferenceModel).filter(CrossReferenceModel.curie == orcid).first()
            if not cross_reference_obj:
                cross_reference_obj = CrossReferenceModel(curie=orcid)
                db.add(cross_reference_obj)
            author_db_obj.orcid_cross_reference = cross_reference_obj
        else:
            setattr(author_db_obj, field, value)

    author_db_obj.dateUpdated = datetime.utcnow()
    db.commit()

    return {"message": "updated"}


def show(db: Session, author_id: int):
    """

    :param db:
    :param author_id:
    :return:
    """

    author = db.query(AuthorModel).filter(AuthorModel.author_id == author_id).first()
    author_data = jsonable_encoder(author)

    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Author with the author_id {author_id} is not available")

    if author_data["resource_id"]:
        author_data["resource_curie"] = db.query(ResourceModel.curie).filter(ResourceModel.resource_id == author_data["resource_id"]).first()
    del author_data["resource_id"]

    if author_data["reference_id"]:
        author_data["reference_curie"] = db.query(ReferenceModel.curie).filter(ReferenceModel.reference_id == author_data["reference_id"]).first()
    del author_data["reference_id"]

    return author_data


def show_changesets(db: Session, author_id: int):
    author = db.query(AuthorModel).filter(AuthorModel.author_id == author_id).first()
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Author with the author_id {author_id} is not available")

    history = []
    for version in author.versions:
        tx = version.transaction
        history.append({"transaction": {"id": tx.id,
                                        "issued_at": tx.issued_at,
                                        "user_id": tx.user_id},
                        "changeset": version.changeset})

    return history
