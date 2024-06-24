from db import db
from models.patient import PatientCaaTableModel
# from utils.association_tables import patient_caa_table


class CaaTableModel(db.Model):
    __tablename__ = "caa_tables"

    # columns
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    table_format = db.Column(db.Text())
    creation_date = db.Column(db.DateTime)
    last_modify_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean)
    is_private = db.Column(db.Boolean)
    description = db.Column(db.Text())
    image_string_coding = db.Column(db.Text())
    is_deleted = db.Column(db.Boolean)
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
        back_populates="caa_tables",
    )
    autism_centre = db.relationship(
        "AutismCentreModel",
        back_populates="caa_tables",
    )

    # object relations mapping
    # patient_caa_table_association = db.relationship(
    #     "PatientModel",
    #     secondary=patient_caa_table,
    #     backref=db.backref('patients_caa_tables_association', lazy='dynamic'),
    # )

    table_patient_association = db.relationship("PatientCaaTableModel",back_populates="caa_table", foreign_keys=[PatientCaaTableModel.caa_table_id])
    original_table_patient = db.relationship("PatientCaaTableModel",back_populates="original_caa_table", foreign_keys=[PatientCaaTableModel.original_caa_table_id])

    table_sectors = db.relationship(
        "TableSectorModel", back_populates="caa_table",  cascade="delete, delete-orphan")

    comunicative_sessions = db.relationship(
        "ComunicativeSessionModel", lazy="dynamic",  cascade="delete, delete-orphan")
    
    patient_cs_logs = db.relationship(
        "PatientCsLogModel",
        lazy="dynamic",
    )

    def __init__(self, title, table_format, creation_date, last_modify_date, is_active, description,image_string_coding, user_id, autism_centre_id,is_private):
        self.title = title
        self.table_format = table_format
        self.creation_date = creation_date
        self.last_modify_date = last_modify_date
        self.is_active = is_active
        self.description = description
        self.user_id = user_id
        self.autism_centre_id = autism_centre_id
        self.is_private = is_private
        self.image_string_coding = image_string_coding
        self.is_deleted = False

    def json(self):
        return {
            'id': self.id,
            'name': self.title,
            'table_format': self.table_format,
            'creation_date': self.creation_date.strftime("%Y-%m-%d"),
            'last_modify_date': self.last_modify_date.strftime("%Y-%m-%d") if self.last_modify_date else None,
            'is_active': self.is_active,
            'sector_list': self.get_table_sectors(),
            'context': self.get_context_list(),
            'description': self.description,
            'image_string_coding': self.image_string_coding,
            'user_id': self.user_id,
            'is_private': self.is_private,
            'autism_centre_id': self.autism_centre_id,
            'is_deleted' : self.is_deleted,
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def update_to_db(self):
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def add_context(self, _context):
        self.context.append(_context)
        db.session.commit()

    def get_context_list(self):
        return [context.json() for sector in self.table_sectors for image in sector.images for context in image.image_context]

    def get_table_sectors(self):
        table_sector_list = []
        for sector in self.table_sectors:
            table_sector_list.append(sector.json())
        return sorted(table_sector_list, key=lambda d: d['id'])


    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id, is_deleted = False).first()

    @classmethod
    def find_general_tables(cls, pattern):
        if pattern != 'null':
            search = "%{}%".format(pattern)
            caa_table_list = cls.query.filter(cls.title.ilike(search), cls.is_deleted == False).all()
        else:
            caa_table_list = cls.query.filter(cls.is_deleted == False).all()
        
        return list(filter(lambda x: len(x.table_patient_association) == 0, caa_table_list))

    
    @classmethod
    def find_owner_tables(cls,user_id):
        caa_table_list = cls.query.filter(cls.user_id == user_id, cls.is_deleted == False).all()
        caa_table_list=list(filter(lambda x: len(x.table_patient_association) == 0, caa_table_list))
        return caa_table_list


    @classmethod
    def find_private_tables(cls,user_id):
        caa_table_list = cls.query.filter(cls.user_id == user_id,cls.is_private==True, cls.is_deleted == False).all()
        caa_table_list=list(filter(lambda x: len(x.table_patient_association) == 0, caa_table_list))
        return caa_table_list

    @classmethod
    def find_default_tables(cls):
        caa_table_list = cls.query.filter(cls.user_id == 27, cls.is_deleted == False).all()
        caa_table_list=list(filter(lambda x: len(x.table_patient_association) == 0, caa_table_list))
        return caa_table_list

    @classmethod
    def find_centre_tables(cls,autism_centre_id):
        caa_table_list = cls.query.filter(cls.autism_centre_id == autism_centre_id, cls.is_deleted == False).all()
        caa_table_list=list(filter(lambda x: len(x.table_patient_association) == 0, caa_table_list))
        return caa_table_list

    @classmethod
    def find_public_tables(cls,pattern):
        search = "%{}%".format(pattern)
        caa_table_list = cls.query.filter(cls.title.like(search), cls.is_deleted == False).all()
        caa_table_list=list(filter(lambda x: len(x.table_patient_association) == 0 and x.is_private == False, caa_table_list))
        return caa_table_list
    
    @classmethod
    def find_most_used_tables(cls, user_id):
        caa_table_list = cls.query.filter(cls.is_deleted == False, cls.user_id != user_id).all()
        caa_table_list=list(filter(lambda x: len(x.table_patient_association) == 0 and x.is_private == False, caa_table_list))
        if(len(caa_table_list)>5):
            caa_table_list=caa_table_list[:5]
        return caa_table_list
