"""
file_crud.py
===========
"""

import hashlib
import io
import os

from botocore.client import BaseClient
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from literature.config import config
from literature.models import FileModel, ReferenceModel
from literature.s3.delete import delete_file_in_bucket
from literature.s3.download import download_file_from_bucket
from literature.s3.upload import upload_file_to_bucket


def create(db: Session, s3: BaseClient, parent_entity_type : str, curie: str, file_contents: bytes, display_name: str,
           content_type: str) -> str:
    """
    Create a new file in the database and upload it to S3.
    :param db:
    :param s3:
    :param parent_entity_type:
    :param curie:
    :param file_contents:
    :param display_name:
    :param content_type:
    :return:
    """

    _, file_extension = os.path.splitext(display_name)
    bucket_name = "agr-literature"
    md5sum = hashlib.md5(file_contents).hexdigest()
    s3_filename = curie + "-File-" + md5sum + file_extension
    folder = config.ENV_STATE + "/agr/" + curie

    file_data = {"s3_filename": s3_filename,
                 "size": len(file_contents),
                 "content_type": content_type,
                 "md5sum": md5sum,
                 "folder": folder,
                 "display_name": display_name,
                 "extension": file_extension,
                 "public": False
                 }

    if parent_entity_type == 'reference':
        reference = db.query(ReferenceModel).filter(ReferenceModel.curie == curie).first()
        file_data["reference"] = reference
        if not reference:
            HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                          detail=f"Reference with the curie {curie} is not available")

        file_obj = db.query(FileModel).filter(FileModel.md5sum == md5sum,
                                              FileModel.reference_id == reference.reference_id).first()
        if file_obj:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"File with md5sum {md5sum} and Reference Curie {curie} already exists: File ID {file_obj.file_id}")

    upload_obj = upload_file_to_bucket(s3_client=s3,
                                       file_obj=io.BytesIO(file_contents),
                                       bucket=bucket_name,
                                       folder=folder,
                                       object_name=s3_filename)

    if not upload_obj:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unable to upload file to s3: {display_name}")

    file_db_obj = FileModel(**file_data)

    db.add(file_db_obj)
    db.commit()
    db.refresh(file_db_obj)

    return file_db_obj.s3_filename


def destroy(db: Session, s3: BaseClient, filename: str):
    """

    :param db:
    :param s3:
    :param filename:
    :return:
    """

    file_obj = db.query(FileModel).filter(FileModel.s3_filename == filename).first()
    if not file_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"file with name {filename} not found")

    bucket_name = "agr-literature"
    delete_file_in_bucket(s3_client=s3,
                          bucket=bucket_name,
                          folder=file_obj.folder,
                          object_name=filename)

    db.delete(file_obj)
    db.commit()

    return None


def patch(db: Session, filename: str, file_update) -> dict:  #: FileSchemaUpdate):
    """

    :param db:
    :param filename:
    :param file_update:
    :return:
    """

    file_db_obj = db.query(FileModel).filter(FileModel.s3_filename == filename).first()
    if not file_db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File with filename {filename} not found")

    for field, value in file_update.items():
        if field == "reference_curie" and value:
            reference_curie = value
            reference = db.query(ReferenceModel).filter(ReferenceModel.curie == reference_curie).first()
            if not reference:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Reference with curie {reference_curie} does not exist")
            file_db_obj.reference = reference
        else:
            setattr(file_db_obj, field, value)

    db.commit()

    return {"message": "updated"}


def show(db: Session, filename: str):
    """

    :param db:
    :param filename:
    :return:
    """

    file_obj = db.query(FileModel).filter(FileModel.s3_filename == filename).first()

    if not file_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File with the filename {filename} is not available")

    file_data = jsonable_encoder(file_obj)
    del file_data["reference_id"]

    return file_data


def show_by_md5sum(db: Session, md5sum: str):
    """

    :param db:
    :param md5sum:
    :return:
    """

    files_obj = db.query(FileModel).filter(FileModel.md5sum == md5sum).all()

    if not files_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File with the md5sum {md5sum} is not available")

    files_data = []
    for file_obj in files_obj:
        file_data = jsonable_encoder(file_obj)
        del file_data["reference_id"]
        files_data.append(file_data)

    return files_data


def download(db: Session, s3: BaseClient, filename: str):
    """

    :param db:
    :param s3:
    :param filename:
    :return:
    """

    file_obj = db.query(FileModel).filter(FileModel.s3_filename == filename).first()

    if not file_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File with the filename {filename} is not available")

    bucket_name = "agr-literature"

    return [download_file_from_bucket(s3,
                                      bucket_name,
                                      file_obj.folder,
                                      file_obj.s3_filename),
            file_obj.content_type]


def show_changesets(db: Session, filename: str):
    """

    :param db:
    :param filename:
    :return:
    """

    file_obj = db.query(FileModel).filter(FileModel.s3_filename == filename).first()
    if not file_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File with the filename {filename} is not available")

    history = []
    for version in file_obj.versions:
        tx = version.transaction
        history.append({"transaction": {"id": tx.id,
                                        "issued_at": tx.issued_at,
                                        "user_id": tx.user_id},
                        "changeset": version.changeset})

    return history
