from typing import List

from fastapi import APIRouter, Depends, Response, Security, status
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import resource_crud
from literature.routers.authentication import auth
from literature.schemas import (NoteSchemaShow, ResourceSchemaPost,
                                ResourceSchemaShow, ResourceSchemaUpdate,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/resource",
    tags=['Resource']
)


get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)


@router.post('/',
             status_code=status.HTTP_201_CREATED,

             response_model=str)
def create(request: ResourceSchemaPost,
           user: OktaUser = db_user,
           db: Session = db_session):
    set_global_user_id(db, user.id)
    return resource_crud.create(db, request)


@router.delete('/{curie}',

               status_code=status.HTTP_204_NO_CONTENT)
def destroy(curie: str,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    resource_crud.destroy(db, curie)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{curie}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
def patch(curie: str,
          request: ResourceSchemaUpdate,
          user: OktaUser = db_user,
          db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return resource_crud.patch(db, curie, patch)


@router.get('/{curie}/notes',
            status_code=200,
            response_model=List[NoteSchemaShow])
def show_notes(curie: str,
               db: Session = db_session):
    return resource_crud.show_notes(db, curie)


@router.get('/{curie}',
            status_code=200,
            response_model=ResourceSchemaShow)
def show(curie: str,
         db: Session = db_session):
    return resource_crud.show(db, curie)


@router.get('/{curie}/versions',
            status_code=200)
def show_versions(curie: str,
                  db: Session = db_session):
    return resource_crud.show_changesets(db, curie)
