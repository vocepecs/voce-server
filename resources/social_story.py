from flask_restful import Resource, reqparse, request
from datetime import datetime
from models.patient import PatientSocialStoryModel
from models.social_story import SocialStoryModel, SocialStorySessionModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.cs_output_image import CsOutputImageModel

from flask_jwt_extended import jwt_required

# TODO Da rimuovere
valid_options = ['PRIVATE', 'CENTRE', 'PUBLIC']


def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")


class SocialStory(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('id', type=int)
        self.parser.add_argument('title', type=str, required=True)
        self.parser.add_argument('description', type=str)
        self.parser.add_argument('image_string_coding', type=str)
        self.parser.add_argument(
            'creation_date', type=parse_date, required=True)
        self.parser.add_argument('is_private', type=bool, required=True)
        self.parser.add_argument('autism_centre_id', type=int)
        self.parser.add_argument('user_id', type=int, required=True)
        self.parser.add_argument('patient_id', type=int)
        self.parser.add_argument('is_deleted', type=bool)
        self.parser.add_argument('is_active', type=bool)
        self.parser.add_argument('cs_list', type=dict, action="append")
        self.parser.add_argument('original_social_story_id', type=int)

    @jwt_required()
    def post(self):
        args = self.parser.parse_args()
        print(f"data: {args}")
        # ! Sostituiti nel body della POST
        # user_id = request.args.get('user_id', type=int, default=None)
        # patient_id = request.args.get('patient_id', type=int, default=None)
        # autism_centre_id = request.args.get('autism_centre_id', type=int, default=None)

        if args.get('original_social_story_id'):
            original_ss = SocialStoryModel.find_by_id(args['original_social_story_id'])
            social_story = SocialStoryModel(
                original_ss.title,
                original_ss.description,
                original_ss.image_string_coding,
                original_ss.creation_date,
                original_ss.is_private,
                original_ss.user_id,
                original_ss.autism_centre_id,
                original_ss.is_active
            )
            
        else:
            social_story = SocialStoryModel(
                title=args["title"],
                description=args["description"],
                image_string_coding=args["image_string_coding"],
                creation_date=args["creation_date"],
                is_private=args["is_private"],
                user_id=args["user_id"],
                autism_centre_id=args['autism_centre_id'],
                is_active=args['is_active']
            )

        social_story_id = social_story.save_to_db()

        if args.get('patient_id'):
            patient_social_story = PatientSocialStoryModel(
                args['patient_id'], 
                social_story_id, 
                args.get('original_social_story_id')
            )
            patient_social_story.save_to_db()

        for cs_index, cs in enumerate(args["cs_list"]):
            social_story_session_model = SocialStorySessionModel(
                social_story_id, cs["cs_id"],
                cs_index, cs["title"],
            )
            social_story_session_model.save_to_db()

            cs_model = ComunicativeSessionModel.find_by_id(cs["cs_id"])
            for image_index, image in enumerate(cs["image_list"]):
                cs_oi = cs_model.get_output_image_by_id(image["image_id"])
                if not cs_oi:
                    cs_output_image_model = CsOutputImageModel(
                        None,
                        None,
                        cs["cs_id"],
                        image["image_id"],
                        None,
                        image["status"],
                        image_index,
                        None,
                    )
                    cs_output_image_model.save_to_db()


        return {
            "message": "Social Story created succesfully",
            "social_story_id": social_story_id,
        }, 201

    @jwt_required()
    def get(self):
        social_story_id = request.args.get('social_story_id', type=int, default=None)
        ss = SocialStoryModel.find_by_id(social_story_id)
        return ss.json(), 200

    @jwt_required()
    def put(self):
        data = self.parser.parse_args()

        ss = SocialStoryModel.find_by_id(data['id'])
        cs_list = data["cs_list"]

        ss_update = False
        if ss.title != data['title']:
            ss.title = data['title']
            ss_update = True
        if ss.description != data['description']:
            ss.description = data['description']
            ss_update = True
        if ss.image_string_coding != data['image_string_coding']:
            ss.image_string_coding = data['image_string_coding']
            ss_update = True
        if ss.is_private != data['is_private']:
            ss.is_private = data['is_private']
            ss_update = True
        if ss.autism_centre_id != data['autism_centre_id']:
            ss.autism_centre_id = data['autism_centre_id']
            ss_update = True

        if ss_update:
            ss.save_to_db()

        # ss : social_story
        # cs : comunicative_session
        # sscs : social_story_comunicative_session
        # cs_oi : cs_output_image

        # Elimino le sessioni comunicative il cui ID non è nella lista di input [cs_list]
        for sscs in ss.social_story_sessions:
            if cs_list == None:
                sscs.delete_from_db()
            elif all(sscs.comunicative_session_id != x["cs_id"] for x in cs_list):
                sscs.delete_from_db()
        # sscs.delete_from_db()

        if cs_list != None:
            for cs_index, cs in enumerate(cs_list):
                sscs = ss.get_session_by_id(cs["cs_id"])
                cs_model = ComunicativeSessionModel.find_by_id(cs["cs_id"])

                # Controllo se la sessione comunicativa è presente oppure se è stato modificato l'ordine e titolo
                if sscs != None:
                    if sscs.title != cs["title"]:
                        sscs.title = cs["title"]
                        sscs.save_to_db()
                    if sscs.position != cs_index:
                        sscs.position = cs_index
                        sscs.save_to_db()
                else:
                    new_sscs = SocialStorySessionModel(
                        ss.id, cs["cs_id"], cs_index, cs["title"])
                    new_sscs.save_to_db()

                # Gestione modifica immagini nella sessione comunicativa
                for image_index, image in enumerate(cs["image_list"]):

                    cs_oi = cs_model.get_output_image_by_id(image["image_id"])


                    if not cs_oi:
                        cs_oi = CsOutputImageModel(
                            None,
                            None,
                            cs["cs_id"],
                            image["image_id"],
                            None,
                            image["status"],
                            image_index,
                            None,
                        )
                        cs_oi.save_to_db()

                    # Controllo se l'immagine è stata eliminata dalla lista
                    if image["status"] == 3:
                        cs_oi.output_state_id = 3
                        cs_oi.save_to_db()

                    # Controllo se l'immagine è stata modificata con un immagine suggerita
                    elif image["status"] == 2:
                        cs_oi.correct_image_id = image["correct_image_id"]
                        cs_oi.output_state_id = 2
                        cs_oi.save_to_db()

                    # Controllo se è stata modificata la posizione dell'immagine
                    # if cs_oi.output_state_id != 3:
                    #     if cs_oi.final_position != None:
                    #         if cs_oi.final_position != image_index:
                    #             cs_oi.final_position = image_index
                    #             cs_oi.output_state_id = 2
                    #             cs_oi.save_to_db()

                    #     elif cs_oi.initial_position != image_index:
                    #         cs_oi.final_position = image_index
                    #         cs_oi.output_state_id = 2
                    #         cs_oi.save_to_db()

        return {
            "message": "Social Story updated succesfully",
            "social_story": ss.json()
        }, 200

    @jwt_required()
    def delete(self):
        ss_id = request.args.get('social_story_id', type=int, default=None)
        print(f"[DEBUG] ss_id: {ss_id} d_type: {type(ss_id)}")
        ss_model = SocialStoryModel.find_by_id(ss_id)
        ss_model.is_deleted = True
        ss_model.save_to_db()

        return {
            "message": "Social Story deleted successfully"
        }, 200
    

class SocialStoriesList(Resource):
    @jwt_required()
    def get(self):
        
        option = request.args.get('option', type=str, default='PRIVATE')
        search_most_used = request.args.get('search_most_used', type=bool, default=False)

        if search_most_used:
            social_story_list = SocialStoryModel.find_most_used_stories()
            return {
                "social_story_list": [social_story.json() for social_story in social_story_list],
                "number_of_stories": len(social_story_list)
            }, 200

        
        if option.upper() not in valid_options:
            return {
                "message": "Invalid option",
                "valid_options": ["PRIVATE", "CENTRE", "PUBLIC"]
            }, 400

        user_id = request.args.get('user_id', type=int, default=None)
        centre_id = request.args.get('centre_id', type=int, default=None)
        text = request.args.get('text', type=str, default="")

        if option.upper() == 'PRIVATE':
            if not user_id:
                return {
                    "message": "Invalid parameter, specify user_id to get private stories",
                }, 400
            social_story_list = SocialStoryModel.find_by_user_id(user_id)
            social_story_list = [ss for ss in social_story_list if ss.is_deleted == False]
            social_story_list = [ss for ss in social_story_list if ss.social_story_patient_association == []]
            return {
                "social_story_list": [social_story.json() for social_story in social_story_list],
                "number_of_stories": len(social_story_list)
            }, 200

        if option.upper() == 'PUBLIC':
            if len(text) > 0:
                social_story_list = SocialStoryModel.find_public_stories(text)
            else:
                return {
                    "message": "Invalid parameter, specify pattern to get public stories",
                }, 400

            return {
                "social_story_list": [social_story.json() for social_story in social_story_list],
                "number_of_stories": len(social_story_list)
            }, 200

        if option.upper() == 'CENTRE':
            if not user_id:
                return {
                    "message": "Invalid parameter, specify user_id to get private stories",
                }, 400
            if not centre_id:
                return {
                    "message": "Invalid parameter, specify centre_id to get private stories",
                }, 400
            social_story_list = SocialStoryModel.find_centre_stories(
                user_id, centre_id)
            return {
                "social_story_list": [social_story.json() for social_story in social_story_list],
                "number_of_stories": len(social_story_list)
            }, 200
