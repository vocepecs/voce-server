from db import db
from utils.association_tables import ass_image_synset


class SynsetModel(db.Model):

    __tablename__ = "synsets"
    id = db.Column(db.Integer, primary_key=True)
    synset_name = db.Column(db.Text())
    synset_name_short = db.Column(db.Text())

    def __init__(self, synset_name,synset_name_short):
        self.synset_name = synset_name
        self.synset_name_short = synset_name_short
    
    def json(self):
        return {
            'id' : self.id,
            'synset_name' : self.synset_name,
            'synset_name_short' : self.synset_name_short
        }

    images = db.relationship("ImageModel",
    secondary=ass_image_synset,
    )
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
    
    @classmethod
    def find_by_name(cls, _name):
        return cls.query.filter_by(synset_name = _name).first()

    