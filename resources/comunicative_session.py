from flask_restful import Resource, reqparse, request
from flask_jwt_extended import jwt_required

from models.comunicative_session.cs_output_image import CsOutputImageModel

### ! [DEPRECATED]
class UpdateComunicativeSession(Resource):
    
    @jwt_required()
    def put(self):
        old_image_id = request.args.get('old_image_id', type=int, default=None)
        new_image_id = request.args.get('new_image_id', type=int, default=None)
        cs_id = request.args.get('cs_id', type=int, default=None)


        cs_output_image = CsOutputImageModel.find_by_cs_image_id(
            cs_id,
            old_image_id,
        )

        print(cs_output_image)
        if new_image_id != None:
            cs_output_image.correct_image_id = new_image_id
            cs_output_image.output_state_id = 2  # MODIFIED
            cs_output_image.update_to_db()

            return {
                "message": "CS output image modified successfully",
                "new_output_state": 2
            }, 200

        cs_output_image.output_state_id = 3  # DELETED
        cs_output_image.update_to_db()

        return {
            "message": "CS output image deleted successfully",
            "new_output_state": 3
        }, 200
