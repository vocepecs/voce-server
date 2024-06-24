from db import db


class AutismCentreModel(db.Model):
    __tablename__ = 'autism_centres'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    address = db.Column(db.String(80))
    secret_code = db.Column(db.String(7))

    # 1 to N Relationships
    users = db.relationship('UserModel', lazy="dynamic")
    images = db.relationship('ImageModel', lazy="dynamic")
    caa_tables = db.relationship('CaaTableModel', lazy="dynamic")
    social_stories = db.relationship("SocialStoryModel", lazy="dynamic")

    def __init__(self, name, address, secret_code):
        self.name = name
        self.address = address
        self.secret_code = secret_code

    def json(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'secret_code': self.secret_code,
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
