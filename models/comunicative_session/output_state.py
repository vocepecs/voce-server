from db import db


class OutputStateModel(db.Model):
    __tablename__ = "output_state"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    description = db.Column(db.Text())

    # 1 to N Relationships
    cs_output_images = db.relationship('CsOutputImageModel', lazy="dynamic")

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