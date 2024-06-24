from db import db


class ImageTagModel(db.Model):
    __tablename__ = "image_tag"

    image_id = db.Column(db.ForeignKey('images.id'), primary_key=True)
    tag_id = db.Column(db.ForeignKey('tags.id'), primary_key=True)
    tag_type = db.Column(db.String(10))
    weight = db.Column(db.Float)

    image = db.relationship("ImageModel", back_populates="image_tag")
    tag = db.relationship("TagModel", back_populates="image_tag")

    def __init__(self, image_id, tag_id, tag_type, weight):
        self.image_id = image_id,
        self.tag_id = tag_id,
        self.tag_type = tag_type,
        self.weight = weight

    def json(self):
        return {
            'id' : self.tag_id,
            'tag_value' : self.tag.tag_value,
            'tag_type' : self.tag_type,
            'weight' : self.weight,
        }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, _image_id, _tag_id):
        return cls.query.filter_by(image_id=_image_id, tag_id=_tag_id).first()

class TagModel(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    tag_value = db.Column(db.String(20), index=True)
    tag_value_stem = db.Column(db.Text())

    image_tag = db.relationship("ImageTagModel", back_populates="tag")

    def __init__(self, tag_value):
        self.tag_value = tag_value

    def json(self):
        return {
            'id': self.id,
            'tag_value': self.tag_value,
            'tag_value_stem' : self.tag_value_stem,
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

    @classmethod
    def find_by_tag_value(cls, tag):
        return cls.query.filter(db.func.lower(cls.tag_value) == db.func.lower(tag)).first()
    
    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()