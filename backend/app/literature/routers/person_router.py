from fastapi import APIRouter, Depends, Response, Security, status
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import person_crud
from literature.routers.authentication import auth
from literature.schemas import (PersonSchemaCreate, PersonSchemaShow,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/person",
    tags=['Person']
)


get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=PersonSchemaShow)
def create(request: PersonSchemaCreate,
           user: OktaUser = db_user,
           db: Session = db_session):
    set_global_user_id(db, user.id)
    return person_crud.create(db, request)


@router.delete('/{person_id}',
               status_code=status.HTTP_204_NO_CONTENT)
def destroy(person_id: int,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    person_crud.destroy(db, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{person_id}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
async def patch(person_id: int,
                request: PersonSchemaCreate,
                user: OktaUser = db_user,
                db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return person_crud.patch(db, person_id, patch)


@router.get('/{person_id}',
            status_code=200)
def show(person_id: int,
         db: Session = db_session):
    return person_crud.show(db, person_id)


@router.get('/{person_id}/versions',
            status_code=200)
def show_versions(person_id: int,
                  db: Session = db_session):
    return person_crud.show_changesets(db, person_id)
