from fastapi import APIRouter, Depends, Response, Security, status
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import reference_manual_term_tag_crud
from literature.routers.authentication import auth
from literature.schemas import (ReferenceManualTermTagSchemaPatch,
                                ReferenceManualTermTagSchemaPost,
                                ReferenceManualTermTagSchemaShow,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/reference_manual_term_tag",
    tags=['Reference Manual Term Tag']
)


get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=str)
def create(request: ReferenceManualTermTagSchemaPost,
           user: OktaUser = db_user,
           db: Session = db_session):
    set_global_user_id(db, user.id)
    return reference_manual_term_tag_crud.create(db, request)


@router.delete('/{reference_manual_term_tag_id}',
               status_code=status.HTTP_204_NO_CONTENT)
def destroy(reference_manual_term_tag_id: int,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    reference_manual_term_tag_crud.destroy(db, reference_manual_term_tag_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{reference_manual_term_tag_id}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
async def patch(reference_manual_term_tag_id: int,
                request: ReferenceManualTermTagSchemaPatch,
                user: OktaUser = db_user,
                db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return reference_manual_term_tag_crud.patch(db, reference_manual_term_tag_id, patch)


@router.get('/{reference_manual_term_tag_id}',
            response_model=ReferenceManualTermTagSchemaShow,
            status_code=200)
def show(reference_manual_term_tag_id: int,
         db: Session = db_session):
    return reference_manual_term_tag_crud.show(db, reference_manual_term_tag_id)


@router.get('/{reference_manual_term_tag_id}/versions',
            status_code=200)
def show_versions(reference_manual_term_tag_id: int,
                  db: Session = db_session):
    return reference_manual_term_tag_crud.show_changesets(db, reference_manual_term_tag_id)
