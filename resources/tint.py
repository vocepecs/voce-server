from flask_restful import Resource, reqparse, request
import requests
from datetime import datetime


_tint_parse = reqparse.RequestParser()
_tint_parse.add_argument(
    'text',
    type=str,
    required=True,
    help = 'Field - text - cannot be blank'
)

class Tint(Resource):
    def post(self):
        data = _tint_parse.parse_args()
        p = requests.get(url='http://localhost:8012/tint',params={
            'text' : data["text"],
            'format' : 'json'
        })
        tint_status_code = p.status_code
        
        return {
            "tint_result" : p.json(),
            "tint_status_code" : tint_status_code
        }, 200

        
