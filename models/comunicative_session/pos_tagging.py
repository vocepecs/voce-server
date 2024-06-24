from operator import ge
from db import db


class PosTaggingModel(db.Model):
    __tablename__ = "pos_tagging"

    token = db.Column(db.Text(), primary_key=True)
    grammatical_type_id = db.Column(db.Integer,
                                    db.ForeignKey('grammatical_types.id'),
                                    primary_key=True,
                                    )
    lemma = db.Column(db.Text())
    tense_id = db.Column(db.Integer, db.ForeignKey('tense.id'))
    verbal_form_id = db.Column(db.Integer, db.ForeignKey('verbal_form.id'))
    gender = db.Column(db.Text())
    number = db.Column(db.Text())


    # 1 to N Relationships
    cs_output_images = db.relationship('CsOutputImageModel', lazy="dynamic")


    # N to 1 Relationships
    grammatical_type = db.relationship(
        "GrammaticalTypeModel",
        back_populates="pos_tagging_results",
    )
    tense = db.relationship(
        "TenseModel",
        back_populates="pos_tagging_results",
    )
    verbal_form = db.relationship(
        "VerbalFormModel",
        back_populates="pos_tagging_results",
    )

    def __init__(self, token, grammatical_type_id, lemma, tense_id, verbal_form_id, gender, number):
        self.token = token
        self.grammatical_type_id = grammatical_type_id
        self.lemma = lemma
        self.tense_id = tense_id
        self.verbal_form_id = verbal_form_id
        self.gender = gender
        self.number = number

    def json(self):
        # TODO Sistemare con tutti i campi
        return {
            "token": self.token,
            "grammatical_type": self.grammatical_type_id,
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return [self.token, self.grammatical_type_id]

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_composite_id(cls, token, grammatical_type_id):
        return cls.query.filter(db.func.lower(cls.token) == db.func.lower(token), cls.grammatical_type_id == grammatical_type_id).first()
