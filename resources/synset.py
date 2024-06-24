from flask_restful import Resource, reqparse, request
from models.synset import SynsetModel
from models.image import ImageModel
from utils.association_tables import ass_image_synset

from flask_jwt_extended import jwt_required


_sysnet_parser = reqparse.RequestParser()
_sysnet_parser.add_argument(
    'synset_name',
    type=str,
    required = True,
    help = "The field - arasaac_id - cannot be blank."
)
_sysnet_parser.add_argument(
    'synset_name_short',
    type=str,
    required = True,
    help = "The field - synset_name_list - cannot be blank.",
)

_image_synset_ass_parser = reqparse.RequestParser()
_image_synset_ass_parser.add_argument(
    'image_id',
    type=int,
    required = True,
    help = "The field - arasaac_id - cannot be blank."
)
_image_synset_ass_parser.add_argument(
    'synset_id_list',
    type=int,
    required = True,
    help = "The field - synset_name_list - cannot be blank.",
    action= "append",
)

class Synset(Resource):
    
    @jwt_required()
    def post(self):
        data = _sysnet_parser.parse_args()
        synset_name = data["synset_name"]
        synset_name_short = data["synset_name_short"]
        synset = SynsetModel.find_by_name(synset_name)
        if synset:
            return {
                "message" : "The synset is already in the database",
                "synset_id" : synset.id
            }, 409
        synset = SynsetModel(synset_name=synset_name,synset_name_short=synset_name_short)
        synset_id = synset.save_to_db()
        return {
            "message" : "Synset created succesfully",
            "synset_id" : synset_id,
        }

    @jwt_required()
    def put(self):
        print("Start")
        
        data = _image_synset_ass_parser.parse_args()
        image_id = data["image_id"]
        synset_id_list = data["synset_id_list"]
        synset_flag = False

        print(f"data: {data}")

        if len(synset_id_list) > 0:
            image = ImageModel.find_by_id(image_id)
            if not image:
                return {
                "message" : "Image not present."
            }, 404
            for synset_id in synset_id_list:
                synset_model = SynsetModel.find_by_id(synset_id)
                if synset_model:
                    synset_model.images.append(image)
                    synset_model.save_to_db()
                else :
                    synset_flag = True
                    print("[WARNING] : Synset model by id NOT found")
            
            return {
                "message" : "Image - synsets association done.",
                "info" : "All synsets were found" if synset_flag == False else "Some synset were not found"
            }, 200
        
        return {
                "message" : "Invalid request, synset_name_list must have size greather than 0"
            }, 409

    @jwt_required()
    def get(self):
        synset_name = request.args.get('synset_name', type=str, default=None)
        image_model_list = ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(SynsetModel.synset_name == synset_name).all()
        return {
            "caa_images": [caa_image.json() for caa_image in image_model_list],
        }, 200
                 