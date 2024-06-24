from db import db


class ImageSynonymModel(db.Model):
    __tablename__ = "image_synonyms"

    # columns
    image_id = db.Column(db.Integer,
                         db.ForeignKey("images.id"),
                         primary_key=True
                         )
    image_syn_id = db.Column(db.Integer,
                             db.ForeignKey("images.id"),
                             primary_key=True,
                             )

    image = db.relationship(
        "ImageModel",
        back_populates="images",
        foreign_keys=[image_id]
    )

    image_synonym = db.relationship(
        "ImageModel",
        back_populates="synonym_images",
        foreign_keys=[image_syn_id]
    )

    def __init__(self, image_id, image_syn_id):
        self.image_id = image_id
        self.image_syn_id = image_syn_id

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
