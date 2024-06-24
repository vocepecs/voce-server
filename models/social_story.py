from db import db
from models.patient import PatientSocialStoryModel


class SocialStorySessionModel(db.Model):
    __tablename__ = "social_stories_sessions"

    social_story_id = db.Column(db.ForeignKey(
        'social_stories.id'), primary_key=True)
    comunicative_session_id = db.Column(db.ForeignKey(
        'comunicative_sessions.id'), primary_key=True)
    position = db.Column(db.Integer)
    title = db.Column(db.Text())

    comunicative_session = db.relationship(
        "ComunicativeSessionModel", back_populates="social_story_sessions")
    social_story = db.relationship(
        "SocialStoryModel", back_populates="social_story_sessions")

    def __init__(self, social_story_id, comunicative_session_id, position, title):
        self.social_story_id = social_story_id
        self.comunicative_session_id = comunicative_session_id
        self.position = position
        self.title = title

    def json(self):
        return {
            'ss_id': self.social_story_id,
            'cs_id': self.comunicative_session_id,
            'position':  self.position,
            'title': self.title,
            'image_list': self.comunicative_session.get_session_image_list()
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return [self.social_story_id, self.comunicative_session_id]

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

class SocialStoryModel(db.Model):
    __tablename__ = "social_stories"

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    description = db.Column(db.Text())
    image_string_coding = db.Column(db.Text())
    creation_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean) #NEW
    is_private = db.Column(db.Boolean)
    is_deleted = db.Column(db.Boolean) #NEW
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
    )
    autism_centre_id = db.Column(
        db.Integer,
        db.ForeignKey("autism_centres.id")
    )

    # N to 1 Relationships
    user = db.relationship(
        "UserModel",
        back_populates="social_stories",
    )
    autism_centre = db.relationship(
        "AutismCentreModel",
        back_populates="social_stories",
    )
    social_story_sessions = db.relationship(
        "SocialStorySessionModel",
        back_populates="social_story",
        #cascade="delete, delete-orphan"
    )

    social_story_patient_association = db.relationship(
        "PatientSocialStoryModel",
        back_populates="social_story", 
        foreign_keys=[PatientSocialStoryModel.social_story_id]
    )

    original_social_story_patient = db.relationship(
        "PatientSocialStoryModel",
        back_populates="original_social_story",
        foreign_keys=[PatientSocialStoryModel.original_social_story_id]
    )

    def __init__(self, title, description, image_string_coding, creation_date, is_private, user_id, autism_centre_id,is_active):
        self.title = title
        self.description = description
        self.image_string_coding = image_string_coding
        self.creation_date = creation_date
        self.is_private = is_private
        self.user_id = user_id
        self.autism_centre_id = autism_centre_id
        self.is_deleted=False
        self.is_active = is_active

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'image_string_coding': self.image_string_coding,
            'creation_date': self.creation_date.strftime("%Y-%m-%d"),
            'is_private': self.is_private,
            'autism_centre_id': self.autism_centre_id,
            'is_deleted' : self.is_deleted,
            'session_list': self.get_social_story_sessions(),
            'linked_to_patient' : True if len(self.social_story_patient_association) > 0 else False,
            'is_active' : self.is_active
        }

    def get_social_story_sessions(self):
        session_list = []
        for sss in self.social_story_sessions:
            session_list.append(sss.json())
        session_list = sorted(session_list, key=lambda s: s['position'])
        return session_list

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def if_session_included(self, _session_id):
        is_included = False
        for sss in self.social_story_sessions:
            if _session_id == sss.comunicative_session_id:
                is_included = True
        return is_included

    def get_session_by_id(self, _session_id):
        social_story_session_filtered = list(filter(
            lambda x: x.comunicative_session_id == _session_id, self.social_story_sessions))
        if len(social_story_session_filtered) > 0:
            return social_story_session_filtered[0]

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter(cls.id == _id, cls.is_deleted == False).first()

    @classmethod
    def find_by_user_id(cls, _user_id):
        return cls.query.filter(
            cls.user_id == _user_id,
            cls.is_deleted == False
        ).all()

    @classmethod
    def find_public_stories(cls, pattern):
        search = "%{}%".format(pattern)
        return cls.query.filter(cls.is_private == False, 
                                cls.autism_centre_id == None, 
                                cls.title.ilike(search), 
                                cls.is_deleted == False
                                ).all()
    
    @classmethod
    def find_most_used_stories(cls):
        social_story_list = cls.query.filter(cls.is_private == False, 
                                cls.autism_centre_id == None, 
                                cls.is_deleted == False,
                                ).all()
        social_story_list.sort(key=lambda x: len(x.social_story_patient_association), reverse=True)
        if len(social_story_list) > 5:
            return social_story_list[:5]
        return social_story_list

    @classmethod
    def find_centre_stories(cls, _user_id, _centre_id):
        return cls.query.filter(cls.autism_centre_id == _centre_id, cls.user_id != _user_id, cls.is_deleted == False).all()
