from fastapi import APIRouter, Depends, Response, Security, status
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import reference_comment_and_correction_crud
from literature.routers.authentication import auth
from literature.schemas import (ReferenceCommentAndCorrectionSchemaPatch,
                                ReferenceCommentAndCorrectionSchemaPost,
                                ReferenceCommentAndCorrectionSchemaShow,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/reference_comment_and_correction",
    tags=['Reference Comment and Correction']
)


get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=str)
def create(request: ReferenceCommentAndCorrectionSchemaPost,
           user: OktaUser = db_user,
           db: Session = db_session):
    set_global_user_id(db, user.id)
    return reference_comment_and_correction_crud.create(db, request)


@router.delete('/{reference_comment_and_correction_id}',
               status_code=status.HTTP_204_NO_CONTENT)
def destroy(reference_comment_and_correction_id: int,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    reference_comment_and_correction_crud.destroy(db, reference_comment_and_correction_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{reference_comment_and_correction_id}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
async def patch(reference_comment_and_correction_id: int,
                request: ReferenceCommentAndCorrectionSchemaPatch,
                user: OktaUser = db_user,
                db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return reference_comment_and_correction_crud.patch(db, reference_comment_and_correction_id, patch)


@router.get('/{reference_comment_and_correction_id}',
            response_model=ReferenceCommentAndCorrectionSchemaShow,
            status_code=200)
def show(reference_comment_and_correction_id: int,
         db: Session = db_session):
    return reference_comment_and_correction_crud.show(db, reference_comment_and_correction_id)


@router.get('/{reference_comment_and_correction_id}/versions',
            status_code=200)
def show_versions(reference_comment_and_correction_id: int,
                  db: Session = db_session):
    return reference_comment_and_correction_crud.show_changesets(db, reference_comment_and_correction_id)
