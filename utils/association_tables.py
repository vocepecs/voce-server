from sqlalchemy import ForeignKey
from db import db

# enrollments = db.Table('enrollments',
#                        db.Column('user_id',
#                                  db.Integer,
#                                  db.ForeignKey('users.id'),
#                                  primary_key=True),
#                        db.Column('patient_id',
#                                  db.Integer,
#                                  db.ForeignKey('patients.id'),
#                                  primary_key=True),
#                        )

ass_image_grammatical_type = db.Table('image_grammatical_type',
                                      db.Column('image_id',
                                                db.Integer,
                                                db.ForeignKey('images.id'),
                                                primary_key=True,
                                                ),
                                      db.Column('grammatical_type_id',
                                                db.Integer,
                                                db.ForeignKey(
                                                    'grammatical_types.id'),
                                                primary_key=True,

                                                )
                                      )

ass_image_context = db.Table('image_context',
                             db.Column('image_id',
                                       db.Integer,
                                       db.ForeignKey('images.id'),
                                       primary_key=True,
                                       ),
                             db.Column('context_id',
                                       db.Integer,
                                       db.ForeignKey('contexts.id'),
                                       primary_key=True,
                                       )
                             )

# patient_caa_table = db.Table('patient_caa_table',
#                              db.Column('patient_id',
#                                        db.Integer,
#                                        db.ForeignKey('patients.id'),
#                                        primary_key=True,
#                                        ),
#                              db.Column('caa_table_id',
#                                        db.Integer,
#                                        db.ForeignKey('caa_tables.id'),
#                                        primary_key=True),
#                              )

image_caa_table = db.Table('image_caa_table',
                           db.Column('image_id',
                                     db.Integer,
                                     db.ForeignKey('images.id'),
                                     primary_key=True,
                                     ),
                           db.Column('caa_table_id',
                                     db.Integer,
                                     db.ForeignKey('caa_tables.id'),
                                     primary_key=True),
                           )

image_patient = db.Table('image_patient',
                         db.Column('image_id',
                                   db.Integer,
                                   db.ForeignKey('images.id'),
                                   primary_key=True,
                                   ),
                         db.Column('patient_id',
                                   db.Integer,
                                   db.ForeignKey('patients.id'),
                                   primary_key=True),

                         )
image_comunicative_session = db.Table('image_comunicative_session',
                                      db.Column('image_id',
                                                db.Integer,
                                                db.ForeignKey('images.id'),
                                                primary_key=True,
                                                ),
                                      db.Column('comunicative_session_id',
                                                db.Integer,
                                                db.ForeignKey(
                                                    'comunicative_sessions.id'),
                                                primary_key=True),

                                      )

# context_caa_table = db.Table('context_caa_table',
#                              db.Column('context_id',
#                                        db.Integer,
#                                        db.ForeignKey('contexts.id'),
#                                        primary_key=True,
#                                        ),
#                              db.Column('caa_table_id',
#                                        db.Integer,
#                                        db.ForeignKey('caa_tables.id'),
#                                        primary_key=True),
#                              )

ass_cs_logs = db.Table('cs_logs',
                       db.Column('cs_id',
                                 db.Integer,
                                 db.ForeignKey('comunicative_sessions.id'),
                                 primary_key=True,
                                 ),
                       db.Column('cs_log_id',
                                 db.Integer,
                                 db.ForeignKey('session_logs.id'),
                                 primary_key=True,
                                 ),
                       )

ass_image_synset = db.Table('image_synset',
                            db.Column('image_id',
                                      db.Integer,
                                      db.ForeignKey('images.id'),
                                      primary_key=True
                                      ),
                            db.Column('synset_id',
                                      db.Integer,
                                      db.ForeignKey('synsets.id'),
                                      primary_key=True
                                      ),
                            )

ass_image_audio = db.Table("image_audio",
                           db.Column("image_id",
                                     db.Integer,
                                     db.ForeignKey("images.id"),
                                     primary_key=True,
                                     ),
                           db.Column("audio_id",
                                     db.Integer,
                                     db.ForeignKey("audio_tts.id"),
                                     primary_key=True,
                                     ),
                           )
# table_sector_image = db.Table('table_sector_image',
#                          db.Column('image_id',
#                                    db.Integer,
#                                    db.ForeignKey('images.id'),
#                                    primary_key=True,
#                                    ),
#                          db.Column('table_sector_id',
#                                    db.Integer,
#                                    db.ForeignKey('table_sectors.id'),
#                                    primary_key=True),
#                          db.Column('table_id',
#                                    db.Integer,
#                                    db.ForeignKey('table_sectors.table_id'),
#                                    primary_key=True),
#                          )
