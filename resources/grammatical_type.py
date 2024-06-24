from flask_restful import Resource, reqparse, request
from models.grammatical_type import GrammaticalTypeModel

from flask_jwt_extended import jwt_required

_grammatical_type_parser = reqparse.RequestParser()
_grammatical_type_parser.add_argument(
    'type',
    type=str,
    required=True,
    help="This field cannot be blank.",
)


class GrammaticalTypeManager(Resource):

    @jwt_required()
    def post(self):
        data = _grammatical_type_parser.parse_args()
        grammatical_type = GrammaticalTypeModel.find_by_value(data['type'])
        if grammatical_type:
            return {
                "message": "The Grammatical type \"" + data["type"] + "\" already exists",
                "grammatical_type_id": grammatical_type.id,
            }, 409
        grammatical_type = GrammaticalTypeModel(**data)
        g_type_id = grammatical_type.save_to_db()
        return {
            "message": "Grammatical type created successfully.",
            "grammatical_type_id": g_type_id,
        }, 200

    @jwt_required()
    def get(self):
        value = request.args.get('grammatical-type', None)
        grammatical_type = GrammaticalTypeModel.find_by_value(value)
        if not grammatical_type:
            return {'message': 'Grammatical type not found'}, 404
        return grammatical_type.json(), 200


class GrammaticalTypeList(Resource):
    @jwt_required()
    def get(self):
        return {
            "grammatical_types": [grammatical_type.json() for grammatical_type in GrammaticalTypeModel.query.all()]
        }, 200
