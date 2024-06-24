from email.mime import image
from tokenize import Token, tokenize
from flask_restful import Resource, reqparse, request
import sqlalchemy
from models.caa_table import CaaTableModel
from models.context import ContextModel
from models.tag import ImageTagModel, TagModel
from utils.pos_tagging import PosTagger
from models.grammatical_type import GrammaticalTypeModel
#from models.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.tense import TenseModel
from models.comunicative_session.verbal_form import VerbalFormModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
from models.comunicative_session.pos_tagging import PosTaggingModel
from models.comunicative_session.session_log import SessionLogModel
from models.image import ImageModel
from utils.nlp_preprocess import NlpPreprocess
from nltk.stem import SnowballStemmer
from utils.association_tables import ass_image_context, ass_image_grammatical_type
import nltk
from datetime import datetime
from sqlalchemy.orm import defer
from db import db

from flask_jwt_extended import jwt_required

class Suggested(Resource):
    def filter_key_word_list(self, image, token_lemma):
        return list(filter(lambda x: (x.tag_type == 'KEYWORD'
                                      and (any(PosTagger.tag_text(z)[0] == token_lemma for z in x.tag.tag_value.split()))),
                           image.image_tag))

    def get_out_of_context_image_list(self, label):
        search = "%{}%".format(label)

        return ImageModel.query.join(ImageTagModel).join(TagModel).filter(
            ImageTagModel.tag_type == 'KEYWORD',
            TagModel.tag_value == label
            # TagModel.tag_value_stem.ilike(search)
        ).all()


    def populate_dict(self, tag_list):
        tag_dict = {}
        for r in tag_list:
            if r[0].id not in tag_dict:
                tag_dict[r[0].id]=[r[1].tag_value]
                #print(f'ID IMMAGINE: {r[0].id} - TAG VALUE: {r[1].tag_value}')
            else:
                 tag_dict[r[0].id].append(r[1].tag_value)
                 #print(f'ID IMMAGINE: {r[0].id} - TAG VALUE: {r[1].tag_value}') 
        return tag_dict

    @jwt_required()
    def get(self):
        image_list_sug = []
        image_id = request.args.get("image_id", None)
        id_table = request.args.get("table_id", type=int, default=None)  # ID TABELLA

        if id_table != None:
            caa_table = CaaTableModel.find_by_id(id_table)
            # CONTESTI TABELLA
            context_list_caa = [ctx.context_type for ctx in caa_table.context]
            print(len(context_list_caa))
            print(f'context list: {context_list_caa}')
        
        print(f'start query: {datetime.now()}')
        
        # Immagine da sostituire
        image = ImageModel.find_by_id(image_id)
        image_tag_model_list = list(filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
        image_general_tag_list = [image_tag.tag.tag_value for image_tag in image_tag_model_list]
        print(f'image_general_tag_list : {image_general_tag_list}')


        image_list_sug.extend(ImageModel.query
                              .join(ImageTagModel)
                              .join(TagModel)
                              .filter(ImageTagModel.tag_type == 'GENERAL', TagModel.tag_value.in_(image_general_tag_list)).all())
        
        print(f'image_list_sug considerando i contesti : {len(image_list_sug)}')
        
        

        
        
        if len(image_list_sug) == 0:
            image = ImageModel.find_by_id(image_id)
            print(f'label search: {image.label}')
            image_list_sug = self.get_out_of_context_image_list(image.label)
        
        print(f'end query: {datetime.now()}')
        
        for x in image_list_sug:
            print(x.label)

        image_id_list = [x.id for x in image_list_sug]
        result_hyp = ImageModel.find_tag_value_for_image('HYPERONYM',image_id_list)
        result_key = ImageModel.find_tag_value_for_image('KEYWORD',image_id_list)

        # print(f'suggested query: {image_list_sug}')
        # print(f'result_hyp query: {result_hyp}')
        # print(f'result_key query: {result_key}')

        print('RISULTATO QUERY JOIN') 
        hyp_tag_dict = self.populate_dict(tag_list=result_hyp)
        key_tag_dict =  self.populate_dict(tag_list=result_key)

        print(f'hyp_tag_dict: {hyp_tag_dict}')
        print(f'key_tag_dict: {key_tag_dict}')
        
        # for r in result_hyp:
        #     if r[0].id not in hyp_tag_dict:
        #         hyp_tag_dict[r[0].id]=[r[1].tag_value]
        #         #print(f'ID IMMAGINE: {r[0].id} - TAG VALUE: {r[1].tag_value}')
        #     else:
        #          hyp_tag_dict[r[0].id].append(r[1].tag_value)
        #          #print(f'ID IMMAGINE: {r[0].id} - TAG VALUE: {r[1].tag_value}')   
        # #print('contesti')
        

        # for r in result_key:
        #     if r[0].id not in key_tag_dict:
        #         key_tag_dict[r[0].id]=[r[1].tag_value]
        #         #print(f'ID IMMAGINE: {r[0].id} - TAG VALUE: {r[1].tag_value}')
        #     else:
        #          key_tag_dict[r[0].id].append(r[1].tag_value)
        #         # print(f'ID IMMAGINE: {r[0].id} - TAG VALUE: {r[1].tag_value}')   
        # #print('contesti')
        
       
       
       
        
        # print(len(image_list_sug))
        # for image in image_list_sug:
           
        #     hyp_tag_dict[image.id] = list(
        #         filter(lambda x: x.tag_type == 'HYPERONYM', image.image_tag))
        #     key_tag_dict[image.id]=list(
        #         filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))

        suggested_list = []

        match_list = []
        #print('LABEL')
        image = ImageModel.find_by_id(image_id)
        #print(image.label)
        #print("Sinonimi")

        key_word_list=list(
            filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
        syn_tag_list = list(
            filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
        #print(syn_tag_list)

        hyp_list = list(filter(lambda x: x.tag_type ==
                        'HYPERONYM', image.image_tag))

        print(f'start KEYWORD: {datetime.now()}')

        
        for j in key_word_list:
            for h,value in key_tag_dict.items():
                if list(filter(lambda x: x == j.tag.tag_value, value)):
                     match_list.append(h)

                
                       
        print(f'start SINONIMI: {datetime.now()}')
        for j in syn_tag_list:
            try:
             match_list.append(list(filter(lambda x: x.label == j.tag.tag_value, image_list_sug))[0].id)
            except:
                print('No match')
        
        print(f'start iperonimi: {datetime.now()}')
        for k,value in hyp_tag_dict.items():
            
            hyp_tag_list = [x  for x in value] 
           # prendo le immagini in cui l'etichetta dell'immagine è iperonimo di altre immagini

            for x in hyp_tag_list:
                if (image.label in x):
                    match_list.append(k)
                    for j in hyp_list:
                        if (j.tag.tag_value in x):
                            
                            match_list.append(k)
                           
                            
        print(f'end iperonimi: {datetime.now()}')

       

        suggested_list = list(set(match_list))
       
        print(suggested_list)

        suggested_image_list = [ImageModel.find_by_id(
            suggested_id).json() for suggested_id in suggested_list]

        return {
            "id": image_id,
            "suggested": suggested_image_list
        }, 200
