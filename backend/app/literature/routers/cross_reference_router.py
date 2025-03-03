from fastapi import APIRouter, Depends, Response, Security, status
from fastapi_okta import OktaUser
from sqlalchemy.orm import Session

from literature import database
from literature.crud import cross_reference_crud
from literature.routers.authentication import auth
from literature.schemas import (CrossReferenceSchema, CrossReferenceSchemaPost,
                                CrossReferenceSchemaUpdate,
                                ResponseMessageSchema)
from literature.user import set_global_user_id

router = APIRouter(
    prefix="/cross_reference",
    tags=['Cross Reference']
)

get_db = database.get_db
db_session: Session = Depends(get_db)
db_user = Security(auth.get_user)


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=str)
def create(request: CrossReferenceSchemaPost,
           user: OktaUser = db_user,
           db: Session = db_session):
    set_global_user_id(db, user.id)
    return cross_reference_crud.create(db, request)


@router.delete('/{curie:path}',
               status_code=status.HTTP_204_NO_CONTENT)
def destroy(curie: str,
            user: OktaUser = db_user,
            db: Session = db_session):
    set_global_user_id(db, user.id)
    cross_reference_crud.destroy(db, curie)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{curie:path}',
              status_code=status.HTTP_202_ACCEPTED,
              response_model=ResponseMessageSchema)
async def patch(curie: str,
                request: CrossReferenceSchemaUpdate,
                user: OktaUser = db_user,
                db: Session = db_session):
    set_global_user_id(db, user.id)
    patch = request.dict(exclude_unset=True)

    return cross_reference_crud.patch(db, curie, patch)


@router.get('/{curie:path}/versions',
            status_code=200)
def show_version(curie: str,
                 db: Session = db_session):
    return cross_reference_crud.show_changesets(db, curie)


@router.get('/{curie:path}',
            response_model=CrossReferenceSchema,
            status_code=200)
def show(curie: str,
         db: Session = db_session):
    return cross_reference_crud.show(db, curie, False)
