from flask_restful import Resource, reqparse, request
from models.context import ContextModel
from flask_jwt_extended import jwt_required


_context_parser = reqparse.RequestParser()
_context_parser.add_argument(
    'context_type',
    type=str,
    required=True,
    help="This field cannot be blank.",
)


class ContextManager(Resource):
    @jwt_required()
    def post(self):
        data = _context_parser.parse_args()
        context = ContextModel.find_by_value(data['context_type'])
        if context:
            return {
                "message": "The context \"" + data["context_type"] + "\" already exists",
                "context_id": context.id
            }, 409
        context = ContextModel(**data)
        context_id = context.save_to_db()
        return {
            "message": "Context created successfully.",
            "context_id": context_id,
        }, 200

    @jwt_required()
    def get(self):
        value = request.args.get('context', None)
        context = ContextModel.find_by_value(value)
        if not context:
            return {'message': 'Context not found'}, 404
        return context.json(), 200


class ContextList(Resource):
    @jwt_required()
    def get(self):
        return {
            "context_list": [context.json() for context in ContextModel.query.all()]
        }, 200
