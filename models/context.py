from db import db
from utils.association_tables import ass_image_context


class ContextModel(db.Model):
    __tablename__ = 'contexts'

    id = db.Column(db.Integer, primary_key=True)
    context_type = db.Column(db.Text())

    images = db.relationship(
        "ImageModel",
        secondary=ass_image_context,
    )

    def __init__(self, context_type):
        self.context_type = context_type

    def json(self):
        return {
            'id': self.id,
            'context_type': self.context_type,
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_value(cls, value):
        return cls.query.filter(db.func.lower(cls.context_type) == db.func.lower(value)).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
