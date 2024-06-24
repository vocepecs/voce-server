from db import db
from utils.association_tables import ass_cs_logs


class SessionLogModel(db.Model):
    __tablename__ = 'session_logs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    description = db.Column(db.Text())


    # N to N Relationships
    comunicative_sessions = db.relationship(
        "ComunicativeSessionModel",
        secondary=ass_cs_logs,
    )


    def __init__(self, title, description):
        self.title = title
        self.description = description

    def json(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def find_by_title(cls, value):
        return cls.query.filter(db.func.lower(cls.title) == db.func.lower(value)).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()