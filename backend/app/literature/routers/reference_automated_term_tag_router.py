from fastapi import APIRouter, Depends, Response, Security, status
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import reference_automated_term_tag_crud
from literature.routers.authentication import auth
from literature.schemas import (ReferenceAutomatedTermTagSchemaPatch,
                                ReferenceAutomatedTermTagSchemaPost,
                                ReferenceAutomatedTermTagSchemaShow,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/reference_automated_term_tag",
    tags=['Reference Automated Term Tag']
)


get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=str)
def create(request: ReferenceAutomatedTermTagSchemaPost,
           user: OktaUser = db_user,
           db: Session = db_session):
    set_global_user_id(db, user.id)
    return reference_automated_term_tag_crud.create(db, request)


@router.delete('/{reference_automated_term_tag_id}',
               status_code=status.HTTP_204_NO_CONTENT)
def destroy(reference_automated_term_tag_id: int,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    reference_automated_term_tag_crud.destroy(db, reference_automated_term_tag_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{reference_automated_term_tag_id}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
async def patch(reference_automated_term_tag_id: int,
                request: ReferenceAutomatedTermTagSchemaPatch,
                user: OktaUser = db_user,
                db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return reference_automated_term_tag_crud.patch(db, reference_automated_term_tag_id, patch)


@router.get('/{reference_automated_term_tag_id}',
            response_model=ReferenceAutomatedTermTagSchemaShow,
            status_code=200)
def show(reference_automated_term_tag_id: int,
         db: Session = db_session):
    return reference_automated_term_tag_crud.show(db, reference_automated_term_tag_id)


@router.get('/{reference_automated_term_tag_id}/versions',
            status_code=200)
def show_versions(reference_automated_term_tag_id: int,
                  db: Session = db_session):
    return reference_automated_term_tag_crud.show_changesets(db, reference_automated_term_tag_id)
