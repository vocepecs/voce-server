from flask_restful import Resource, reqparse, request
from datetime import datetime
from enum import Enum

from models.image import ImageModel 
from models.patient import PatientModel
from models.tag import TagModel, ImageTagModel
from models.context import ContextModel
from models.synset import SynsetModel
from models.image_synonym import ImageSynonymModel

from models.caa_table import CaaTableModel, PatientCaaTableModel
from models.table_sector import TableSectorModel

from flask_jwt_extended import jwt_required
 

def parse_date(dateString):
    return datetime.strptime(dateString, "%Y-%m-%d")


class PostType(Enum):
    IMAGE_CREATION = 1
    IMAGE_PATIENT_ASSOCIATION = 2
    IMAGE_TAG_ASSOCIATION = 3
    IMAGE_CONTEXT_ASSOCIATION = 4
    IMAGE_SYNSET_ASSOCIATION = 5
    IMAGE_SYNONYM_ASSOCIATION = 6

class CaaTablePostType(Enum):
    CAA_TABLE_CREATION = 1
    CAA_TABLE_SECTOR_ASSOCIATION = 2
    CAA_TABLE_SECTOR_IMAGE_ASSOCIATION = 3

class ImageMaintenance(Resource):
    def __init__(self):

        self.parser = reqparse.RequestParser()
        self.parser.add_argument('id_arasaac', type=int, location='json')
        self.parser.add_argument('label', type=str, required=True, help = "label error", location='json')
        self.parser.add_argument('url', type=str, required=True, help = "url error", location='json')
        self.parser.add_argument('string_coding', type=str, location='json')
        self.parser.add_argument('usage_counter', type=int, location='json')
        self.parser.add_argument('insert_date',type=parse_date, required=True, help = "insert date error", location='json')
        self.parser.add_argument('autism_centre_id', type=int, location='json')
        

        self.im_ass_parser = reqparse.RequestParser()
        self.im_ass_parser.add_argument('image_id', type=int)
        self.im_ass_parser.add_argument('patient_id', type=int)
        self.im_ass_parser.add_argument('tag_value', type=str)
        self.im_ass_parser.add_argument('tag_type', type=str)
        self.im_ass_parser.add_argument('context_type', type=str)
        self.im_ass_parser.add_argument('synset_name', type=str)
        self.im_ass_parser.add_argument('id_arasaac', type=int)
    
    def post_type_validation(self,type):
        for types in PostType:
            if type.upper() in types.name:
                return True
        return False
    
    def image_creation(self):
        args = self.parser.parse_args()
        image_model = ImageModel(**args)
        image_id = image_model.save_to_db()
        print(image_id)
        return {
            "Message" : "Image successfully added",
            "image_id" : image_id
        }, 201
    
    def image_patient_association(self):
        args = self.im_ass_parser.parse_args()
        
        try:
            patient_id = args['patient_id']
            image_id = args['image_id']
        except:
            return {
                "message" : "Errore: inserire patient_id o image_id"
            }, 400
        
        patient_model = PatientModel.find_by_id(patient_id)
        image_model = ImageModel.find_by_id(image_id)

        patient_model.images.append(image_model)
        patient_model.save_to_db()

        return {
            "message" : "Image associated to Patient"
        }, 200
        
    def image_tag_association(self):
        im_ass_args = self.im_ass_parser.parse_args()

        try:
            image_id = im_ass_args['image_id']
            tag_type = im_ass_args['tag_type']
            tag_value = im_ass_args['tag_value']
        except:
            return {
                "message" : "Errore: inserire image_id, tag_type, tag_value"
            }, 400

        tag_model = TagModel.find_by_tag_value(tag_value)

        if tag_model:
            image_tag_model = ImageTagModel(image_id,tag_model.id,tag_type,1)

            image_tag_model.save_to_db()
            return {
                "message" : "Image tag associated successfully"
            }, 200
        else:
            return {
                "message" : "Tag value not found"
            }, 404

    def image_context_association(self):
        im_ass_args = self.im_ass_parser.parse_args()

        try:
            image_id = im_ass_args['image_id']
            context_type = im_ass_args['context_type']
        except:
            return {
                "message" : "Errore: inserire image_id, context_type"
            }, 400
        
        context_model = ContextModel.find_by_value(context_type)
        image_model = ImageModel.find_by_id(image_id)

        image_model.image_context.append(context_model)
        image_model.save_to_db()

        return {
            "message" : "Image Context succesfully added"
        }, 200
    
    def image_synset_association(self):
        im_ass_args = self.im_ass_parser.parse_args()

        try:
            image_id = im_ass_args['image_id']
            synset_name = im_ass_args['synset_name']
        except:
            return {
                "message" : "Errore: inserire image_id, synset_name"
            }, 400
        
        synset_model = SynsetModel.find_by_name(synset_name)
        image_model = ImageModel.find_by_id(image_id)

        image_model.synsets.append(synset_model)
        image_model.save_to_db()

        return {
            "message" : "Image Synset succesfully added"
        }, 200 

    def image_synonym_association(self):
        im_ass_args = self.im_ass_parser.parse_args()

        try:
            image_id = im_ass_args['image_id']
            id_arasaac = im_ass_args['id_arasaac']
        except:
            return {
                "message" : "Errore: inserire image_id, id_arasaac"
            }, 400
        
        arasaac_image_model = ImageModel.find_by_id_arasaac(id_arasaac)

        image_synonym_model = ImageSynonymModel(image_id,arasaac_image_model.id)
        image_synonym_model.save_to_db()
        

        return {
            "message" : "Image Synonym succesfully added"
        }, 200

    @jwt_required()
    def post(self):
        type = request.args.get('post_type', type=str, default=None)
        if self.post_type_validation(type) == False:
            return {
                "message" : "Tipologia di metodo POST errata"
            }, 400
        
        if type.upper() == PostType.IMAGE_CREATION.name:
            return self.image_creation()
        elif type.upper() == PostType.IMAGE_PATIENT_ASSOCIATION.name:
            return self.image_patient_association()
        elif type.upper() == PostType.IMAGE_TAG_ASSOCIATION.name:
            return self.image_tag_association()
        elif type.upper() == PostType.IMAGE_CONTEXT_ASSOCIATION.name:
            return self.image_context_association()
        elif type.upper() == PostType.IMAGE_SYNSET_ASSOCIATION.name:
            return self.image_synset_association()
        elif type.upper() == PostType.IMAGE_SYNONYM_ASSOCIATION.name:
            return self.image_synonym_association()
        
    @jwt_required()
    def get(self):
        label = request.args.get('label', type=str, default=None)
        image_model = ImageModel.find_custom_image_by_label(label)
        if image_model : 
            return {
                "message" : "image found",
                "image" : image_model.json()
            }, 200
        
        return {
            "message" : "image not found"
        }, 404
        


class CaaTableMaintenance(Resource):
    
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', type=str,location='json')
        self.parser.add_argument('table_format', type=str,location='json')
        self.parser.add_argument('creation_date', type=parse_date, location='json')
        self.parser.add_argument('last_modify_date', type=parse_date,location='json')
        self.parser.add_argument('is_active', type=bool,location='json')
        self.parser.add_argument('description', type=str,location='json')
        self.parser.add_argument('user_id', type=int,location='json')
        self.parser.add_argument('patient_id', type=int,location='json')
        self.parser.add_argument('image_string_coding', type=str,location='json')
        self.parser.add_argument('is_private', type=bool,location='json')
        self.parser.add_argument('autism_centre_id', type=int,location='json')
        self.parser.add_argument('sector_list', type=dict, action='append',location='json')
    
    @jwt_required()
    def post(self):
        
        # Get input data e parameters
        args = self.parser.parse_args()
        patient_id = args['patient_id']

        caa_table = CaaTableModel(
            args['name'],
            args['table_format'],
            args['creation_date'],
            args['last_modify_date'],
            args['is_active'],
            args['description'],
            args['image_string_coding'],
            args['user_id'],
            args['autism_centre_id'],
            args['is_private']
        )

        caa_table_id = caa_table.save_to_db()

        print(f"New table id: {caa_table_id}")

        # Creazione dei settori per il salvataggio delle immagini in tabella
        json_sector_list = args['sector_list']
        for json_sector in json_sector_list:
            table_sector = TableSectorModel(
                int(json_sector['id']),
                caa_table_id,
                json_sector['sector_color'],
                json_sector['table_sector_number'],
            )
            for id_arasaac in json_sector['image_id_arasaac_list']:
                image_model = ImageModel.find_by_id_arasaac(id_arasaac)
                table_sector.images.append(image_model)
            table_sector.save_to_db()

        # Associazione Tabella - Paziente
        if patient_id:
            pt_association = PatientCaaTableModel(patient_id,caa_table_id,None)
            pt_association.save_to_db()


        return {"message": "Caa Table created successfully.",
                "caa_table_id": caa_table_id, }, 201
    

