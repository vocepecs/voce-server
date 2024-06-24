from db import db
from utils.association_tables import ass_image_audio
from sqlalchemy import func

class AudioTTSModel(db.Model):
    __tablename__ = "audio_tts"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.Text())
    gender = db.Column(db.Text())
    model = db.Column(db.Text())
    framework = db.Column(db.Text())
    base64_string = db.Column(db.Text())


    images = db.relationship(
        "ImageModel",
        secondary = ass_image_audio,
        back_populates = "audio_tts"
    )

    def __init__(self, label, gender, model, framework, base64_string):
        self.label = label
        self.gender = gender
        self.model = model
        self.framework = framework
        self.base64_string = base64_string
    

    def json(self):
        return {
            "id" : self.id,
            "label" : self.label,
            "gender" : self.gender,
            "model" : self.model,
            "framework" : self.framework,
            "base64_string" : self.base64_string,
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls,_id):
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_label(cls,_label):
        return cls.query.filter(func.lower(cls.label) == _label.lower()).all()


