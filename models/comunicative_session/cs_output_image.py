from db import db


class CsOutputImageModel(db.Model):
    __tablename__ = "cs_output_images"

    id = db.Column(db.Integer, primary_key=True)
    pos_tagging_token_ref = db.Column(db.Integer)
    pos_tagging_grammatical_type_ref = db.Column(db.Integer)
    comunicative_session_id = db.Column(
        db.Integer,
        db.ForeignKey("comunicative_sessions.id"),
    )
    image_id = db.Column(
        db.Integer,
        db.ForeignKey("images.id")
    )
    correct_image_id = db.Column(
        db.Integer,
        db.ForeignKey("images.id")
    )
    output_state_id = db.Column(
        db.Integer,
        db.ForeignKey("output_state.id")
    )
    initial_position = db.Column(db.Integer)
    final_position = db.Column(db.Integer)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['pos_tagging_token_ref', 'pos_tagging_grammatical_type_ref'],
            ['pos_tagging.token', 'pos_tagging.grammatical_type_id'],
        ),
    )

    # N to 1 Relationships
    comunicative_session = db.relationship(
        "ComunicativeSessionModel",
        back_populates="cs_output_images",
        cascade="delete"
    )
    image = db.relationship(
        "ImageModel",
        back_populates="cs_output_images",
        foreign_keys=[image_id],
    )
    correct_image = db.relationship(
        "ImageModel",
        back_populates="cs_output_correct_images",
        foreign_keys=[correct_image_id],
    )
    output_state = db.relationship(
        "OutputStateModel",
        back_populates="cs_output_images",
    )

    def __init__(self,
                 pos_tagging_token_ref,
                 pos_tagging_grammatical_type_ref,
                 comunicative_session_id,
                 image_id,
                 correct_image_id,
                 output_state_id,
                 initial_position,
                 final_position,
                 ):
        self.pos_tagging_token_ref = pos_tagging_token_ref
        self.pos_tagging_grammatical_type_ref = pos_tagging_grammatical_type_ref
        self.comunicative_session_id = comunicative_session_id
        self.image_id = image_id
        self.correct_image_id = correct_image_id
        self.output_state_id = output_state_id
        self.initial_position = initial_position
        self.final_position = final_position

    def json(self):
        return {
            'id': self.id,
            'pos_tagging_token_ref': self.pos_tagging_token_ref,
            'pos_tagging_grammatical_type_ref': self.pos_tagging_grammatical_type_ref,
            'comunicative_session_id': self.comunicative_session_id,
            'image_id': self.image_id,
            'correct_image_id': self.correct_image_id,
            'output_state_id': self.output_state_id,
            'initial_position': self.initial_position,
            'final_position': self.final_position
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self.id

    def update_to_db(self):
        db.session.commit()

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_cs_image_id(cls, _cs_id, _image_id):
        return cls.query.filter_by(comunicative_session_id=_cs_id, image_id=_image_id).first()

    @classmethod
    def find_by_cs_id(cls, cs_id):
        return cls.query.filter_by(comunicative_session_id=cs_id).all()
