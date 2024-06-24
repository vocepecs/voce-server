from tokenize import Name
from db import db
from sqlalchemy import update


class EnrollmentModel(db.Model):
    __tablename__ = "enrollments"

    user_id = db.Column(db.ForeignKey('users.id'), primary_key=True)
    patient_id = db.Column(db.ForeignKey('patients.id'), primary_key=True)
    is_active = db.Column(db.Boolean)

    user = db.relationship("UserModel", back_populates="enrollments")
    patient = db.relationship("PatientModel", back_populates="enrollments")

    def __init__(self, user_id, patient_id, is_active):
        self.user_id = user_id
        self.patient_id = patient_id
        self.is_active = is_active

    def get_json_patient(self):
        json_patient = self.patient.json()
        json_patient['is_active'] = self.is_active
        return json_patient

    def get_json_user(self):
        return self.user.json()
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def find_by_id(cls, _user_id, _patient_id):
        return cls.query.filter_by(user_id = _user_id, patient_id = _patient_id).first()


class UserModel(db.Model):
    __tablename__ = 'users'

    # columns
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(80))
    password_hash = db.Column(db.LargeBinary(128))
    name = db.Column(db.String(30))
    role_id = db.Column(db.Integer, db.ForeignKey("user_roles.id"))
    email_verified = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=True)
    email_subscription = db.Column(db.Boolean, default=False)
    first_access = db.Column(db.Boolean, default=True)
    subscription_date = db.Column(db.DateTime)
    
    autism_centre_id = db.Column(
        db.Integer, db.ForeignKey("autism_centres.id"))

    # N to 1 Relationships
    user_role = db.relationship("UserRolesModel", back_populates="users")
    autism_centre = db.relationship(
        "AutismCentreModel",
        back_populates="users",
    )

    
    enrollments = db.relationship("EnrollmentModel", back_populates="user")

    # 1 to N Relationships
    caa_tables = db.relationship('CaaTableModel', lazy="dynamic")
    social_stories = db.relationship('SocialStoryModel', lazy="dynamic")
    images = db.relationship('ImageModel', lazy="dynamic")
    comunicative_evaluations = db.relationship(
        "ComunicativeEvaluationModel",
        lazy="dynamic",
    )
    comunicative_sessions = db.relationship(
        "ComunicativeSessionModel",
        lazy="dynamic",
    )

    patient_cs_logs = db.relationship(
        "PatientCsLogModel",
        lazy="dynamic",
    )

    def __init__(self, email, name, role_id, autism_centre_id, first_access=True, subscription_date=None):
        self.email = email
        self.role_id = role_id
        self.name = name
        self.autism_centre_id = autism_centre_id
        self.first_access = first_access
        self.subscription_date = subscription_date

    def json(self):
        
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.user_role.json(),
            'email_verified': self.email_verified,
            'autism_centre': self.autism_centre.json() if self.autism_centre != None else None,
            'patient_list': self.get_patients(),
            'first_access': self.first_access,
        }

    def get_patients(self):
        patient_list = []
        for enr in self.enrollments:
            patient_list.append(enr.get_json_patient())
        return patient_list

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    def set_active_patient(self, patient_id):
        for enrollment in self.enrollments:
            enrollment.is_active = False
            if enrollment.patient.id == patient_id:
                enrollment.is_active = True
        db.session.commit()

    @classmethod
    def find_by_username(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_autism_centre(cls, _autism_centre_id):
        return cls.query.filter_by(autism_centre_id=_autism_centre_id).all()

    @classmethod
    def find_active_patient(cls, _id):
        user = cls.query.filter_by(id=_id).first()
        for enrollment in user.enrollments:
            if enrollment.is_active:
                return enrollment.patient
