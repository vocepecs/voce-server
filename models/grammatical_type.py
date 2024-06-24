from db import db
from utils.association_tables import ass_image_grammatical_type


class GrammaticalTypeModel(db.Model):
    __tablename__ = "grammatical_types"

    id = db.Column(db.Integer, primary_key=True)
    tint_tag = db.Column(db.String(2))
    type = db.Column(db.String(40))

    # images = db.relationship('ImageModel', lazy="dynamic")
    images = db.relationship(
        "ImageModel",
        secondary=ass_image_grammatical_type,
    )

    pos_tagging_results = db.relationship(
        "PosTaggingModel",
        lazy="dynamic",
    )

    def __init__(self, type, tint_tag):
        self.type = type
        self.tint_tag = tint_tag

    def json(self):
        return {
            'id': self.id,
            'type': self.type,
            'tint_tag':self.tint_tag,
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
        return cls.query.filter(db.func.lower(cls.type) == db.func.lower(value)).first()
    
    @classmethod
    def find_by_tint_tag(cls,tag):
        return cls.query.filter(cls.tint_tag == tag.upper()).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
