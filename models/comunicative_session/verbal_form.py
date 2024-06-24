from db import db


class VerbalFormModel(db.Model):
    __tablename__ = "verbal_form"

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Text())

    # 1 to N Relationships
    pos_tagging_results = db.relationship(
        "PosTaggingModel",
        lazy="dynamic",
    )

    def __init__(self, value):
        self.value = value

    def json(self):
        return {
            "id": self.id,
            "value": self.value
        }
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_value(cls, value):
        return cls.query.filter(cls.value == value).first()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()