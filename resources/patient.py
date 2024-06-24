from models.caa_table import CaaTableModel
from models.social_story import SocialStoryModel, SocialStorySessionModel
from models.table_sector import TableSectorModel
from models.user import UserModel
from models.image import ImageModel
from models import EnrollmentModel
from flask_restful import Resource, reqparse, request
from datetime import datetime

from models.patient import PatientModel

from flask_jwt_extended import jwt_required

_patient_image_parser = reqparse.RequestParser()
_patient_image_parser.add_argument(
    'patient_list',
    type=int,
    action='append'
)

# ? Si può portare nel POST Method di Image
class PatientImageAssociation(Resource):
    @jwt_required()
    def post(self):
        data = _patient_image_parser.parse_args()
        patient_list = data['patient_list']
        image_id = request.args.get('image_id', None)

        if len(patient_list) == 0 or patient_list == None:
            return {
                "Message": "No patients were provided"
            }, 400

        if image_id == None:
            return {
                "Message": "No image was provided"
            }, 400

        for patient_id in patient_list:
            patient = PatientModel.find_by_id(patient_id)
            image = ImageModel.find_by_id(image_id)
            patient.images.append(image)
            patient.save_to_db()

        return {
            "Message": "Patients images association done"
        }, 200

# ? Si può portare nel POST Method di Patient
class PatientEnrollment(Resource):
    @jwt_required()
    def post(self):
        patient_id = request.args.get('patient_id', None)
        user_id = request.args.get('user_id', None)
        user = UserModel.find_by_id(user_id)
        autism_centre_id = user.autism_centre_id

        # Se user associato ad autism_centre
        # allora associo patient a tutti gli user
        if autism_centre_id:
            print(f'autism_centre_id : {autism_centre_id}')
            user_list = UserModel.find_by_autism_centre(autism_centre_id)
            for user in user_list:
                enrollment = EnrollmentModel(user.id, patient_id, False)
                user.enrollments.append(enrollment)
                user.save_to_db()

        # Altrimenti associo patient al solo utente (indipendente)
        else:
            enrollment = EnrollmentModel(user.id, patient_id, False)
            user.enrollments.append(enrollment)
            user.save_to_db()

        return {"message": "Patient enrolled successfully."}, 201

# ? Si può portare nel PUT Method di Patient
class ActivePatient(Resource):
    @jwt_required()
    def post(self):
        patient_id = request.args.get('patient_id', None)
        user_id = request.args.get('user_id', None)
        if not patient_id:
            return {"message": "patient_id parameter not found."}, 400
        if not user_id:
            return {"message": "user_id parameter not found."}, 400
        user = UserModel.find_by_id(user_id)
        user.set_active_patient(int(patient_id))
        return {"message": "active patient update sucessfully."}, 200

    @jwt_required()
    def get(self):
        user_id = request.args.get('user_id', None)
        if not user_id:
            return {"message": "user_id parameter not found."}, 400
        patient = UserModel.find_active_patient(user_id)
        if not patient:
            return {"message": "No active patient found"}, 404
        return patient.json(), 200
    


def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")


class Patient(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('nickname', type=str)
        self.parser.add_argument('enroll_date', type=parse_date)
        self.parser.add_argument('communication_level', type=str)
        self.parser.add_argument('notes', type=str)
        self.parser.add_argument('vocal_profile', type=str)
        self.parser.add_argument('social_story_view_type', type=str)
        self.parser.add_argument('gender', type=str)
        self.parser.add_argument('full_tts_enabled', type=bool)
        # self.parser.add_argument('is_cs_active', type=bool)
        # self.parser.add_argument('user_id', type=int)

    @jwt_required()
    def post(self):
        args = self.parser.parse_args()
        patient = PatientModel(**args)
        patient_id = patient.save_to_db()
        return {
            "message": "Patient created successfully.",
            "patient_id": patient_id,
        }, 201

    @jwt_required()
    def put(self):
        patient_id = request.args.get('patient_id', type=int, default=None)
        patient = PatientModel.find_by_id(patient_id)
        args = self.parser.parse_args()
        print(F"patient: {args}")
        for attr in args.keys():
            if args[attr] is not None:
                setattr(patient, attr, args[attr])
        patient.save_to_db()
        return {
            "message": "Patient updated successfully.",
        }, 200

    @jwt_required()
    def get(self):
        patient_id = request.args.get('patient_id', type=int, default=None)
        patient = PatientModel.find_by_id(patient_id)
        if not patient:
            return {"message": "Patient not found"}, 404
        return patient.json(), 200

    @jwt_required()
    def delete(self):
        patient_id = request.args.get('patient_id', None)
        user = PatientModel.find_by_id(patient_id)
        if not user:
            return {'message': 'Patient not found'}, 404
        user.delete_from_db()
        return {'message': 'User deleted.'}, 200


# ? Devo gestirla come le tabelle con una N:N e salvando la storia di origine
class PatientSocialStory(Resource):
    
    @jwt_required()
    def post(self):
        social_story_id = request.args.get('social_story_id', None)
        patient_id = request.args.get('patient_id', None)
        patient = PatientModel.find_by_id(patient_id)

        if not patient:
            return {"message": "Patient not found"}, 404
        social_story = SocialStoryModel.find_by_id(social_story_id)
        if not social_story:
            return {"message": "Social story not found"}, 404

        new_social_story = SocialStoryModel(
            title=social_story.title,
            description=social_story.description,
            image_string_coding=social_story.image_string_coding,
            creation_date=social_story.creation_date,
            is_user_private=True,
            patient_id=patient_id,
            user_id=social_story.user_id,
            is_centre_private=social_story.is_centre_private,
            autism_centre_id=social_story.autism_centre_id
        )

        new_social_story_id = new_social_story.save_to_db()
        new_social_story = SocialStoryModel.find_by_id(new_social_story_id)
        for session in social_story.social_story_sessions:
           session_copy = SocialStorySessionModel(
            new_social_story_id,
            session.comunicative_session_id,
            session.position,
            session.title,
           )
           new_social_story.social_story_sessions.append(session_copy)
        #new_social_story.social_story_sessions = social_story.social_story_sessions
        new_social_story.save_to_db()
        return {"message": "Social Story linked successfully."}, 200

class PatientList(Resource):
    @jwt_required()
    def get(self):
        return {"patients": [patient.json() for patient in PatientModel.query.all()]}
