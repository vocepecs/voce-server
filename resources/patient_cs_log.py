from flask_restful import Resource, reqparse, request
from datetime import datetime
from models.comunicative_session.patient_cs_log import PatientCsLogModel

from flask_jwt_extended import jwt_required

_log_parser = reqparse.RequestParser()
_log_parser.add_argument(
    'date',
    type=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
    required=True,
    help="The field - date - cannot be blank.",
)
_log_parser.add_argument(
    'log_type',
    type=str,
    required=True,
    help="The field - log_type - cannot be blank.",
)
_log_parser.add_argument(
    'patient_id',
    type=int,
    required=True,
    help="The field - patient_id - cannot be blank.",
)
_log_parser.add_argument(
    'user_id',
    type=int,
    required=True,
    help="The field - user_id - cannot be blank.",
)
_log_parser.add_argument(
    'caa_table_id',
    type=int,
    required=True,
    help="The field - caa_table_id - cannot be blank.",
)
_log_parser.add_argument(
    'image_id',
    type=int,
    required=False,
)
_log_parser.add_argument(
    'image_position',
    type=int,
    required=False,
)

valid_log_type = [
    'DELETE_LAST',
    'DELETE_ALL',
    'INSERT_IMAGE',
    'SINGLE_AUDIO_PLAY',
    'PHRASE_AUDIO_PLAY'
]


class PatientCsLog(Resource):

    @jwt_required()
    def post(self):
        data = _log_parser.parse_args()
        if data["log_type"].upper() not in valid_log_type:
            return {
                "message" : "Invalid log type",
                "valid_log_types" : valid_log_type
            }, 403
        if data["log_type"].upper() == 'INSERT_IMAGE':
            if data["image_id"] == None:
               return {
                "message" : "Specify image id.",
            }, 403
            if data["image_position"] == None:
               return {
                "message" : "Specify image position.",
            }, 403
        if data["log_type"].upper() == "DELETE_LAST":
            if data["image_id"] == None:
               return {
                "message" : "Specify image id.",
            }, 403

        patient_cs_log = PatientCsLogModel(**data)
        patient_cs_log.save_to_db()

        return {
            "message" : "Log saved succesfully"
        }, 200
