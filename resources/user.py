from blacklist import BLACKLIST
from flask import current_app as app, render_template, make_response
from flask_mail import Message
from flask_jwt_extended.utils import get_jti, get_jwt, get_jwt_identity
from flask_restful import Resource, reqparse, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    verify_jwt_in_request,
    jwt_required,
    get_jwt_identity,
    get_jwt)
from password_hash import bcrypt
from models.user import UserModel, EnrollmentModel
from models.caa_table import CaaTableModel
from models.social_story import SocialStoryModel

from security import Criptography

from datetime import datetime, timedelta
import re

class UserTest(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email',type=str,required=True)
        self.parser.add_argument('password',type=str,required=True)
    
    def post(self):
        # args = self.parser.parse_args()
        # pw_hash = bcrypt.generate_password_hash(args['password'])

        # user = UserModel(
        #     email=args['email'],
        #     password=args['password'],
        #     role_id=1,
        #     name="Mattia Test",
        #     autism_centre_id=None
        # )
        # user.password_hash = pw_hash
        # user.save_to_db()

        # return {
        #     "message": "User created successfully.",
        #     "password_hash": pw_hash.decode('utf-8'),
        #     "password_hash_type": type(pw_hash).__name__,
        #     "password_hash_check": bcrypt.check_password_hash(pw_hash, args['password']),
        # }, 201
        # user_list = UserModel.query.all()
        # for user in user_list:
        #     if not user.password_hash:
        #         pw_hash = bcrypt.generate_password_hash(user.password)
        #         user.password_hash = pw_hash
        #         user.save_to_db()
        return {
            "message" : "Ok"
        }, 200
    
    def get(self):
        
        args = self.parser.parse_args()
        user = UserModel.find_by_username(args['email'])
        if bcrypt.check_password_hash(user.password_hash, args['password']):
            return {
                "message": "User found successfully.",
                "user": user.json(),
            }, 200
        
        return {
            "message": "Password not match.",
        }, 401
        





class User(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email',type=str,required=True)
        self.parser.add_argument('old_password',type=str,required=False)
        self.parser.add_argument('password',type=str,required=True)
        self.parser.add_argument('role_id',type=int,required=False)
        self.parser.add_argument('name',type=str,required=False)
        self.parser.add_argument('autism_centre_id',type=int,required=False)
        self.parser.add_argument('patient_list', type=dict, action='append')
    
    @jwt_required()
    def post(self):
        args = self.parser.parse_args()
    
        if UserModel.find_by_username(args['email']):
            return {"message": "A user with that username already exists"}, 400

        user = UserModel(
            email=args['email'],
            role_id=args['role_id'],
            name=args['name'],
            autism_centre_id=args['autism_centre_id']
        )

        user.password_hash = bcrypt.generate_password_hash(args['password'])

        user_id = user.save_to_db()
        new_user = UserModel.find_by_id(user_id)

        return {
            "message": "User created successfully.",
            "user": new_user.json()
        }, 201

    @jwt_required()
    def put(self):
        args = self.parser.parse_args()
        user = UserModel.find_by_username(args['email'])

        # Aggiorno gli attributi di user senza considerare il campo patient_list che devo usarlo per gli Enrollments
        for attr in [key for key in args.keys() if key != 'patient_list']:
            if args[attr]:
                setattr(user, attr, args[attr])

        # Aggiorno la password
        if args['old_password']:
            if bcrypt.check_password_hash(user.password_hash, args['old_password']):
                user.password_hash = bcrypt.generate_password_hash(args['password'])
            else:
                return {
                    "title" : "password-not-match",
                    "message": "Old password not match.",
                }, 401        
        
        user.save_to_db()
        
        # Aggiorno gli Enrollments (active user)
        if args['patient_list']:
            for patient in args['patient_list']:
                enrollment = EnrollmentModel.find_by_id(user.id, patient['id'])
                enrollment.is_active = patient['is_active']
                enrollment.save_to_db()

        # Aggiorno PatientTable (active table)
        if args['patient_list']:
            for patient_dict in args['patient_list']:
                for caa_table_dict in patient_dict['table_list']:
                    caa_table = CaaTableModel.find_by_id(caa_table_dict['id'])
                    caa_table.is_active = caa_table_dict['is_active']
                    caa_table.save_to_db()


        # Aggiorno PatientStory (active story)
        if args['patient_list']:
            for patient_dict in args['patient_list']:
                for social_story_dict in patient_dict['social_story_list']:
                    social_story = SocialStoryModel.find_by_id(social_story_dict.get("id"))
                    if social_story:
                        social_story.is_active = social_story_dict.get("is_active")
                        social_story.save_to_db()
            
            
        
        return {
            "message": "User updated successfully.",
        }, 200

    @jwt_required()
    def get(self):
        user_id = request.args.get('user_id', None)
        user = UserModel.find_by_id(user_id)
        if not user:
            return {'message': 'User not found'}, 404
        return user.json(), 200

    @jwt_required()
    def delete(self):
        user_id = request.args.get('user_id', None)
        user = UserModel.find_by_id(user_id)
        if not user:
            return {'message': 'User not found'}, 404
        user.delete_from_db()
        return {'message': 'User deleted.'}, 200


class HandShake(Resource):
    @jwt_required()
    def get(self):
        return {
            'message': 'You Are logged in'
        }, 200


class UserSignUp(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email',type=str,required=True)
        self.parser.add_argument('password',type=str,required=True)
        self.parser.add_argument('role_id',type=int,required=False)
        self.parser.add_argument('name',type=str,required=False)
        self.parser.add_argument('autism_centre_id',type=int,required=False)
        self.parser.add_argument('email_subscription',type=bool,required=False)
        self.parser.add_argument('first_access',type=bool,required=False)

    def _is_valid_email(self, email):
        regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(regex, email)

    def post(self):

        args = self.parser.parse_args()
        
        if UserModel.find_by_username(args['email']):
            return {
                "message": "A user with that username already exists",
                "error": "user-already-exists",
                }, 400
        
        if not self._is_valid_email(args['email']):
            return {
                "message": "Invalid email format",
                "error": "invalid-email-format",
                }, 400
        
        
        user = UserModel(
            email=args['email'],
            role_id=args['role_id'],
            name=args['name'],
            autism_centre_id=args['autism_centre_id'],
            first_access=args['first_access'],
            subscription_date=datetime.now()
        )
        
        if args['email_subscription']:
            user.email_subscription = args['email_subscription']

        user.password_hash = bcrypt.generate_password_hash(args['password'])
        user_id = user.save_to_db()
        new_user = UserModel.find_by_id(user_id)
        
        return {
            "message": "User created successfully.",
            "user": new_user.json(),
        }, 201

class UserLogin(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email',type=str,required=True)
        self.parser.add_argument('password',type=str,required=True)

    
    def post(self):
        # get data from parser
        args = self.parser.parse_args()

        # find user in database
        user = UserModel.find_by_username(args['email'])

        if not user:
            return {'message': 'User not found'}, 404
        
        if user.enabled == False:
            return {
                'error': 'user-not-enabled',
                'message': 'User not enabled'
            }, 401

        if bcrypt.check_password_hash(user.password_hash, args['password']):
            
            if not user.email_verified:
                return {
                    'error': 'user-not-verified',
                    'message': 'User not verified',
                }, 401

            access_token = create_access_token(identity=user.id, fresh=True)
            refresh_token = create_refresh_token(user.id)
            return {
                'user_id': user.id,
                'access_token': access_token,
                'refresh_token': refresh_token,
            }, 200
        return {
            'error': 'invalid-credentials',
            'message': 'Invalid credentials'
        }, 401


class UserLogout(Resource):
    @jwt_required()
    def post(self):
        # jti is "JWT ID", a unique identifier for a JWT.
        jti = get_jwt()["jti"]
        BLACKLIST.add(jti)
        return {'message': 'Successfully logged out.'}, 200


class TokenRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {'access_token': new_token}, 200

class ConfirmRegistration(Resource):
    def get(self, token):
        
        cripto = Criptography()
        user_id = cripto.decrypt(token)
        user = UserModel.find_by_id(int(user_id))


        if user.email_verified == False:
            user.email_verified = True
            user.save_to_db()


        html_content = render_template('email_verified_confirm.html')
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        response.status_code = 200

        return response
        
class ConfirmDeletion(Resource):
    def get(self, token):

        cripto = Criptography()
        user_id = cripto.decrypt(token)
        user = UserModel.find_by_id(user_id)

        if not user:
            return {'message': 'User not found'}, 404
        
        user.enabled = False
        user.save_to_db()
        
        mail_service = app.extensions.get('mail')
        msg = Message(
            subject="Conferma di eliminazione account VOCE",
            sender=app.config.get('MAIL_USERNAME'),
            recipients=[app.config.get('MAIL_USERNAME')]
        )

        deletion_deadline = datetime.now() + timedelta(days=30)
        deletion_deadline = deletion_deadline.strftime("%d/%m/%Y") 
        
        html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Richiesta Eliminazione</title>
            </head>
            <body>
                <h1>Richiesta Eliminazione Account</h1>
                <p>Abbiamo ricevuto una richiesta di eliminazione dell'account da parte di un utente.</p>
                <p>
                    Eliminazione richiesta entro il: <strong>{deletion_deadline}</strong><br>
                    Utente: <strong>{user.email}</strong><br>
                    UID: <strong>{user.id}</strong><br>
                </p>
            </body>
            </html>

            
        """.format(user.id)

        msg.html = html
        mail_service.send(msg)
        
        html_content = render_template('account_delete_confirm.html')
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        response.status_code = 200

        return response       