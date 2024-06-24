from db import db


class PatientCsLogModel(db.Model):
    __tablename__ = 'patient_cs_logs'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    log_type = db.Column(db.Text())
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"))
    caa_table_id = db.Column(db.Integer, db.ForeignKey("caa_tables.id"))
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"))
    image_position = db.Column(db.Integer)

    # N to 1 Relationships
    user = db.relationship(
        "UserModel",
        back_populates="patient_cs_logs",
        cascade="delete",
    )
    patient = db.relationship(
        "PatientModel",
        back_populates="patient_cs_logs",
        cascade="delete"
    )
    caa_table = db.relationship(
        "CaaTableModel",
        back_populates="patient_cs_logs",
        cascade="delete"
    )
    image = db.relationship(
        "ImageModel",
        back_populates="patient_cs_logs",
        cascade="delete"
    )

    def __init__(self,date,log_type,user_id,patient_id,caa_table_id,image_id,image_position):
        self.date = date
        self.log_type = log_type
        self.user_id = user_id
        self.patient_id = patient_id
        self.caa_table_id = caa_table_id
        self.image_id = image_id
        self.image_position = image_position

    # def json(self):
    #     return {
    #         "id" : self.id,
    #         "date" : self.date, #TODO format
    #         "log_type" : self.log_type,
    #         "user_id"
    #     }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def update_to_db(self):
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()   

