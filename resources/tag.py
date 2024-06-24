from flask_restful import Resource, reqparse, request
from models.image import ImageModel
from models.tag import ImageTagModel, TagModel
from nltk.stem import SnowballStemmer
from datetime import datetime

from flask_jwt_extended import jwt_required

_tag_parser = reqparse.RequestParser()
_tag_parser.add_argument(
    'tag_value',
    type=str,
    required=True,
    help="This field cannot be blank.",
)

_img_tag_parser = reqparse.RequestParser()
_img_tag_parser.add_argument(
    'tag_type',
    type=str,
    required=True,
    help="This field cannot be blank.",
)
_img_tag_parser.add_argument(
    'weight',
    type=int,
)


class TagManager(Resource):

    @jwt_required()
    def post(self):
        data = _tag_parser.parse_args()
        tag = TagModel.find_by_tag_value(data["tag_value"])
        if tag:
            return {
                "message": "The tag \"" + data["tag_value"] + "\" already exists",
                "tag_id": tag.id
            }, 409
        tag = TagModel(**data)
        tag_id = tag.save_to_db()
        return {
            "message": "Tag created successfully.",
            "tag_id": tag_id
        }, 200

    @jwt_required()
    def get(self):
        value = request.args.get('tag_value', None)
        tag = TagModel.find_by_tag_value(value)
        if not tag:
            return {'message': 'Tag not found'}, 404
        return tag.json(), 200


class TagList(Resource):
    @jwt_required()
    def get(self):
        return {
            "tags": [tag.json() for tag in TagModel.query.all()]
        }, 200


class TagValueStem(Resource):
    @jwt_required()
    def put(self):
        tag_list = TagModel.query.all()
        ps = SnowballStemmer('italian')
        print(f'START STEMMING: {datetime.now()}')
        for tag in tag_list:
            if tag.tag_value_stem == None:
                tag.tag_value_stem = ps.stem(tag.tag_value)
                tag.update_to_db()
        print(f'END STEMMING: {datetime.now()}')


class ImageTagAssociaton(Resource):
    @jwt_required()
    def post(self):
        
        image_id = request.args.get('image_id', None)
        tag_id = request.args.get('tag_id', None)

        image_tag = ImageTagModel.find_by_id(image_id,tag_id)
        if image_tag :
            return {'message': 'The tag is already associated to image'}, 409
        
        image = ImageModel.find_by_id(image_id)
        tag = TagModel.find_by_id(tag_id)

        if not image:
            return {'message': 'Image not found'}, 409
        if not tag:
            return {'message': 'Tag not found'}, 409

        data = _img_tag_parser.parse_args()
        imageTag = ImageTagModel(
            image_id, tag_id, data['tag_type'], data['weight'])
        imageTag.tag = tag
        image.image_tag.append(imageTag)
        image.save_to_db()
        return {
            "message": "Tag associated to image succesfully"
        }, 200
