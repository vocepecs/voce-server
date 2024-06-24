from flask_restful import Resource, reqparse, request
from models.audio_tts import AudioTTSModel
from models.image import ImageModel
from flask_jwt_extended import jwt_required

class AudioTTS(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument("label", type=str, required=True, location="json")
        self.parser.add_argument("gender", type=str, required=True, location="json")
        self.parser.add_argument("model", type=str, location="json")
        self.parser.add_argument("framework", type=str, location="json")
        self.parser.add_argument("base64_string", type=str, required=True, location="json")

    @jwt_required()
    def post(self):
        image_id = request.args.get("image_id", type=int, default=None)
        args = self.parser.parse_args()

        if not image_id:
            return {
                "message" : "Specificare l'id dell'immagine"
            }, 400

        image_model = ImageModel.find_by_id(image_id)
        if not image_model:
            return {
                "message" : "L'immagine specificata non esiste"
            }, 400
        
        audio_tts_model = AudioTTSModel(**args)
        audio_tts_model.images.append(image_model)

        audio_tts_id = audio_tts_model.save_to_db()



        return {
            "message" : "Audio TTS sussefully created",
            "audio_tts_id" :audio_tts_id
        }, 201


    def get(self):
        pass
        