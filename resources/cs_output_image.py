from flask_restful import Resource, request, reqparse
from models.comunicative_session.cs_output_image import CsOutputImageModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from utils.nlp_preprocess import NlpPreprocess
import Levenshtein

from flask_jwt_extended import jwt_required

_cs_image_parser = reqparse.RequestParser()
_cs_image_parser.add_argument(
    'initial_id_list',
    type=int,
    action='append',
)
_cs_image_parser.add_argument(
    'final_id_list',
    type=int,
    action='append',
)


class CsOutputImage(Resource):
    @jwt_required()
    def post(self):
        image_id = request.args.get('image_id', type=int, default=None)
        new_image_id = request.args.get('new_image_id', type=int, default=None)
        cs_id = request.args.get('cs_id', type=int, default=None)

        print(f"image id: {image_id}")
        print(f"new image id: {new_image_id}")
        print(f"comunicative session id: {cs_id}")

        if len(_cs_image_parser.args) > 0:
            data = _cs_image_parser.parse_args()
            print(f"data: {data}")

        # Sostituzione immagine
        if new_image_id:
            cs_ouput_image_model = CsOutputImageModel.find_by_cs_image_id(
                cs_id, image_id)
            print(f"cs model: {cs_ouput_image_model}")
            if cs_ouput_image_model:
                cs_ouput_image_model.correct_image_id = new_image_id
                cs_ouput_image_model.output_state_id = 2  # Modificata
                cs_ouput_image_model.save_to_db()
                return {
                    "old_image_id": image_id,
                    "new_image_id": new_image_id,
                    "session_id": cs_id,
                    "output_state": 2,
                    "output_message": "Pittogramma sostituito",
                    "message": "Image modified succesfully"
                }, 200
            else:
                return {
                    "message": "cs output image not found"
                }, 404

        # Cambio di posizione
        elif data['initial_id_list'] != data['final_id_list']:

            cs_output_image_list = CsOutputImageModel.find_by_cs_id(cs_id)

            print(f"data final id list: {data['final_id_list']}")
            print(f"cs output image list: {cs_output_image_list}")

            for cs_output_image in cs_output_image_list:
                print(f"cs output image: {cs_output_image.image_id}")

            for cs_output_image in cs_output_image_list:
                new_position = data['final_id_list'].index(
                    cs_output_image.image_id)
                cs_output_image.final_position = new_position
                cs_output_image.output_state_id = 2  # Modificata
                cs_output_image.save_to_db()

            return {

                "new_position": data['final_id_list'],
                "session_id": cs_id,
                "output_state": 2,
                "output_message": "Pittogramma riordinato",
                "message": "Image modified succesfully"
            }, 200

    @jwt_required()
    def delete(self):
        image_id = request.args.get('image_id', type=int, default=None)
        cs_id = request.args.get('cs_id', type=int, default=None)
        cs_ouput_image_model = CsOutputImageModel.find_by_cs_image_id(
            cs_id, image_id)
        if cs_ouput_image_model:
            cs_ouput_image_model.output_state_id = 3
            cs_ouput_image_model.save_to_db()
            return {
                "image_id": image_id,
                "session_id": cs_id,
                "output_state": 3,
                "output_message": "Pittogramma eliminato",
                "message": "Image deleted succesfully"
            }, 200
        else:
            return {
                "message": "cs output image not found"
            }, 404


class CsOutputPushImage(Resource):
    
    """
    Questo metodo permette di inserire una nuova immagine nella sessione comunicativa corrente,
    a partire da un token di ricerca, un id di immagine e un id di sessione.

    :param image_id: l'id dell'immagine da inserire
    :param search_token: il token di ricerca usato per trovare l'immagine
    :param cs_phrase: la frase della sessione comunicativa
    :param cs_id: l'id della sessione comunicativa
    :return: un messaggio di successo o di errore
    """
    @jwt_required()
    def post(self):
        image_id = request.args.get('image_id', type=int, default=None)
        search_token = request.args.get('search_token', type=str, default=None)
        cs_phrase = request.args.get('cs_phrase', type=str, default=None)
        cs_id = request.args.get('cs_id', type=int, default=None)

        cs = ComunicativeSessionModel.find_by_id(cs_id)
        # Aggiorno la frase della sessione comunicativa se è cambiata lato client dopo la traduzione
        if cs.text_phrase.lower() != cs_phrase.lower():
            cs.text_phrase = cs_phrase

        npl_preprocess = NlpPreprocess()
        token_dict, token_lemmas, pos_tag_m_list = npl_preprocess.get_token_lemmas(
            phrase=cs_phrase)

        # Imposto la posizione iniziale della nuova immagine inserita in coda
        initial_position = 0
        cs_output_image_list = CsOutputImageModel.find_by_cs_id(cs_id)
        for cs_output_image in cs_output_image_list:
            if cs_output_image.final_position:
                if cs_output_image.final_position > initial_position:
                    initial_position = cs_output_image.final_position
            elif cs_output_image.initial_position > initial_position:
                initial_position = cs_output_image.initial_position

        initial_position = initial_position + 1

        for pos_tag_m in pos_tag_m_list:
            dist = Levenshtein.distance(pos_tag_m.token, search_token)
            print(f"pos_tag_m token: {pos_tag_m.token}")
            print(f"search token: {search_token}")
            print(f"LEV Distance : {dist}")
            if dist <= 1:
                cs_output_image = CsOutputImageModel(
                    pos_tag_m.token,
                    pos_tag_m.grammatical_type_id,
                    cs_id,
                    image_id,
                    None,
                    1,
                    initial_position,
                    None
                )
                cs_output_image.save_to_db()
        return {
            "message": "Immagine inserita correttamente in coda"
        }, 200
