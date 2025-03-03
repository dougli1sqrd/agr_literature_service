from typing import List

from botocore.client import BaseClient
from fastapi import APIRouter, Depends, Response, Security, status
from fastapi.responses import StreamingResponse
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import file_crud
from literature.deps import s3_auth
from literature.routers.authentication import auth
from literature.schemas import (FileSchemaShow, FileSchemaUpdate,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/file",
    tags=['File']
)


get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)
s3_session = Depends(s3_auth)


@router.delete('/{filename}',
               status_code=status.HTTP_204_NO_CONTENT)
def destroy(filename: str,
            s3: BaseClient = s3_session,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    file_crud.destroy(db, s3, filename)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{filename}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
async def update(filename: str,
                 request: FileSchemaUpdate,
                 user: OktaUser = db_user,
                 db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return file_crud.patch(db, filename, patch)


@router.get('/{filename}',
            response_model=FileSchemaShow,
            status_code=200)
def show(filename: str,
         db: Session = db_session):
    return file_crud.show(db, filename)


@router.get('/by_md5sum/{md5sum}',
            response_model=List[FileSchemaShow],
            status_code=200)
def show_md5(md5sum: str,
             db: Session = db_session):
    return file_crud.show_by_md5sum(db, md5sum)


@router.get('/download/{filename}',
            status_code=200)
async def show_download(filename: str,
                        s3: BaseClient = s3_session,
                        user: OktaUser = db_user,
                        db: Session = db_session):
    [file_stream, media_type] = file_crud.download(db, s3, filename)

    return StreamingResponse(file_stream, media_type=media_type)


@router.get('/{filename}/versions',
            status_code=200)
def show_versions(filename: str,
                  db: Session = db_session):
    return file_crud.show_changesets(db, filename)
