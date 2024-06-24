from db import db


class UserRolesModel(db.Model):
    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))

    # users = db.relationship('UserModel', back_populates="user_roles")
    users = db.relationship('UserModel', lazy="dynamic")

    def __init__(self, title):
        self.title = title

    def json(self):
        return {
            'id': self.id,
            'title': self.title,
        }
