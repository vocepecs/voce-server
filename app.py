import torch.multiprocessing as mp
import os

from flask import Flask, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from password_hash import bcrypt
from datetime import timedelta

from resources.user import User, UserLogin, TokenRefresh, UserLogout, HandShake, UserTest, UserSignUp, ConfirmRegistration, ConfirmDeletion
from resources.patient import Patient, PatientEnrollment, PatientList, ActivePatient, PatientImageAssociation,PatientSocialStory
from resources.image import Image, ImageList, ImageContext, ImageGrammaticalType, AllImageList
from resources.caa_table import CaaTable, AddImageToTable, CaaTableList, ActiveCaaTable, CaaTableListTest
from resources.tag import TagManager, TagList, ImageTagAssociaton, TagValueStem
from resources.grammatical_type import GrammaticalTypeManager,GrammaticalTypeList
from resources.context import ContextManager,ContextList
from resources.search_algorithm import Search, Translate,ContextTable
from resources.centre import AutismCentre, AutismCentreList, VerifyCode
from resources.suggested import Suggested
from resources.comunicative_session import UpdateComunicativeSession
from resources.patient_cs_log import PatientCsLog
from resources.cs_output_image import CsOutputImage, CsOutputPushImage
from resources.social_story import SocialStory, SocialStoriesList
from resources.translate import TranslateAlgorithm
from resources.tint import Tint
from resources.synset import Synset
from resources.image import ImageSynonym
from resources.audio_tts import AudioTTS

from resources.maintenance import ImageMaintenance, CaaTableMaintenance

from resources.wsd import WordSenseDisambiguation

from resources.email_sender import PasswordReset, SendEmailConfirmation, SendDeleteRequestEmail


# Risorse analisi dati

from resources.most_frequent_images import ImageFrequenceGraph
from resources.patient_phrases_stat import PhraseStatistics
from resources.distinct_pittograms import DistinctPictograms
from resources.grammatical_types_usage import GrammaticalTypesUsage
from resources.context_frequency import ContextFrequenceGraph


from resources.test import TestServer
from blacklist import BLACKLIST

from resources.search2 import Translate2
from resources.suggested2 import Suggested2

app = Flask(__name__)

app.config['DEBUG'] = True


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['JWT_SECRET_KEY'] = os.environ.get('API_KEY') 

app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Email service configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER') 
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') 
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') 
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False

mail = Mail(app)
api = Api(app)
jwt = JWTManager(app)
bcrypt = bcrypt.init_app(app)

@jwt.additional_claims_loader
def add_claims_to_jwt(identity):
    if identity == 1:
        return {'is_admin': True}
    return {'is_admin': False}


@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    app.logger.info(jwt_payload)
    return jwt_payload['jti'] in BLACKLIST


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    token_type = jwt_payload['type']
    return jsonify({
        'description': 'The token has expired.',
        'error': 'token_expired',
        'type': token_type,
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'description': 'Signature verification failed.',
        'error': 'invalid_token',
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'description': 'Request does not contain an access token.',
        'error': 'unauthorized_request',
    }), 401

@jwt.needs_fresh_token_loader
def token_not_fresh_callback():
    return jsonify({
        'description': 'The token is not fresh.',
        'error': 'fresh_token_required',
    }), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'description': 'The token has been revoked.',
        'error': 'token_revoked',
    }), 401


APP_ROOT = '/vocecaa-rest'

api.add_resource(TestServer, APP_ROOT+'/test-server')
api.add_resource(UserTest, APP_ROOT+'/user-test')
api.add_resource(PasswordReset, APP_ROOT+'/password-reset')
api.add_resource(SendEmailConfirmation, APP_ROOT+'/send-email-confirmation')
api.add_resource(ConfirmRegistration,APP_ROOT+'/confirm-registration/<string:token>')
api.add_resource(SendDeleteRequestEmail, APP_ROOT+'/delete-request')
api.add_resource(ConfirmDeletion, APP_ROOT+'/confirm-deletion/<string:token>')


api.add_resource(User,APP_ROOT+'/user')
api.add_resource(UserSignUp,APP_ROOT+'/signup')
api.add_resource(UserLogin, APP_ROOT+'/login')
api.add_resource(HandShake, APP_ROOT+'/handshake')
api.add_resource(TokenRefresh, APP_ROOT+'/refresh')
api.add_resource(UserLogout, APP_ROOT+'/logout')

api.add_resource(AutismCentre, APP_ROOT+'/autism-centre')
api.add_resource(AutismCentreList, APP_ROOT+'/autism-centre/all-centres')
api.add_resource(VerifyCode, APP_ROOT+'/autism-centre/verify-code')

api.add_resource(Patient, APP_ROOT+'/patient')
api.add_resource(PatientList, APP_ROOT+'/patients')
api.add_resource(PatientEnrollment, APP_ROOT+'/patient/enroll-patient')
api.add_resource(ActivePatient, APP_ROOT+'/patient/active-patient')
api.add_resource(PatientSocialStory, APP_ROOT+'/patient/add-social-story')
api.add_resource(PatientImageAssociation,APP_ROOT+'/patient/add-image')

api.add_resource(Image, APP_ROOT+'/image')
api.add_resource(ImageList,APP_ROOT+'/images')
api.add_resource(ImageContext, APP_ROOT+'/image/add-context')
api.add_resource(ImageGrammaticalType, APP_ROOT+'/image/add-grammatical-type')

api.add_resource(CaaTableList, APP_ROOT+'/caa-tables')
api.add_resource(CaaTableListTest, APP_ROOT+'/caa-tables-test')
api.add_resource(CaaTable, APP_ROOT+'/caa-table')
api.add_resource(AddImageToTable,APP_ROOT+'/caa-table/add-image')
api.add_resource(ActiveCaaTable, APP_ROOT+'/caa-table/active-caa-table')

api.add_resource(TagManager, APP_ROOT+'/tag')
api.add_resource(TagValueStem, APP_ROOT+'/all-tags/add-stemmatized-value')
api.add_resource(TagList,APP_ROOT+'/all-tags')
api.add_resource(ImageTagAssociaton, APP_ROOT+'/add-tag-to-image')

api.add_resource(GrammaticalTypeManager, APP_ROOT+'/grammatical-type')
api.add_resource(GrammaticalTypeList, APP_ROOT+'/all-grammatical-types')

api.add_resource(ContextManager, APP_ROOT+'/context')
api.add_resource(ContextList, APP_ROOT+'/all-contexts')


api.add_resource(Search, APP_ROOT+'/search')
api.add_resource(Translate, APP_ROOT+'/translate')
api.add_resource(Suggested,APP_ROOT+ '/search-suggested')
api.add_resource(ContextTable, APP_ROOT+'/contextTable')


api.add_resource(UpdateComunicativeSession, APP_ROOT+'/comunicative-session/update-output-image')
api.add_resource(CsOutputImage, APP_ROOT+'/cs_output_image')
api.add_resource(CsOutputPushImage, APP_ROOT+'/add-cs-output-image')
api.add_resource(PatientCsLog, APP_ROOT+'/patient-cs-logs')

api.add_resource(SocialStory, APP_ROOT+'/social-story')
api.add_resource(SocialStoriesList, APP_ROOT+'/social-stories')
api.add_resource(TranslateAlgorithm, APP_ROOT+'/translate-algorithm')

api.add_resource(Tint, APP_ROOT+'/nlp/tint')
api.add_resource(Synset, APP_ROOT+'/nlp/synset')
api.add_resource(ImageSynonym, APP_ROOT+'/add-image-synonyms')
api.add_resource(Translate2,APP_ROOT+'/translate_v2')
api.add_resource(Suggested2,APP_ROOT+ '/search-suggested2')

api.add_resource(WordSenseDisambiguation, APP_ROOT+ '/wsd')

# Aggiunta risorse di analisi
api.add_resource(ImageFrequenceGraph, APP_ROOT + '/most-frequent-images')
api.add_resource(PhraseStatistics, APP_ROOT + '/patient-phrases-stat')
api.add_resource(DistinctPictograms, APP_ROOT + '/distinct-pictograms')
api.add_resource(GrammaticalTypesUsage, APP_ROOT + '/grammatical-types-usage')
api.add_resource(ContextFrequenceGraph, APP_ROOT + '/context-frequency')
# Aggiunta risorse mainteance
# api.add_resource(TestImageFrequenceGraph, APP_ROOT+"/test-most-frequent-images")
api.add_resource(ImageMaintenance, APP_ROOT+'/image-maintenance')
api.add_resource(CaaTableMaintenance, APP_ROOT+'/caa-table-maintenance')


api.add_resource(AllImageList, APP_ROOT+'/all-images')

api.add_resource(AudioTTS, APP_ROOT+'/audio_tts')


if __name__ == '__main__':
    from db import db
    db.init_app(app)

    if app.config['DEBUG']:
        @app.before_first_request
        def create_tables():
            db.create_all()

    
    mp.set_start_method('spawn',force=True)
    app.run(port=5000)
