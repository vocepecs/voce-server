from flask_restful import Resource, reqparse, request
from models.autism_centre import AutismCentreModel
import random
import string

_autism_centre_parser = reqparse.RequestParser()
_autism_centre_parser.add_argument(
    'name',
    type=str,
    required=True,
    help="This field cannot be blank.",
)
_autism_centre_parser.add_argument(
    'address',
    type=str,
        required=True,
    help="This field cannot be blank.",
)


class AutismCentre(Resource):
    def post(self):
        data = _autism_centre_parser.parse_args()
        secret_code = self.generate_code()
        data['secret_code'] = secret_code
        autism_centre = AutismCentreModel(**data)
        autism_centre.save_to_db()
        return {
            "message": "Autism centre created succesfully",
            "secret_code" : secret_code
        }, 201

    def generate_code(self):
        x = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
        print(x)
        return x

class VerifyCode(Resource):
    
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('secret_code', type=str, required=True, help="This field cannot be blank.")
        self.parser.add_argument('centre_id', type=int, required=True, help="This field cannot be blank.")
    
    
    def post(self):
        args = self.parser.parse_args()
        input_code = args['secret_code']
        centre_id = args['centre_id']
        autism_centre = AutismCentreModel.find_by_id(centre_id)
        
        if autism_centre.secret_code == input_code:
            return {
                "Message" : "The secret code is correct"
            }, 200
        else :
            return {
                "Message" : "The secret code is incorrect"
            }, 400

class AutismCentreList(Resource):
    def get(self):
        return {
            "autism_centres": [autism_centre.json() for autism_centre in AutismCentreModel.query.all()]
        }, 200