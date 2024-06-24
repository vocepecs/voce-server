from db import db
from utils.association_tables import image_patient  # , patient_caa_table
from datetime import date


class PatientSocialStoryModel(db.Model):
    __tablename__ = 'patient_social_story'

    patient_id = db.Column(db.Integer, db.ForeignKey(
        "patients.id"), primary_key=True)
    social_story_id = db.Column(db.Integer, db.ForeignKey(
        "social_stories.id"), primary_key=True)
    original_social_story_id = db.Column(
        db.Integer, db.ForeignKey("social_stories.id"))

    patient = db.relationship(
        "PatientModel", back_populates="social_story_patient_association")
    social_story = db.relationship(
        "SocialStoryModel", back_populates="social_story_patient_association", foreign_keys=[social_story_id])
    original_social_story = db.relationship(
        "SocialStoryModel", back_populates="original_social_story_patient", foreign_keys=[original_social_story_id])

    def __init__(self, patient_id, social_story_id, original_social_story_id):
        self.patient_id = patient_id
        self.social_story_id = social_story_id
        self.original_social_story_id = original_social_story_id

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return [self.patient_id, self.social_story_id, self.original_social_story_id]

    def update_to_db(self):
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()


class PatientCaaTableModel(db.Model):
    __tablename__ = 'patient_caa_table'

    patient_id = db.Column(db.Integer, db.ForeignKey(
        "patients.id"), primary_key=True)
    caa_table_id = db.Column(db.Integer, db.ForeignKey(
        "caa_tables.id"), primary_key=True)
    original_caa_table_id = db.Column(
        db.Integer, db.ForeignKey("caa_tables.id"), primary_key=True)

    patient = db.relationship(
        "PatientModel", back_populates="table_patient_association")
    caa_table = db.relationship(
        "CaaTableModel", back_populates="table_patient_association", foreign_keys=[caa_table_id])
    original_caa_table = db.relationship(
        "CaaTableModel", back_populates="original_table_patient", foreign_keys=[original_caa_table_id])

    def __init__(self, patient_id, caa_table_id, original_caa_table_id):
        self.patient_id = patient_id
        self.caa_table_id = caa_table_id
        self.original_caa_table_id = original_caa_table_id

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return [self.patient_id, self.caa_table_id, self.original_caa_table_id]

    def update_to_db(self):
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()


class PatientModel(db.Model):
    __tablename__ = 'patients'

    # columns
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(30))
    enroll_date = db.Column(db.DateTime)
    communication_level = db.Column(db.Integer)
    notes = db.Column(db.String(500))
    vocal_profile = db.Column(db.Text())
    social_story_view_type = db.Column(db.Text())
    gender = db.Column(db.Text())
    full_tts_enabled = db.Column(db.Boolean, default=False)

    # object relations mapping
    comunicative_evaluations = db.relationship(
        "ComunicativeEvaluationModel", lazy="dynamic")

    enrollments = db.relationship("EnrollmentModel", back_populates="patient")

    table_patient_association = db.relationship(
        "PatientCaaTableModel", back_populates="patient")
    
    social_story_patient_association = db.relationship(
        "PatientSocialStoryModel", back_populates="patient"
    )

    images = db.relationship(
        "ImageModel",
        secondary=image_patient,
    )

    comunicative_sessions = db.relationship(
        "ComunicativeSessionModel", lazy="dynamic"
    )

    patient_cs_logs = db.relationship(
        "PatientCsLogModel",
        lazy="dynamic",
    )

    def __init__(self, nickname, enroll_date, communication_level, notes, vocal_profile, social_story_view_type, gender, full_tts_enabled=False):
        self.nickname = nickname
        self.enroll_date = enroll_date
        self.communication_level = communication_level
        self.notes = notes
        self.vocal_profile = vocal_profile
        self.social_story_view_type = social_story_view_type
        self.gender = gender
        self.full_tts_enabled = full_tts_enabled

    def json(self):
        return {
            'id': self.id,
            'nickname': self.nickname,
            'enroll_date': self.enroll_date.strftime("%Y-%m-%d"),
            'communication_level': self.communication_level,
            'notes': self.notes,
            'table_list': self.get_tables(),
            'social_story_list': self.get_social_stories(),
            'image_list': self.get_images(),
            'vocal_profile': self.vocal_profile,
            'social_story_view_type': self.social_story_view_type,
            'gender' : self.gender,
            'full_tts_enabled': self.full_tts_enabled,
        }

    def set_active_table(self, table_id):
        for table in self.caa_tables:
            table.is_active = False
            if table.id == table_id:
                table.is_active = True
        db.session.commit()

    def get_social_stories(self):
        social_story_list = []
        for ass in self.social_story_patient_association:
            if ass.social_story.is_deleted == False:
                social_story_list.append(ass.social_story.json())
        return social_story_list

    def get_tables(self):
        table_list = []
        for tp_ass in self.table_patient_association:
            table_list.append(tp_ass.caa_table.json())
        return [table for table in table_list if table['is_deleted'] == False]

    def get_images(self):
        image_list = []
        for image in self.images:
            image_list.append(image.json())
        return image_list

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
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
