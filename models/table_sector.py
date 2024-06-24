from db import db
# from utils.association_tables import table_sector_image


class TableSectorImage(db.Model):

    __tablename__ = "table_sector_image"

    image_id =  db.Column(db.Integer, db.ForeignKey('images.id'), primary_key=True)
    table_sector_id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['table_sector_id', 'table_id'],
            ['table_sectors.id', 'table_sectors.table_id'],
        ),
    )


class TableSectorModel(db.Model):
    __tablename__ = "table_sectors"

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.ForeignKey('caa_tables.id'), primary_key=True)
    color = db.Column(db.String(10))
    sector_number = db.Column(db.String(10))

    caa_table = db.relationship(
        "CaaTableModel", back_populates="table_sectors")
    
    images = db.relationship(
        "ImageModel",
        secondary="table_sector_image",
        back_populates="table_sectors"
    )

    def __init__(self, id, table_id, color, sector_number):
        self.id = id
        self.table_id = table_id
        self.color = color
        self.sector_number = sector_number

    def update(self, id, table_id, color, sector_number):
        self.id = id
        self.table_id = table_id
        self.color = color
        self.sector_number = sector_number

    def json(self):
        return {
            'id': self.id,
            'sector_color': self.color,
            'table_sector_number': self.sector_number,
            'image_list':self.get_images()
        }

    def get_images(self): 
        images = []
        for sector in self.images:
            images.append(sector.json())
        return images

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()
    
    def update_to_db(self):
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, _id, _table_id):
        return cls.query.filter_by(id=_id, table_id = _table_id).first()
    
    @classmethod
    def find_all_table_sectors(cls, _table_id):
        return cls.query.filter_by(table_id = _table_id).all()
