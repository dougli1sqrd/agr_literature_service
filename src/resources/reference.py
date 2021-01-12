import logging
import json

from flask import request
from flask import jsonify

from flask_sqlalchemy import SQLAlchemy
from flask_apispec.views import MethodResource
from flask_apispec.annotations import doc

from shared.models import db

from references.models import Reference
from references.models import Pubmed
from references.models import Pubmod

#from references.models import Journal
#from references.models import Title

logger = logging.getLogger('literature logger')

@doc(description='Add reference to resource', tags=['references'])
class AddReferenceResource(MethodResource):
    def post(self):
        data_string = request.form['data']
        try:
            data = json.loads(data_string)
        except ValueError as e:
            return print(e)

        #Create and/or Find reference record by ID
        reference_id = None
        if 'reference_id' in data:
            reference_obj_from_db = Reference.query.filter_by(id=data['reference_id']).first()
            if reference_obj_from_db:
               reference_id = data['reference_id']
            else:
               return "Supplied 'reference_id' not in database"
        if reference_id == None and 'pubmed_id' in data:
            pubmed_obj_from_db = Pubmed.query.filter_by(id=data['pubmed_id']).first()
            if pubmed_obj_from_db:
                reference_id = pubmed_obj_from_db.reference_id
        elif reference_id == None and 'pubmod_id' in data:
            pubmod_obj_from_db = Pubmed.query.filter_by(id=data['pubmod_id']).first()
            if pubmod_obj_from_db:
                reference_id = pubmod_obj_from_db.reference_id

        if reference_id == None:
            reference_obj = Reference()
        else:
            reference_obj = Reference.query.filter_by(id=reference_id).first()




        #add secondary IDs to database
        if 'pubmed_id' in data:
            pubmed_obj_from_db = Pubmed.query.filter_by(id=data['pubmed_id']).first()
            if not pubmed_obj_from_db:
                print("Adding pubmed_id to database")
                db.session.add(reference_obj)
                pubmed_obj = Pubmed(id=data['pubmed_id'], reference=reference_obj)
                db.session.add(pubmed_obj)
                db.session.commit()
                reference_id = Pubmed.query.filter_by(id=data['pubmed_id']).first().reference_id
        if 'pubmod_id' in data:
            if 'mod' not in data:
                return "'mod' field required if adding 'pubmod_id'"
            print(data['pubmod_id'])
            pubmod_obj_from_db = Pubmod.query.filter_by(id=data['pubmod_id']).first()
            if not pubmod_obj_from_db:
                print("Adding PubMod ID to Database")
                logger.info("Adding PubMod ID to database: ", data['pubmod_id'])
                db.session.add(reference_obj)
                pubmod_obj = Pubmod(id=data['pubmod_id'], mod=data['mod'], reference=reference_obj)
                db.session.add(pubmod_obj)
                db.session.commit()
                reference_id = Pubmod.query.filter_by(id=data['pubmod_id']).first().reference_id

        if 'title' in data:
            print("Adding title")


        return 'Created or Updated: AllianceReference:%s' % reference_id

@doc(description='list all references to resource', tag=['references'])
class ReferenceListResource(MethodResource):
    def get(self):
        return "test"
