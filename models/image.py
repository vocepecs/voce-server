from sqlalchemy.orm import backref
from db import db
from utils.association_tables import image_caa_table, image_patient, image_comunicative_session, ass_image_context, ass_image_grammatical_type, ass_image_synset, ass_image_audio

from models.grammatical_type import GrammaticalTypeModel
from models.context import ContextModel
from models.autism_centre import AutismCentreModel
from models.tag import ImageTagModel, TagModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
from models.image_synonym import ImageSynonymModel


class ImageModel(db.Model):
    __tablename__ = "images"

    # columns
    id = db.Column(db.Integer, primary_key=True)
    id_arasaac = db.Column(db.Integer)
    label = db.Column(db.String(50))
    url = db.Column(db.String(50))
    string_coding = db.Column(db.String)
    usage_counter = db.Column(db.Integer)
    #is_personal = db.Column(db.Boolean)
    insert_date = db.Column(db.DateTime)
    #is_active = db.Column(db.Boolean)
    # grammatical_type_id = db.Column(
    #     db.Integer, db.ForeignKey("grammatical_types.id"))
    # context_id = db.Column(db.Integer, db.ForeignKey("contexts.id"))
    autism_centre_id = db.Column(db.Integer, db.ForeignKey("autism_centres.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # object relation mapping
    # grammatical_type = db.relationship(
    #     "GrammaticalTypeModel", back_populates="images")
    # context = db.relationship("ContextModel", back_populates="images")
    autism_centre = db.relationship("AutismCentreModel", back_populates="images")
    user = db.relationship("UserModel", back_populates="images")

    image_context = db.relationship(
        "ContextModel",
        secondary=ass_image_context,
        backref=db.backref('image_context', lazy='dynamic')
    )

    image_grammatical_type = db.relationship(
        "GrammaticalTypeModel",
        secondary=ass_image_grammatical_type,
        backref=db.backref('image_grammatical_type', lazy='dynamic')
    )

    image_caa_table_association = db.relationship(
        "CaaTableModel",
        secondary=image_caa_table,
        backref=db.backref('image_caa_tables_association', lazy='dynamic',),
    )

    patients = db.relationship(
        "PatientModel",
        secondary=image_patient,
        backref=db.backref('patients', lazy='dynamic'),
    )

    image_comunicative_session_association = db.relationship(
        "ComunicativeSessionModel",
        secondary=image_comunicative_session,
        backref=db.backref(
            'image_comunicative_sessions_association', lazy='dynamic'),
    )

    table_sectors = db.relationship(
        "TableSectorModel",
        secondary="table_sector_image",
        back_populates='images',
        cascade="delete"
    )

    audio_tts = db.relationship(
        "AudioTTSModel",
        secondary = ass_image_audio,
        back_populates="images"
    )

    image_tag = db.relationship("ImageTagModel", back_populates="image", cascade="delete")

    cs_output_images = db.relationship('CsOutputImageModel',
                                       lazy="dynamic",
                                       foreign_keys=[
                                           CsOutputImageModel.image_id],
                                       back_populates="image")
    cs_output_correct_images = db.relationship('CsOutputImageModel',
                                               lazy="dynamic",
                                               foreign_keys=[
                                                   CsOutputImageModel.correct_image_id],
                                               back_populates="correct_image")

    images = db.relationship("ImageSynonymModel",
                             lazy="dynamic",
                             foreign_keys=[ImageSynonymModel.image_id],
                             back_populates="image"
                             )

    synonym_images = db.relationship("ImageSynonymModel",
                             lazy="dynamic",
                             foreign_keys=[ImageSynonymModel.image_syn_id],
                             back_populates="image_synonym"
                             )

    synsets = db.relationship("SynsetModel",
                              secondary=ass_image_synset,
                              )

    patient_cs_logs = db.relationship(
        "PatientCsLogModel",
        lazy="dynamic",
    )

    def __init__(self, id_arasaac, label, url, string_coding, usage_counter, insert_date, autism_centre_id, user_id):
        self.id_arasaac = id_arasaac
        self.label = label
        self.url = url
        self.string_coding = string_coding
        self.usage_counter = usage_counter
        #self.is_personal = is_personal
        self.insert_date = insert_date
        #self.is_active = is_active
        # self.grammatical_type_id = grammatical_type_id
        # self.context_id = context_id
        self.autism_centre_id = autism_centre_id
        self.user_id = user_id

    def json(self):
        return {
            'id': self.id,
            'id_arasaac': self.id_arasaac,
            'label': self.label,
            'url': self.url,
            'string_coding': "b'" + self.string_coding + "'",
            'usage_counter': self.usage_counter,
            #'is_personal': self.is_personal,
            "is_personal": True if self.user_id else False,
            'insert_date': self.insert_date.strftime("%Y-%m-%d"),
            #'is_active': self.is_active,
            'grammatical_type': self.get_grammatical_types(),
            'image_context': self.get_contexts(),
            'autism_centre': self.autism_centre.json() if self.autism_centre else None,
            'tag_list': self.get_tags(),
            'synset_list': self.get_synsets(),
            'audio_tts_list' : self.get_audios()
        }

    def json_simple(self):
        return {
            'id': self.id,
            'tag_list': self.get_tags(),
            'synset_list': self.get_synsets(),
        }
    
    def get_audios(self):
        audio_list = []
        for audio in self.audio_tts:
            audio_list.append(audio.json())
        return audio_list

    def get_tags(self):
        tag_list = []
        for tag in self.image_tag:
            tag_list.append(tag.json())
        return tag_list

    def get_synsets(self):
        synset_list = []
        for synset in self.synsets:
            synset_list.append(synset.json())
        return synset_list

    def get_contexts(self):
        context_list = []
        for context in self.image_context:
            context_list.append(context.json())
        return context_list

    def get_grammatical_types(self):
        grammatical_type_list = []
        for grammatical_type in self.image_grammatical_type:
            grammatical_type_list.append(grammatical_type.json())
        return grammatical_type_list

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, _id):
        print(f"TEST ID {_id}")
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_id_arasaac(cls, _id):
        return cls.query.filter_by(id_arasaac=_id).first()

    @classmethod
    def find_tag_value_for_image(cls, tag_type, image_list_id):
        return [db.session.query(cls, TagModel)
                .join(ImageTagModel, ImageTagModel.image_id == cls.id)
                .join(TagModel, TagModel.id == ImageTagModel.tag_id)
                .filter(ImageTagModel.tag_type == tag_type, cls.id.in_(image_list_id)).all()][0]
    
    @classmethod
    def find_custom_image_by_label(cls,_label):
        return cls.query.filter_by(label=_label, id_arasaac=None).first()
    
    @classmethod
    def find_user_images(cls, _user_id):
        return cls.query.filter_by(user_id = _user_id).all() 
        
