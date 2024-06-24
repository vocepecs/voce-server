from flask_restful import Resource, request, reqparse
from flask_mail import Message
from flask import current_app as app, render_template, make_response
from flask_jwt_extended import jwt_required
from models import UserModel
from password_hash import bcrypt

from security import Criptography



import random
import string


def _generate_random_string(length = 8, only_digits = False):
    if only_digits:
        letters_and_digits = string.digits
    else:
        letters_and_digits = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters_and_digits) for _ in range(length))
    return result_str

class PasswordReset(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email',type=str,required=True)

    def post(self):
        
        args = self.parser.parse_args()
        email = args['email']

        if email is None or len(email) == 0:
            return {'message': 'Email not specified'}, 400
        
        mail_service = app.extensions.get('mail')
        msg = Message(
            subject="Ripristino password VOCE",
            sender="vocepecs@unipv.it",
            recipients=[email]
        )

        new_password = _generate_random_string()

        user = UserModel.find_by_username(email)
        if user is None:
            return {'message': 'Email not found'}, 404
        
        user.password_hash = bcrypt.generate_password_hash(new_password)
        user.save_to_db()

        html = """
            <p>Caro utente,</p>

            <p>Abbiamo creato una password temporanea per il tuo account: <strong>{}</strong></p>

            <p>Utilizza questa password per accedere al tuo account. Ti consigliamo vivamente di modificare questa password il prima possibile per motivi di sicurezza.</p>

            <p>Cordiali saluti,</p>
            <p>Il team di VOCE</p>
        """.format(new_password)
        
        msg.html = html
        mail_service.send(msg)

        # send email
        return {'message': 'Password reset email sent successfully'}, 200
    
class SendEmailConfirmation(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('email',type=str,required=True)

    def post(self):

        email = request.args.get('email', type=str, default=None)

        if email is None or len(email) == 0:
            return {'message': 'Email not specified'}, 400

        user = UserModel.find_by_username(email)
        
        if user is None:
            return {'message': 'Email not found'}, 404
    

        cripto = Criptography()
        obscured_id = cripto.encrypt(str(user.id))

        mail_service = app.extensions.get('mail')
        
        msg = Message(
            subject="Conferma di registrazione VOCE",
            sender="vocepecs@unipv.it",
            recipients=[email]
        )

        

        html = """
            <p>Caro utente,</p>

            <p>Benvenuto in VOCE! Clicca sul link sottostante per confermare la tua mail e iniziare ad utilizzare l'app</p>

            <a href="https://vocepecs.unipv.it/vocecaa-rest/confirm-registration/{}">Conferma email</a>

            <p>Cordiali saluti,</p>
            <p>Il team di VOCE</p>
        """.format(obscured_id)

        msg.html = html
        # try:
        mail_service.send(msg)
        # except  MailException as e:
        #     return {
        #         "error" : "invalid-email-address",
        #         "message" : "The SMTP server can not reach the emai"
        #     }, 400

        # send email
        return {'message': 'Registration Email sent successfully'}, 200
    


class SendDeleteRequestEmail(Resource):
    
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('user_id',type=str,required=True)
    
    @jwt_required()
    def post(self):

        user_id = self.parser.parse_args()['user_id']
        user = UserModel.find_by_id(user_id)
        if not user:
            return {'message': 'User not found'}, 404
        
        mail_service = app.extensions.get('mail')
        msg = Message(
            subject="Conferma di eliminazione account VOCE",
            sender=app.config.get('MAIL_USERNAME'),
            recipients=[user.email]
        )

        cripto = Criptography()
        obscured_id = cripto.encrypt(str(user.id))

        html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Conferma Eliminazione</title>
            </head>
            <body>
                <p>Caro utente,</p>
            <p>
                Abbiamo ricevuto la tua richiesta di eliminazione dell'account e ci dispiace vedere che stai pensando di andartene.<br>
                Prima di dire addio ufficialmente a VOCE, vogliamo assicurarci che tu sia consapevole delle conseguenze di questa azione.
                Clicca sul link sottostante per confermare l'eliminazione del tuo account.
            </p>
            <a href="https://vocepecs.unipv.it/vocecaa-rest/confirm-deletion/{}" style="display:inline-block; padding:10px 20px; background-color:#3498db; color:#ffffff; text-decoration:none;">Conferma Eliminazione</a>
            
            <p>
                Se non hai richiesto tu questa eliminazione o hai cambiato idea e vuoi continuare ad utilizzare VOCE, ignora questa mail e continua ad utilizzare l'applicazione come al solito.
            </p>

            <p>
                Grazie mille per aver fatto parte della nostra community.<br>
                Se ci sono problemi o domande, siamo qui per aiutarti.
            </p>

            <p>A presto,<br>Il team di VOCE</p>
            </body>
            </html>

            
        """.format(obscured_id)

        msg.html = html
        mail_service.send(msg)
        

        return {'message': 'Email confirmation succesfully sended'}, 200