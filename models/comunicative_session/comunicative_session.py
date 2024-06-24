from db import db
from utils.association_tables import ass_cs_logs


class ComunicativeSessionModel(db.Model):
    __tablename__ = 'comunicative_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"))
    caa_table_id = db.Column(db.Integer, db.ForeignKey("caa_tables.id"))
    text_phrase = db.Column(db.String(300))
    date = db.Column(db.DateTime)

    # N to 1 Relationships
    user = db.relationship("UserModel", back_populates="comunicative_sessions")
    patient = db.relationship(
        "PatientModel",
        back_populates="comunicative_sessions",
    )
    
    caa_table = db.relationship(
        "CaaTableModel",
        back_populates="comunicative_sessions",
        cascade="delete"
    )

    # N to N Relationships
    cs_logs = db.relationship(
        "SessionLogModel",
        secondary=ass_cs_logs,
        backref=db.backref('cs_logs', lazy='dynamic')
    )

    # 1 to N Relationships
    cs_output_images = db.relationship('CsOutputImageModel',lazy="dynamic", cascade="delete, delete-orphan")
    social_story_sessions = db.relationship('SocialStorySessionModel', back_populates="comunicative_session") #, cascade="delete, delete-orphan")

    def __init__(self, user_id, patient_id, caa_table_id, text_phrase,date):
        self.user_id = user_id
        self.patient_id = patient_id
        self.caa_table_id = caa_table_id
        self.text_phrase = text_phrase
        self.date = date

    def json(self):
        return {
            'id': self.id,
            'text_phrase': self.text_phrase,
        }

    def get_session_image_list(self):
        image_list = []
        # image_list_sorted = []
        for cs_image in self.cs_output_images:
            if cs_image.output_state_id != 3:
                position = cs_image.final_position if cs_image.final_position != None else cs_image.initial_position
                image = cs_image.correct_image if cs_image.correct_image_id else cs_image.image
                image_list.append({
                    "image" : image,
                    "position" : position,
                })
        print(f'image_list: {image_list}')
        # image_list = sorted(list_to_be_sorted, key=lambda d: d['name']) 
        image_list.sort(key=lambda x: x['position'])
        return [image['image'].json() for image in image_list]  

    
    def get_output_image_by_id(self,_id):
        for cs_oi in self.cs_output_images:
            if cs_oi.correct_image_id == _id:
                return cs_oi
            elif cs_oi.image_id == _id:
                return cs_oi

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def update_to_db(self):
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
