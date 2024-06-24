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
from models.patient import PatientModel
from utils.nlp_preprocess import NlpPreprocess
from nltk.stem import SnowballStemmer
import nltk
from datetime import datetime
from sqlalchemy.orm import defer
from db import db
from models.synset import SynsetModel
from utils.association_tables import ass_image_synset
from nltk.corpus import wordnet as wn
from collections import OrderedDict
from utils.association_tables import image_patient
from models.image_synonym import ImageSynonymModel
from sqlalchemy import or_
from sqlalchemy import func

from flask_jwt_extended import jwt_required

class Suggested2(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('image_id', type=int, required=True, location='json')
        self.parser.add_argument('patient_id', type=int, location='json')

    @jwt_required()
    def post(self):
        image_list_sug = []
        args = self.parser.parse_args()
        image_id = args['image_id']
        patient_id= args['patient_id']

        print(f"args: {args}")

        image = ImageModel.find_by_id(image_id)

        #estraggo le immagini che hanno questo synset(prendo synset ridotto così sono più larga)
        syn=[s['synset_name_short'] for s in image.get_synsets()]
        #synset_short=".".join(synset.split('.')[0:2])
        """for synset_short in syn:
            image_list_syn=ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(SynsetModel.synset_name_short==synset_short).all()
            image_list_syn= list(set(image_list_syn))
            image_list_sug.extend(image_list_syn)            
        print(len(image_list_sug))
        print(image_list_sug)"""

        #Lista delle suggerite create prendendo tutte le immagini con tag KEYWORD uguale alla label 
        image_list_tag=ImageModel.query.join(ImageTagModel).join(TagModel).filter( ImageTagModel.tag_type=='KEYWORD',TagModel.tag_value.ilike(image.label)).all()
        image_list_sug.extend(image_list_tag)
        print('tag')
        print(image_list_tag)

        #Lista delle suggerite create prendendo tutte le immagini sinonime 
        id_list_sin=ImageSynonymModel.query.filter( or_(ImageSynonymModel.image_id==image_id,ImageSynonymModel.image_syn_id==image_id)).all()
        image_list_sin=[]
        for i in id_list_sin:
            if str(i.image_id) == image_id:
                image_list_sin.append(ImageModel.find_by_id(i.image_syn_id))
            if str(i.image_syn_id)== image_id:
                image_list_sin.append(ImageModel.find_by_id(i.image_id))
        
        image_list_sug.extend(image_list_sin)
        print('syn')
        print(image_list_sin)
        #ricavo le keyword dell'immagine per estrarre tutte quelle immagini il cui tag value di tipo KEYWORD è contenuto nel tag splittato o lo contengono interamente
        
        image_tag_model_list = list(filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
        image_key_tag_list = [image_tag.tag.tag_value for image_tag in image_tag_model_list]

        for tag in image_key_tag_list:
            image_list_tag2=[]
            image_list_tag2=ImageModel.query.join(ImageTagModel).join(TagModel).filter(ImageTagModel.tag_type=='KEYWORD',func.lower(TagModel.tag_value).contains(tag.lower())).all()
            it_stop_words = nltk.corpus.stopwords.words('italian')
            for tag_split in tag.split():
                if tag_split not in (it_stop_words):
                    print(tag_split)
                    image_list_tag2.extend(ImageModel.query.join(ImageTagModel).join(TagModel).filter( ImageTagModel.tag_type=='KEYWORD',func.lower(TagModel.tag_value).contains(tag_split.lower())).all())
                    image_list_tag2.extend(ImageModel.query.join(ImageTagModel).join(TagModel).filter( ImageTagModel.tag_type=='KEYWORD',func.lower(TagModel.tag_value)==tag_split.lower()).all())
            image_list_sug.extend(image_list_tag2)
            print('tag2')
            print(image_list_tag2)

        """#estraggo le immagini relative al synset iperonimo se non è un verbo
        syns=[s['synset_name'] for s in image.get_synsets()]
        for s in syns:
            syn= wn.synset(s)
            check_V=(False if s.split('.')[1]=='v' else True)
            hypernyms = syn.hypernyms()
            print(len(hypernyms))
            if check_V:
                print('sono qui')
                for h in hypernyms:
                    hyper_name=".".join(str(h)[8:].split('.')[0:2])
                    print('hyper'+hyper_name)
                    image_list_hyp=ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(SynsetModel.synset_name_short==hyper_name).all()
                    image_list_hyp = list(set(image_list_hyp))
                    print(len(image_list_hyp))
                    image_list_sug.extend(image_list_hyp)"""

        image_list_sug=list(OrderedDict.fromkeys(image_list_sug))
        image_custom = []
        image_custom2 = []
        if patient_id:
            image_custom=ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id==patient_id).all() 
            image_custom2=ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id!=patient_id).all() 
            lista=[im.id for im in image_custom]
        image_list_custom=[im for im in image_custom if im in image_list_sug]
        image_list=[]
        image_list.extend(image_list_custom)
        image_list.extend(image_list_sug)
        
        image_id_sugg=[im.id_arasaac for im in image_list if im.id_arasaac!=None]
        final_imageIdAra_list = list(OrderedDict.fromkeys(image_id_sugg))

        id_image_list=[im.id for im in image_list if (str(im.id)!=str(image_id) and im not in image_custom2)] 
        list_final = list(OrderedDict.fromkeys(id_image_list))
        final_list=[ImageModel.find_by_id(id).json() for id in list_final]
        

        final_imageId_list = list(OrderedDict.fromkeys(id_image_list))

        return {
            "id": image_id,
            "tot": len(final_list),
            "suggested": final_list
        }, 200

    @jwt_required()
    def get(self):
        image_list_sug = []
        image_id = request.args.get("image_id", None)
        patient_id=request.args.get("patient_id",None)

        image = ImageModel.find_by_id(image_id)

        #estraggo le immagini che hanno questo synset(prendo synset ridotto così sono più larga)
        syn=[s['synset_name_short'] for s in image.get_synsets()]
        #synset_short=".".join(synset.split('.')[0:2])
        """for synset_short in syn:
            image_list_syn=ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(SynsetModel.synset_name_short==synset_short).all()
            image_list_syn= list(set(image_list_syn))
            image_list_sug.extend(image_list_syn)            
        print(len(image_list_sug))
        print(image_list_sug)"""

        #Lista delle suggerite create prendendo tutte le immagini con tag KEYWORD uguale alla label 
        image_list_tag=ImageModel.query.join(ImageTagModel).join(TagModel).filter( ImageTagModel.tag_type=='KEYWORD',TagModel.tag_value.ilike(image.label)).all()
        image_list_sug.extend(image_list_tag)
        print('tag')
        print(image_list_tag)

        #Lista delle suggerite create prendendo tutte le immagini sinonime 
        id_list_sin=ImageSynonymModel.query.filter( or_(ImageSynonymModel.image_id==image_id,ImageSynonymModel.image_syn_id==image_id)).all()
        image_list_sin=[]
        for i in id_list_sin:
            if str(i.image_id) == image_id:
                image_list_sin.append(ImageModel.find_by_id(i.image_syn_id))
            if str(i.image_syn_id)== image_id:
                image_list_sin.append(ImageModel.find_by_id(i.image_id))
        
        image_list_sug.extend(image_list_sin)
        print('syn')
        print(image_list_sin)
        #ricavo le keyword dell'immagine per estrarre tutte quelle immagini il cui tag value di tipo KEYWORD è contenuto nel tag splittato o lo contengono interamente
        
        image_tag_model_list = list(filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
        image_key_tag_list = [image_tag.tag.tag_value for image_tag in image_tag_model_list]

        for tag in image_key_tag_list:
            image_list_tag2=[]
            image_list_tag2=ImageModel.query.join(ImageTagModel).join(TagModel).filter(ImageTagModel.tag_type=='KEYWORD',func.lower(TagModel.tag_value).contains(tag.lower())).all()
            it_stop_words = nltk.corpus.stopwords.words('italian')
            for tag_split in tag.split():
                if tag_split not in (it_stop_words):
                    print(tag_split)
                    image_list_tag2.extend(ImageModel.query.join(ImageTagModel).join(TagModel).filter( ImageTagModel.tag_type=='KEYWORD',func.lower(TagModel.tag_value).contains(tag_split.lower())).all())
                    image_list_tag2.extend(ImageModel.query.join(ImageTagModel).join(TagModel).filter( ImageTagModel.tag_type=='KEYWORD',func.lower(TagModel.tag_value)==tag_split.lower()).all())
            image_list_sug.extend(image_list_tag2)
            print('tag2')
            print(image_list_tag2)

        """#estraggo le immagini relative al synset iperonimo se non è un verbo
        syns=[s['synset_name'] for s in image.get_synsets()]
        for s in syns:
            syn= wn.synset(s)
            check_V=(False if s.split('.')[1]=='v' else True)
            hypernyms = syn.hypernyms()
            print(len(hypernyms))
            if check_V:
                print('sono qui')
                for h in hypernyms:
                    hyper_name=".".join(str(h)[8:].split('.')[0:2])
                    print('hyper'+hyper_name)
                    image_list_hyp=ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(SynsetModel.synset_name_short==hyper_name).all()
                    image_list_hyp = list(set(image_list_hyp))
                    print(len(image_list_hyp))
                    image_list_sug.extend(image_list_hyp)"""

        image_list_sug=list(OrderedDict.fromkeys(image_list_sug))
        image_custom2 = []
        if patient_id:
            image_custom=ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id==patient_id).all() 
            image_custom2=ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id!=patient_id).all() 
            lista=[im.id for im in image_custom]
        image_list_custom=[im for im in image_custom if im in image_list_sug]
        image_list=[]
        image_list.extend(image_list_custom)
        image_list.extend(image_list_sug)
        
        image_id_sugg=[im.id_arasaac for im in image_list if im.id_arasaac!=None]
        final_imageIdAra_list = list(OrderedDict.fromkeys(image_id_sugg))

        id_image_list=[im.id for im in image_list if (str(im.id)!=str(image_id) and im not in image_custom2)] 
        list_final = list(OrderedDict.fromkeys(id_image_list))
        final_list=[ImageModel.find_by_id(id).json() for id in list_final]
        

        final_imageId_list = list(OrderedDict.fromkeys(id_image_list))

        return {
            "id": image_id,
            "tot": len(final_list),
            "suggested": final_list
        }, 200