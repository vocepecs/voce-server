from db import db


class ComunicativeEvaluationModel(db.Model):
    __tablename__ = "comunicative_evaluations"

    # columns
    id = db.Column(db.Integer, primary_key=True)
    evaluation_date = db.Column(db.DateTime)
    value = db.Column(db.Integer)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # object relations mapping
    patient = db.relationship("PatientModel", back_populates="comunicative_evaluations")
    user = db.relationship("UserModel", back_populates="comunicative_evaluations")

    def __init__(self, evaluation_date, value, patient_id, user_id):
        self.evaluation_date = evaluation_date
        self.value = value
        self.patient_id = patient_id
        self.user_id = user_id

    def json(self):
        return {
            'id': self.id,
            'evaluation_date': self.evaluation_date.strftime("%d/%m/%Y"),
            'value': self.value,
            'patient': self.patient.json(),
            'user': self.user.json(),
        }

        
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()
