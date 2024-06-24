from flask_restful import Resource, reqparse, request
from sqlalchemy import func
from datetime import datetime
from models.context import ContextModel
from models.grammatical_type import GrammaticalTypeModel
from models.image_synonym import ImageSynonymModel

from models.image import ImageModel
from models.tag import ImageTagModel, TagModel
from sqlalchemy import or_

from models.audio_tts import AudioTTSModel
from utils.gcp_tts_api import GcpTTSApi
import base64

from flask_jwt_extended import jwt_required

_image_parser = reqparse.RequestParser()
_image_parser.add_argument(
    'id_arasaac',
    type=int,
    required=False,
    help="This field cannot be blank.",
)
_image_parser.add_argument(
    'label',
    type=str,
    required=True,
    help="This field cannot be blank.",
)
_image_parser.add_argument(
    'url',
    type=str,
    required=True,
    help="This field cannot be blank.",
)
_image_parser.add_argument(
    'string_coding',
    type=str,
)
_image_parser.add_argument(
    'usage_counter',
    type=int,
    required=False,
    help="This field cannot be blank.",
)
# _image_parser.add_argument(
#     'is_personal',
#     type=bool,
#     required=True,
#     help="This field cannot be blank.",
# )
_image_parser.add_argument(
    'insert_date',
    type=lambda x: datetime.strptime(x, "%Y-%m-%d"),
    required=True,
    help="This field cannot be blank.",
)
# _image_parser.add_argument(
#     'is_active',
#     type=bool,
#     required=True,
#     help="This field cannot be blank.",
# )
# _image_parser.add_argument(
#     'grammatical_type_id',
#     type=int,
#     required=True,
#     help="This field cannot be blank.",
# )
# _image_parser.add_argument(
#     'context_id',
#     type=int,
#     required=True,
#     help="This field cannot be blank.",
# )
_image_parser.add_argument(
    'autism_centre_id',
    type=int,
    required=False,
    help="This field cannot be blank.",
)

_private_image_parser = reqparse.RequestParser()
_private_image_parser.add_argument(
    'patient_list',
    type=int,
    action='append'
)


_image_synonym_parser = reqparse.RequestParser()
_image_synonym_parser.add_argument(
    'synonym_id_list',
    type=int,
    action='append'
)


# Constants
ARASAAC_IMAGE = 'arasaac_image'
CUSTOM_IMAGE = 'custom_image'


def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")


class Image(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('id_arasaac', type=int, location='json')
        self.parser.add_argument(
            'label', type=str, required=True, location='json')
        self.parser.add_argument('url', type=str, location='json')
        self.parser.add_argument(
            'string_coding', type=str, required=True, location='json')
        self.parser.add_argument('usage_counter', type=int, location='json')
        self.parser.add_argument(
            'insert_date', type=parse_date, required=True, location='json')
        self.parser.add_argument('autism_centre_id', type=int, location='json')
        self.parser.add_argument(
            'user_id', type=str, required=True, location='json')

    def SelectTargetImage(self, image_list):
        if len(image_list) == 1:
            return image_list

        elif len(image_list) > 1:
            context_list = []
            for image in image_list:
                ctx_id_list = list(
                    map(lambda x: x.id, image.image_context))
                ctx_id_list.append(image.id)
                context_list.extend([ctx_id_list])
            context_list.sort(key=len, reverse=True)
            print(f'context list: {context_list}')
            # prendo l'id della prima immagine
            images_selected = [context_list[0][-1]]
            for context in context_list[1:]:
                if len(context) != len(context_list[0]) or any(item not in context_list[0][:-1] for item in context[:-1]):
                    images_selected.append(context[-1])
            print(f'images selected: {images_selected}')

            if len(images_selected) == 1:
                image = next(
                    (image for image in image_list if image.id ==
                     images_selected[0]),
                    None
                )
                return [image]

            else:
                return [caa_image for caa_image in image_list if caa_image.id in images_selected]
        else:
            return None

    def createCustomImage(self, data, image_id):
        
        image = ImageModel.find_by_id(image_id)
        new_image = ImageModel(**data)

        new_image_id = new_image.save_to_db()
        
        new_image = ImageModel.find_by_id(new_image_id)

        print("TEST CREAZIONE PITTOGRAMMA CUSTOM")
        print(f"image tags: {image.image_tag}")

        
        for im_tag_association in image.image_tag:
            im_tag_model = ImageTagModel(
                new_image_id,
                im_tag_association.tag_id,
                im_tag_association.tag_type,
                im_tag_association.weight
            )
            im_tag_model.save_to_db()

        for im_context in image.image_context:
            new_image.image_context.append(im_context)
        
        new_image.save_to_db()

        audio_tts_model = AudioTTSModel.find_by_label(new_image.label)
        if audio_tts_model:
            for audio_tts in audio_tts_model:
                audio_tts.images.append(new_image)
                audio_tts.save_to_db()
            return new_image_id
        

        try:
            gcp_tts_api = GcpTTSApi()
            for gender in ["MALE", "FEMALE"]:
                response, model = gcp_tts_api.synthetize_speech(gender=gender, input_text=new_image.label)
                base64_string = base64.b64encode(response).decode('utf-8')
                framework = "CGP Cloud Text To Speech API"

                audio_tts_model = AudioTTSModel(
                    label=new_image.label,
                    gender=gender,
                    model=model,
                    framework=framework,
                    base64_string=base64_string
                )

                audio_tts_model.images.append(new_image)
                audio_tts_model.save_to_db()

        except Exception as e:
            print(f"An error occurred: {str(e)}")
        
        finally:    
            return new_image_id

    @jwt_required()
    def post(self):

        image_type = request.args.get(
            'image_type', type=str, default='arasaac_image')

        image_id = request.args.get('image_id', type=int, default=None)

        correction_label = request.args.get(
            'correction_label', type=str, default=None)

        args = self.parser.parse_args()

        print("TEST PARAMETRI CREAZIONE PITTOGRAMMA")
        print(f"args: {args}")
        print(f"image_id: {image_id}")
        print(f"image_type: {image_type}")
        print(f"correction_label: {correction_label}")

        # Creo l'immagine customizzata copiando i metadati dall'immagine di arasaac
        if image_id != None:
            new_image_id = self.createCustomImage(args, image_id)
            if new_image_id != None:
                return {
                    "message": "Image created successfully",
                    "image_id": new_image_id
                }, 200
            return {
                "message": "Internal server error: Image not created"
            }, 500

        if image_type == ARASAAC_IMAGE:
            id_arasaac = args['id_arasaac']
            image_arasaac = ImageModel.find_by_id_arasaac(id_arasaac)
            if not image_arasaac:
                image = ImageModel(**args)
                image_id = image.save_to_db()
                return {"message": "Image created successfully.",
                        "image_id": image_id
                        }, 200

            return {"message": "This image already exists",
                    "ARASAAC Image": image_arasaac.json()
                    }, 409

        # Se non ho un immagine di ARASAAC, avvio nuovo processo di creazione di un'immagine customizzata
        elif image_type == CUSTOM_IMAGE:

            if correction_label != None and correction_label != 'null':
                label = correction_label
            else:
                label = args['label']

            # Lista immagini con tag KEYWORD uguale alla label in input
            image_list = ImageModel.query.join(ImageTagModel).join(TagModel).filter(
                ImageTagModel.tag_type == 'KEYWORD',
                func.lower(TagModel.tag_value) == func.lower(label)
            ).all()

            target_image_list = self.SelectTargetImage(image_list)

            if target_image_list != None:
                return {
                    "caa_images": [caa_image.json() for caa_image in target_image_list],
                    "state": "pending"
                }, 200
            else:
                image_list = ImageModel.query.join(ImageTagModel).join(TagModel).filter(
                    ImageTagModel.tag_type == 'KEYWORD',
                    TagModel.tag_value.ilike(label)
                ).all()
                target_image_list = self.SelectTargetImage(image_list)
                if target_image_list != None:
                    return {
                        "caa_images": [caa_image.json() for caa_image in target_image_list],
                        "state": "pending"
                    }, 200
                else:
                    return {
                        "Message": "No Image found for tagging, please retray with another label",
                        "state": "failure"
                    }, 400

    @jwt_required()
    def get(self):
        value = request.args.get('image_id', None)
        image = ImageModel.find_by_id(value)
        if not image:
            return {'message': 'Image not found'}, 404
        return image.json(), 200

    @jwt_required()
    def delete(self):
        value = request.args.get('image_id', None)
        image = ImageModel.find_by_id(value)
        if image.id_arasaac != None:
            return {'message': 'Delete not available for ARASAAC images'}, 400
        if not image:
            return {'message': 'Image not found'}, 404
        image.delete_from_db()
        return {'message': 'Image deleted'}, 200

    @jwt_required()
    def put(self):
        value = request.args.get('image_id', None)
        image = ImageModel.find_by_id(value)
        if not image:
            return {'message': 'Image not found'}, 404
        data = request.get_json()
        for key in data.keys():
            if key == 'label':
                image.label = data[key]
            elif key == 'url':
                image.url = data[key]
            elif key == 'string_coding':
                image.string_coding = data[key]
            elif key == 'usage_counter':
                image.usage_counter = data[key]
            elif key == 'insert_date':
                image.insert_date = data[key]
            elif key == 'autism_centre_id':
                image.autism_centre_id = data[key]
            elif key == 'user_id':
                image.user_id = data[key]
        image.save_to_db()
        return {'message': 'Image updated'}, 200


class AllImageList(Resource):
    @jwt_required()
    def get(self):
        return [caa_image.json() for caa_image in ImageModel.query.all()], 200
        # return ImageModel.query.first().json(), 200


class ImageList(Resource):

    @jwt_required()
    def get(self):

        # Images search parameters
        search_user_images = request.args.get(
            'search_user_images', type=bool, default=False)
        user_id = request.args.get('user_id', type=int, default=None)

        if search_user_images == True:
            caa_image_list = ImageModel.find_user_images(user_id)
            if caa_image_list:
                return {
                    "message": f"{len(caa_image_list)} images found.",
                    "caa_images": [caa_image.json() for caa_image in caa_image_list]
                }, 200
            return {
                "message": "No images found"
            }, 404

        # ? TEST per analisi sui synsey e tag
        method = request.args.get('method', type=str, default=None)
        if method:
            return {
                "caa_images": [caa_image.json_simple() for caa_image in ImageModel.query.all()]
            }

        return {
            "caa_images": [caa_image.json() for caa_image in ImageModel.query.all()]
        }


class ImageContext(Resource):
    @jwt_required()
    def post(self):
        image_id = request.args.get('image_id', None)
        context_id = request.args.get('context_id', None)

        image = ImageModel.find_by_id(image_id)
        if not image:
            return {'message': 'Image not found'}, 404
        context = ContextModel.find_by_id(context_id)
        if not context:
            return {'message': 'Context not found'}, 404

        image.image_context.append(context)
        image.save_to_db()

        return {
            "message": "Context associated to image succesfully"
        }, 200


class ImageGrammaticalType(Resource):
    @jwt_required()
    def post(self):
        image_id = request.args.get('image_id', None)
        grammatical_type_id = request.args.get('grammatical_type_id', None)

        image = ImageModel.find_by_id(image_id)
        if not image:
            return {'message': 'Image not found'}, 404
        grammatical_type = GrammaticalTypeModel.find_by_id(grammatical_type_id)
        if not grammatical_type:
            return {'message': 'Grammatical type not found'}, 404

        image.image_grammatical_type.append(grammatical_type)
        image.save_to_db()

        return {
            "message": "Grammatical type associated to image succesfully"
        }, 200


class ImageSynonym(Resource):
    @jwt_required()
    def post(self):
        image_id = request.args.get('image_id', type=int, default=None)
        synonym_id_list = _image_synonym_parser.parse_args()["synonym_id_list"]

        for syn_id in synonym_id_list:

            imageSynModel = ImageSynonymModel(image_id, syn_id)
            imageSynModel.save_to_db()

        return {
            "message": "Synonyms correctly added"
        }, 200
