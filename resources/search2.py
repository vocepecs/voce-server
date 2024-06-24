from flask_restful import Resource, reqparse, request
from utils.pos_tagging import PosTagger
from datetime import datetime
from nltk.stem import SnowballStemmer
from utils.nlp_preprocess import NlpPreprocess
from models.image import ImageModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.session_log import SessionLogModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
from models.comunicative_session.patient_cs_log import PatientCsLogModel

from nltk.corpus import wordnet as wn
from utils.association_tables import ass_image_synset
from models.synset import SynsetModel
from models.patient import PatientModel
from models.image_synonym import ImageSynonymModel
from sqlalchemy import or_
from utils.association_tables import image_patient
from collections import OrderedDict
import Levenshtein

from utils.wsd_model import WSDModel

from flask_jwt_extended import jwt_required

_search_parser = reqparse.RequestParser()
_search_parser.add_argument(
    'phrase',
    type=str,
    required=False,
    help='This field cannot be blank',
)


ps = SnowballStemmer('italian')

class Translate2(Resource):

    def findTokenInDict(self, image_dict, token):
        for image in image_dict.items():
            for tok in image[1]["occorrenza"]:
                if tok in token:
                    return image[0]

    def sortCaaImageList(self, image_list, image_dict, token_list):
        print(f"token_list: {token_list}")
        # for x in image_list:
        #     print(f"label: {x.label}")
        image_id_list = []
        image_list_sorted = []

        for token in token_list:
            image_id = self.findTokenInDict(image_dict=image_dict, token=token)
            if image_id:
                for image in image_list:
                    if image.id == image_id:
                        image_list_sorted.append(image)

        image_list_sorted_final = []
        for image in image_list_sorted:
            if(image.id not in [x.id for x in image_list_sorted_final]):
                image_list_sorted_final.append(image)

        return image_list_sorted_final

    def filter_key_word_list(self, image, token_lemma):
        return list(filter(lambda x: (x.tag_type == 'KEYWORD'
                                      and (any(PosTagger.tag_text(z)[0] == token_lemma for z in x.tag.tag_value.split()))),
                           image.image_tag))

    def get_image_list_from_table(self, caa_table):
        image_list = []
        sector_list = caa_table.table_sectors
        for sector in sector_list:
            # print(sector)
            for image in sector.images:
                image_list.append(image)
        return image_list

    def get_image_dictionary(self, keyword_tag_list, stem_token_lemmas, dizionario, image):
        print('START get_image_dictionary: ', datetime.now())
        for keyword_tag in keyword_tag_list:
            # Vedo se tra le keyword delle immagini in tabella esistono i token della frase
            token_list = list(filter(lambda x: (
                ps.stem(x) in stem_token_lemmas), keyword_tag.tag.tag_value.split()))

            for token in token_list:
                # per ogni token trovato all'interno delle mie immagini, lo aggiungo ad un dizionario
                # il campo occorenza terrà conto a quale token si riferisce quell'immagine
                # il costrutto if-else serve per aggiungere l'immagine che rappresenta il token trovato al dizionario
                # nel momento in cui quell'immagine esiste già(vado nell'else) io aggiungo solo il token a cui si riferisce
                # questo può essere utile quando un'immagine si riferisce a più di un token
                if (image.id in dizionario.keys()) == False:
                    dizionario[image.id] = {
                        'frequenza': 1, 'occorrenza': [token]}
                else:

                    # TODO VERIFICA STEM, FORSE POSSIAMO SALVARLO IN OCCORRENZA
                    if (token not in dizionario[image.id].get):
                        if ps.stem(token) not in [ps.stem(x) for x in dizionario[image.id].get]:
                            dizionario[image.id].get.append(token)
        print('END get_image_dictionary: ', datetime.now())
        return dizionario

    def get_image_dictionary_v1(self, keyword_tag_list, stem_token_lemmas, dizionario, image):
        print('START get_image_dictionary_v1: ', datetime.now())
        # TODO eliminare stop-words ?
        nlp_preprocess = NlpPreprocess()
        
        print(f"PRIMA KEYWORD TAG LIST: {keyword_tag_list}")

        ktl_splitted = [nlp_preprocess.elimination_stop_word_general(
            x.tag.tag_value) for x in keyword_tag_list]
        

        print(f"DOPO KEYWORD TAG LIST: {ktl_splitted}")

        #print(f'ktl_splitted: {ktl_splitted}')
        ktl_splitted_tmp = []

        # CALCIO DI RIGORE
        # ktl_splitted = [[calcio,di,rigore],[dare un calcio],[calcio]]

        #

        # TODO Funziona se la keyword è una sola
        for sublist in ktl_splitted:
            for item in sublist:
                #print(f'item in sublist: {item}')
                ktl_splitted_tmp.append(ps.stem(item))
                # ktl_splitted_tmp.append(item)

        # [calc, di, rig,]

        #print(f'N TOKEN =  {len(ktl_splitted_tmp)}')
        #print(f'ktl_splitted_tmp: {ktl_splitted_tmp}')
        n_token = len(ktl_splitted_tmp)



        token_list = list(filter(lambda x: (
            x in stem_token_lemmas), ktl_splitted_tmp))

        print(f'token_list len: {len(token_list)}')

        for k_token in token_list:
            print(f'TOKEN: {k_token}')
            if (image.id in dizionario.keys()) == False:
                print('Immagine NON ancora presente nel dizionario')
                dizionario[image.id] = {
                    'frequenza': 1, 'occorrenza': [k_token], 'n_token': n_token}
            else:
                print('Immagine presente nel dizionario')
                if (k_token not in dizionario[image.id].get('occorrenza')):
                    print('Token non presente tra le occorrenze dell\'immagine')
                    # if ps.stem(k_token) not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                    #     print('STEM del Token non presente tra le occorrenze STEMMATE dell\'immagine')
                    dizionario[image.id].get('occorrenza').append(k_token)

        print('END get_image_dictionary_v1: ', datetime.now())
        return dizionario

    def get_final_image_dictionary(self, image_list, stem_token_lemmas, dizionario):
        for image in image_list:

            print(f"IMAGE TEST: {image.label}")
            # Mi salvo tutte le keyword, sinonimi, tag generali dell'immagine i-esima
            keyword_tag_list = list(
                filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))

            print(f"STEM TOKEN LEMMAS: {stem_token_lemmas}")
            print(f"KEYWORD TAG LIST: {keyword_tag_list}")

            dizionario = self.get_image_dictionary_v1(keyword_tag_list=keyword_tag_list,
                                                      stem_token_lemmas=stem_token_lemmas,
                                                      dizionario=dizionario,
                                                      image=image,
                                                      )

            print(f'V1 - In tabella: {dizionario}')

        return dizionario

    '''def get_out_of_context_image_list(self, token):
        search = "%{}%".format(token)

        return ImageModel.query.join(ImageTagModel).join(TagModel).filter(
            ImageTagModel.tag_type == 'KEYWORD',
            TagModel.tag_value.ilike(search)
        ).all()'''

    '''def get_image_dictionary_out_of_context(self, out_context_image_list, token, token_stem, dizionario):

        for image in out_context_image_list:
            if (image.id in dizionario.keys()) == False:
                dizionario[image.id] = {
                    'frequenza': 1, 'occorrenza': [token]}
            else:
                if (token not in dizionario[image.id].get('occorrenza')):
                    if token_stem not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                        dizionario[image.id].get(
                            'occorrenza').append(token)
        return dizionario'''

    '''def get_left_over_tokens(self, dizionario, token_lemmas):
        oc_list = [x['occorrenza'] for x in list(dizionario.values())]

        occ_list = []
        for sublist in oc_list:
            occ_list.extend(sublist)

        # print(occ_list)
        # token filtered sono i token non trovati all'interno delle immagini in tabella
        token_filtered = list(
            filter(lambda x: ps.stem(x) not in occ_list, token_lemmas))
        return token_filtered'''

    def search_image_custom(self, img_syn,id_patient):
        count=0
        im_c=None
        image_custom_list=[]
        time_old=None
        time_new=None
        image_custom_list.extend(ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id==id_patient ).all())            
        image_custom2=[im for im in image_custom_list if im in img_syn]            
        for im_s in image_custom2:
            image_count=[]
            print(f"[TEST - search_image_custom] im_s.id : {im_s.id}")
            image_count.extend(ImageModel.query.join(PatientCsLogModel).filter(PatientCsLogModel.patient_id==id_patient,
                                                            PatientCsLogModel.image_id==im_s.id ).order_by(PatientCsLogModel.id.desc()).all())     
            print(len(image_count))
            if (len(image_count)>0):
                last_im_id=image_count[0].id
                time_new=(PatientCsLogModel.query.filter(PatientCsLogModel.patient_id==id_patient,
                                                                PatientCsLogModel.image_id==last_im_id ).order_by(PatientCsLogModel.id.desc()).first()).date
            if(len(image_count)>0 and len(image_count)>=count and (time_old==None or time_new>time_old)):
                count=len(image_count)
                time_old=time_new
                im_c=im_s.id                                 
        return im_c
    
    def search_image_prefer(self,img_syn,id_patient):
        count=0
        im_c=None
        image_custom_list=[]
        time_old=None
        time_new=None
        image_custom_list.extend(ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id!=id_patient ).all())
        im=[im1 for im1 in img_syn if im1 not in image_custom_list]
        for im_s in im:
            image_prefer_list=[]
            print(f"[TEST - search_image_prefer] im_s.id : {im_s.id}")
            image_prefer_list.extend(ImageModel.query.join(PatientCsLogModel).filter(PatientCsLogModel.patient_id==id_patient,
                                                                PatientCsLogModel.image_id==im_s.id ).order_by(PatientCsLogModel.id.desc()).all())                      
            print(len(image_prefer_list))
            if (len(image_prefer_list)>0):
                last_im_id=image_prefer_list[0].id
                time_new=(PatientCsLogModel.query.filter(PatientCsLogModel.patient_id==id_patient,
                                                                PatientCsLogModel.image_id==last_im_id ).order_by(PatientCsLogModel.id.desc()).first()).date            
            if(len(image_prefer_list)>0 and len(image_prefer_list)>=count and (time_old==None or time_new>time_old)):
                count=len(image_prefer_list)
                time_old=time_new
                im_c=im_s.id
        return im_c
    
    def search_imageLog(self,img_syn,id_patient):
        count=0
        im_c=None
        image_custom_list=[]
        time_old=None
        time_new=None
        image_custom_list.extend(ImageModel.query.join(image_patient).join(PatientModel).filter(PatientModel.id!=id_patient ).all())
        im=[im1 for im1 in img_syn if im1 not in image_custom_list]
        for im_s in im:
            image_db_list=[]
            print(f"[TEST - search_imageLog] im_s.id : {im_s.id}")
            image_db_list.extend(ImageModel.query.join(PatientCsLogModel).filter(PatientCsLogModel.image_id==im_s.id,
                                                                PatientCsLogModel.log_type=='INSERT_IMAGE' ).order_by(PatientCsLogModel.id.desc()).all())           
            print(len(image_db_list))             
            if (len(image_db_list)>0):
                last_im_id=image_db_list[0].id
                print(f"[TEST] id_patient : {id_patient}")
                print(f"[TEST] last_im_id : {last_im_id}")
                # time_new=(PatientCsLogModel.query.filter(PatientCsLogModel.patient_id==id_patient,
                #                                                 PatientCsLogModel.image_id==last_im_id ).order_by(PatientCsLogModel.id.desc()).first()).date
                time_new=(PatientCsLogModel.query.filter(PatientCsLogModel.image_id==last_im_id ).order_by(PatientCsLogModel.id.desc()).first()).date
            
            if(len(image_db_list)>0 and len(image_db_list)>=count and (time_old==None or time_new>time_old)):
                count=len(image_db_list)
                time_old=time_new
                im_c=im_s.id
        return im_c
    
    def search_phrase(self,id_patient,phrase,id_user,id_table):
        CS=ComunicativeSessionModel.query.filter(ComunicativeSessionModel.text_phrase==phrase).order_by(ComunicativeSessionModel.id.desc()).first()
        cs_output_image_id_list = []
        image_id_list=[]
        cs_id=None
        if(CS!=None):
            
            cs_out=CsOutputImageModel.query.filter(CsOutputImageModel.comunicative_session_id==CS.id, CsOutputImageModel.output_state_id != 3).all()
            
            for out in cs_out:
                print(f"[DEBUG] cs_out : {out.json()}")
                image_id = 0
                diction={}
                if(out.output_state_id==1):
                    diction['pos']=out.initial_position
                    image_id = out.image_id
                if(out.output_state_id==2):
                    if(out.correct_image_id!=None):
                        diction['pos']=out.initial_position
                        image_id=out.correct_image_id
                    else:
                        diction['pos']=out.final_position
                        image_id = out.image_id
            
                img_syn=[]
                print(f"TEST IMG: {image_id}")
                img_syn.append(ImageModel.find_by_id(image_id))
                for i in ImageSynonymModel.query.filter(or_(ImageSynonymModel.image_id==image_id,ImageSynonymModel.image_syn_id==image_id)).all():
                    if(i.image_id==image_id):
                        img_syn.append(ImageModel.find_by_id(i.image_syn_id))
                    if(i.image_syn_id==image_id):
                        img_syn.append(ImageModel.find_by_id(i.image_id))
                img_syn=list(OrderedDict.fromkeys(img_syn))
                im_c=self.search_image_custom(img_syn,id_patient)                
                if im_c!=None:                   
                    diction['img']=im_c                    
                else:                    
                    im_c=self.search_image_prefer(img_syn,id_patient)
                    if im_c!=None:                      
                        diction['img']=im_c                       
                    else:                       
                        diction['img']=image_id                    
                communicative_session = ComunicativeSessionModel(
                    id_user,
                    id_patient,
                    id_table,
                    phrase,
                    datetime.now(),
                )
                cs_id = communicative_session.save_to_db()
                cs_output_image = CsOutputImageModel(out.pos_tagging_token_ref,
                                                 out.pos_tagging_grammatical_type_ref,
                                                 cs_id,
                                                 diction['img'],
                                                 None, 
                                                 1, 
                                                 diction['pos'],
                                                 None, 
                                                 )
                cs_output_image_id = cs_output_image.save_to_db()
                cs_output_image_id_list.append(cs_output_image_id)
                image_id_list.append(diction)  

        return image_id_list,cs_output_image_id_list,cs_id
    
    def search_phrase_Sog(self,id_patient,phrase,id_user,id_table):
        CS=ComunicativeSessionModel.query.filter(ComunicativeSessionModel.text_phrase==phrase,
                                                 ComunicativeSessionModel.patient_id==id_patient).order_by(ComunicativeSessionModel.id.desc()).first()        
        cs_output_image_id_list = []
        image_id_list=[]
        cs_id=None
        if(CS!=None):
            id=CS.id
            cs_out=CsOutputImageModel.query.filter(CsOutputImageModel.comunicative_session_id==id).all()

            communicative_session = ComunicativeSessionModel(
                    id_user,
                    id_patient,
                    id_table,
                    phrase,
                    datetime.now(),
                )
            cs_id = communicative_session.save_to_db()
            
            for out in cs_out:
                print(f"Cs output image ID: {out.id}")
                
                diction={}
                if(out.output_state_id==1):
                    diction['img']=out.image_id
                    diction['pos']=out.initial_position
                    
                if(out.output_state_id==2):
                    if(out.correct_image_id!=None):
                        diction['img']=out.correct_image_id
                        diction['pos']=out.initial_position
                        
                    else:
                        diction['img']=out.image_id
                        diction['pos']=out.final_position
                                                  
                
                if len(diction) > 0:
                    cs_output_image = CsOutputImageModel(out.pos_tagging_token_ref,
                                                    out.pos_tagging_grammatical_type_ref,
                                                    cs_id,
                                                    diction['img'],
                                                    None, 
                                                    1,  
                                                    diction['pos'],
                                                    None,
                                                    )
                
                    cs_output_image_id = cs_output_image.save_to_db()
                    cs_output_image_id_list.append(cs_output_image_id)
                    image_id_list.append(diction)
        
        return image_id_list,cs_output_image_id_list,cs_id
        
    def create_image_dictionary(self, id_table, token_list,phrase):
        
        print(f"[13092023] token_list: {token_list}")

        stem_token_list = []
        image_list = []


        token_list_filtered = list(filter(lambda x: x != '?' and x != '!', token_list))
        
        
        for token in token_list_filtered:
            stem_token_list.append(ps.stem(token))
        
        wsd_model = WSDModel()
        prediction_list = wsd_model.wsd_algorithm(phrase=phrase)

        
        
        # image_dict = {}

        for prediction in prediction_list:
            if len(prediction):
                df=(prediction)[0][0]
                if df:
                    k = str(df)
                    lem = wn.lemma_from_key(k)
                    synset_name=".".join(str(lem)[7:].split('.')[0:2])
                    print(f"Synset estratto: {str(lem)[7:]}")

                    im_list=ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(synset_name == SynsetModel.synset_name_short).all()
                    # image_dict[synset_name] = ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(synset_name == SynsetModel.synset_name_short).all()
                    image_list.extend(im_list)
                    
                    if (len(im_list))== 0:
                        hypernyms = lem.synset().hypernyms()
                        for h in hypernyms:
                            synset_name=".".join(str(h)[8:].split('.')[0:2])
                            print(f"Iperonimo estratto: {synset_name}")
                            image_list.extend(ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(synset_name == SynsetModel.synset_name_short).all())
                            # image_dict[synset_name] = ImageModel.query.join(ass_image_synset).join(SynsetModel).filter(synset_name == SynsetModel.synset_name_short).all()
                    
                    print(f"Prima del filtro ricavo : {len(image_list)} immagini")
                    
                    npl_preprocess = NlpPreprocess()
                    t, token_lemmas, p = npl_preprocess.get_token_lemmas(
                                phrase=phrase)
                    
                    print(f"Token stemmatizzati per il match: {stem_token_list}")

                    print("PRIMA:")
                    
                    for im in image_list:
                        print(f"IMMAGINE: {im.label}")
                    
                    image_list=list(filter(lambda z:
                                                any( len(list(tok for tok in stem_token_list for tag in x.tag.tag_value.lower().split() if tok in tag or tag in tok))>0 
                                                and x.tag_type=="KEYWORD" for x in z.image_tag
                                                            ),
                                                image_list)
                                        )
                    # image_dict[synset_name]=list(filter(lambda z:
                    #                             any( len(list(tok for tok in stem_token_list for tag in x.tag.tag_value.lower().split() if tok in tag or tag in tok))>0 
                    #                             and x.tag_type=="KEYWORD" for x in z.image_tag
                    #                                         ),
                    #                             image_dict[synset_name])
                    #                     )
                    
                    # if len(image_dict[synset_name]) == 0:
                    #     pass
                    
                    
                    
                    print(f"Dopo del filtro ricavo : {len(image_list)} immagini")
                    
                    '''image_list=list(filter(lambda z:
                                                any( len(list(set(x.tag.tag_value.split()).intersection(stem_token_list)))>0 and x.tag_type=="KEYWORD" for x in z.image_tag
                                                            ),
                                                image_list)
                                        )'''
                    #o il tag value o token list devono essere lemmatizzati altrimenti batterie diverso da batteria
                    '''image_list=list(filter(lambda z:
                                                any(x.tag.tag_value  in token_list and x.tag_type=="KEYWORD" for x in z.image_tag
                                                            ),
                                                image_list)
                                        )'''
                    
        #image_list = self.get_image_list_from_table(caa_table=caa_table)

        
        #print('fine for')
        #print(datetime.now())
        # istanzio un oggetto di tipo SnowballStemmer utile per il processo di stemming
        '''stem_token_list = []

        # token stemmatizzati
        for token in token_list:
            stem_token_list.append(ps.stem(token))'''
        synonym_tag_dict = {}
        general_tag_dict = {}
        dizionario = {}

        # QUESTO CICLO MI TROVA TUTTI I POSSIBILI MATCH TRA PAROLE E KEYWORD IMMAGINI DENTRO LA TABELLA
        print('Ricerca in tabella: Start ', datetime.now())
        print(f"Lista immagini SYnset: {image_list}")
        dizionario = self.get_final_image_dictionary(
            image_list=image_list,
            stem_token_lemmas=stem_token_list,
            dizionario=dizionario
        )
        print('DIZIONARIO')
        print(dizionario)
        print('Fine ricerca immagini in tabella', datetime.now())

        '''# Per tutti token non trovati all'interno della tabella, vedo fuori della tabella e considero i contesti della tabella
        token_filtered = self.get_left_over_tokens(
            dizionario=dizionario,
            token_lemmas=token_list,
        )

        print(f'TOKEN FILTERED - ricerca in tabella: {token_filtered}')

        # FLAG PER STATO LOG
        in_table = True
        not_in_db = False
        log_find_in_table = 'FIND_IN_TABLE'
        log_out_of_table = 'FIND_OUT_OF_TABLE'
        log_not_present_in_db = 'IMAGE_NOT_PRESENT_IN_DB'

        if(len(token_filtered) != 0):
            # flag log stato
            not_in_db = True

            for token in token_filtered:
                token_stem = ps.stem(token)

                out_context_image_list = self.get_out_of_context_image_list(
                    token=token
                )

                pos_tag_token = PosTaggingModel.find_by_composite_id(token, 22)
                if token == '?':

                    out_context_image_list.extend(
                        [ImageModel.find_by_id(29218)])

                elif token == 'o':
                    out_context_image_list.extend(
                        [ImageModel.find_by_id(28862)])

                elif pos_tag_token:
                    out_context_image_list.extend(ImageModel.query
                                                  .join(ass_image_grammatical_type)
                                                  .join(GrammaticalTypeModel)
                                                  .filter(GrammaticalTypeModel.id == 22, ImageModel.label.ilike(f"%{token}%")).all())

                image_list.extend(out_context_image_list)

                print('Ricerca fuori contesto: Start ', datetime.now())
                dizionario = self.get_final_image_dictionary(
                    image_list=out_context_image_list,
                    stem_token_lemmas=stem_token_list,
                    dizionario=dizionario
                )
                print('DIZIONARIO')
                print(dizionario)
                print('Fine ricerca immagini fuori contesto', datetime.now())'''

        return dizionario, image_list, stem_token_list

    @jwt_required()
    def post(self):

        data = _search_parser.parse_args()
        print(f"Frase inserita {data['phrase']}")
        phrase = data['phrase']
        id_table = request.args.get("id_table", type=int, default=None)
        id_patient = request.args.get("id_patient", type=int, default=None)
        id_user = request.args.get("id_user", type=int, default=None)

        id_table = None if id_table == 'null' else id_table
        id_patient = None if id_patient == 'null' else id_patient

        print(f"patient_id: {id_patient}, type: {type(id_patient)}")
        print(f"table_id: {id_table}")
        
        if id_table != None and id_patient != None:
            dict_image_position,cs_output_image_id_list,cs_id=self.search_phrase_Sog(id_patient,phrase,id_user,id_table)
                
            dict_image_position=sorted(dict_image_position, key=lambda x: x['pos'])
            caa_images_sorted=[ImageModel.find_by_id(id['img']) for id in dict_image_position]
            
            if(len(dict_image_position)>0):
                return {
                    "caa_images": [caa_image.json() for caa_image in caa_images_sorted],
                    "cs_output_image_id_list": cs_output_image_id_list,
                    "cs_id": cs_id
                }, 200
        
            dict_image_position,cs_output_image_id_list,cs_id=self.search_phrase(id_patient,phrase,id_user,id_table)
                
            dict_image_position=sorted(dict_image_position, key=lambda x: x['pos'])
            caa_images_sorted=[ImageModel.find_by_id(id['img']) for id in dict_image_position]


            if(len(dict_image_position)>0):
                return {
                    "caa_images": [caa_image.json() for caa_image in caa_images_sorted],
                    "cs_output_image_id_list": cs_output_image_id_list,
                    "cs_id": cs_id
                }, 200
        
        
        


        # 1. recupero la sessione comunicativa con stesso paziente e stessa frase
        # 2. Recupero tutte le cs_output_images della sessione comunicativa
        # 2.1 Controllo gli stati della cs_output_image 
        # 3. Salvo la nuova sessione comunicativa nel db (i dati sono copiati dalla vecchia sessione comunicativa)
        # 4. Salvo tutte le cs_output_images nel db (i dati sono copiati dalla vecchia sessione cs_output_image)
        
        communicative_session = ComunicativeSessionModel(
            id_user,
            id_patient,
            id_table,
            phrase,
            datetime.now(),
        )
        cs_id = communicative_session.save_to_db()

        in_table = False
        not_in_db = True
        log_find_in_table = 'FIND_IN_TABLE'
        log_out_of_table = 'FIND_OUT_OF_TABLE'
        log_not_present_in_db = 'IMAGE_NOT_PRESENT_IN_DB'

        # PROCESSING FRASE
        # token_lemmas = phrase_tokenized
        npl_preprocess = NlpPreprocess()
        
        # TODO elimiare token lemmas, sono gia inclusi in posttag m list
        token_dict, token_lemmas, pos_tag_m_list = npl_preprocess.get_token_lemmas(
            phrase=phrase)

        print(f'TOKEN LEMMAS : {token_lemmas}')

        final_token_list = []
        for token in token_dict.items():
            if(token[1]['grammatical_type'] == 'V'):
                final_token_list.append(token[1]['lemma'])
            else:
                final_token_list.append(token[0])

        dizionario, image_list, stem_token_lemmas = self.create_image_dictionary(
            token_list=final_token_list,
            id_table=id_table,
            phrase=phrase
        )



        print("###TEST###")
        print(f"dizionario: {dizionario}")
        print(f"image_list: {image_list}")
        print(f"stem_token_lemmas: {stem_token_lemmas}")
        print("###END###")

        token_not_found = []
        
        for lemma in stem_token_lemmas:
            found = any(lemma in valore['occorrenza'] for valore in dizionario.values())
            if not found:
                token_not_found.append(lemma)
        
        print(f"TOKEN LEMMAS: {token_lemmas}")
        print(f"TOKEN NOT FOUND: {token_not_found}")
        if len(token_not_found):

            tokens_to_find = list(filter(lambda x: any(token in x for token in token_not_found), token_lemmas))
            tokens_to_find = list(filter(lambda x: x != '?' and x != '!', tokens_to_find))

            print(f"tokens to find: {tokens_to_find}")

            if len(tokens_to_find):
                for t in tokens_to_find:
                    results = self.create_image_dictionary(
                        token_list=[t],
                        id_table=id_table,
                        phrase=t
                    )
                    dizionario.update(results[0]) # Estendo il dizionario
                    image_list.extend(results[1]) # Estendo la lista di immagini

        
        if(len(dizionario) == 0):
            print(f"[DEBUG] Tokens to find : {tokens_to_find}")
            return {
                "message": "Nessuna immagine trovata",
                "cs_id" : cs_id,
                "lemmas_not_found" : tokens_to_find,
            }, 404

        massimo2 = max([len(i['occorrenza']) for i in dizionario.values()])
        print('MASSIMO')
        print(massimo2)
        traduzione = []
        #tok = token_lemmas
        print(f'dizionario prima dell\'algoritmo finale:\n{dizionario}')

        # TODO
        # 1) ordinare le immagini per numero di occorrenze decrescente
        # 2) Per ogni immagine faccio il dep parcing del tag Keyword
        # 3) Confronto tra i due dependency parsing

        # PARTE IN CUI TROVO IL MATCH UNIVOCO WORD-IMMAGINI BASANDOMI SULLA LEN DI OCCORRENZA DEL DIZIONARIO
        # POSSO AVERE DUE SISTUAZIONI, AD UN IMMAGINE SONO ASSOCIATE PIù DI UN TOKEN(IF) , A TUTTE LE IMMAGINI
        # SONO ASSOCIATE UNO E UN SOLO TOKEN
        if massimo2 > 1:
            tok = []
            #tok.extend(stem_token_lemmas)
            tok.extend(stem_token_lemmas)

            # stem_tok = []
            # for t in tok:
            #     stem_tok.append(ps.stem(t))

            # Filtro tutti gli elementi che hanno un numero di token in occorrenza = massimo
            
            newDict = dict(filter(lambda elem: (
                (len(elem[1]['occorrenza'])) == massimo2), dizionario.items()))

            print(f'Nuovo dizionario: {newDict}')

            for key in newDict:
                # Se il token è nella lista di occorrenze
                if len(set(newDict[key].get('occorrenza')).intersection(set(tok))) > 0:
                    traduzione.append(key)
                    for j in newDict[key].get('occorrenza'):
                        if j in tok:
                            tok.remove(j)

            print(tok)

            if len(tok) != 0:
                for token in token_lemmas:
                    if ps.stem(token) in tok:
                        print(token)  #
                        flag = False
                        for key in dizionario.keys():
                            print(key)
                            image = list(filter(lambda x: x.id == key, image_list))[0]
                            keyword_tag_list = list(
                                filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
                            filtered_keyword_tag_list = list(filter(lambda x: ps.stem(
                                x.tag.tag_value) == ps.stem(token), keyword_tag_list))

                            if len(filtered_keyword_tag_list) > 0:

                                image_id = image.id
                                traduzione.append(image_id)
                                #occorrenza = dizionario.get(image_id)['occorrenza']
                                flag = True
                                #dizionario_traduzione[image_id] = {
                                #    'frequenza': 1, 'occorrenza': occorrenza}
                                #dizionario[image.id] = {
                                #    'frequenza': 1, 'occorrenza': occorrenza}
                                synonym_tag_list = list(
                                    filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                                general_tag_list = list(
                                    filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                                # synonym_tag_dict[image.id] = [
                                #     item.tag_id for item in synonym_tag_list]
                                # general_tag_dict[image.id] = [
                                #     item.tag_id for item in general_tag_list]
                                tok.remove(ps.stem(token))

                                break
                        if flag == False:

                            for key in dizionario.keys():
                                print(key)
                                image = list(filter(lambda x: x.id == key, image_list))[
                                    0]  # match tra id dizionario e id image_list
                                keyword_tag_list = list(
                                    filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
                                filtered2_keyword_tag_list = list(
                                    filter(lambda x: token in x.tag.tag_value, keyword_tag_list))
                                print(filtered2_keyword_tag_list)
                                if len(filtered2_keyword_tag_list) > 0:

                                    image_id = image.id
                                    traduzione.append(image_id)
                                    occorrenza = dizionario.get(image_id)['occorrenza']
                                    #dizionario_traduzione[image_id] = {
                                    #    'frequenza': 1, 'occorrenza': occorrenza}
                                    synonym_tag_list = list(
                                        filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                                    general_tag_list = list(
                                        filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                                    # synonym_tag_dict[image.id] = [
                                    #     item.tag_id for item in synonym_tag_list]
                                    # general_tag_dict[image.id] = [
                                    #     item.tag_id for item in general_tag_list]
                                    tok.remove(ps.stem(token))
                                    flag = True
                                if flag == True:
                                    break
                
                '''for token in tok:
                    flag = False
                    for image in image_list:

                        keyword_tag_list = list(filter(lambda x: x.tag_type == 'KEYWORD' and (
                            image.id in dizionario.keys()), image.image_tag))

                        for keyword_tag in keyword_tag_list:
                            if ps.stem(keyword_tag.tag.tag_value) == token:
                                # if keyword_tag.tag.tag_value == token:
                                image_id = image.id
                                traduzione.append(image_id)
                                occorrenza = dizionario.get(
                                    image_id)['occorrenza']
                                #dizionario_traduzione[image_id] = {'frequenza': 1, 'occorrenza': occorrenza}
                                #dizionario[image.id]={'frequenza': 1, 'occorrenza': occorrenza}
                                synonym_tag_list = list(
                                    filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                                general_tag_list = list(
                                    filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                                # synonym_tag_dict[image.id] = [
                                #     item.tag_id for item in synonym_tag_list]
                                # general_tag_dict[image.id] = [
                                #     item.tag_id for item in general_tag_list]

                                tok.remove(token)

                                flag = True
                                break
                        if flag == True:
                            break'''

            dizionario_traduzione = dict(
                filter(lambda x: x[0] in traduzione, dizionario.items()))
            print('DIZIONARIO TRADUZIONE')
            print(dizionario_traduzione)
        else:
            dizionario_traduzione = {}
            tok = []
            tok.extend(token_lemmas)

            for token in token_lemmas:

                print(token)  #
                flag = False
                for key in dizionario.keys():
                    print(key)
                    image = list(filter(lambda x: x.id == key, image_list))[0]
                    keyword_tag_list = list(
                        filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
                    filtered_keyword_tag_list = list(filter(lambda x: ps.stem(
                        x.tag.tag_value) == ps.stem(token), keyword_tag_list))

                    if len(filtered_keyword_tag_list) > 0:

                        image_id = image.id
                        traduzione.append(image_id)
                        occorrenza = dizionario.get(image_id)['occorrenza']
                        flag = True
                        dizionario_traduzione[image_id] = {
                            'frequenza': 1, 'occorrenza': occorrenza}
                        dizionario[image.id] = {
                            'frequenza': 1, 'occorrenza': occorrenza}
                        synonym_tag_list = list(
                            filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                        general_tag_list = list(
                            filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                        # synonym_tag_dict[image.id] = [
                        #     item.tag_id for item in synonym_tag_list]
                        # general_tag_dict[image.id] = [
                        #     item.tag_id for item in general_tag_list]
                        tok.remove(token)

                        break

                if flag == False:

                    for key in dizionario.keys():
                        print(key)
                        image = list(filter(lambda x: x.id == key, image_list))[
                            0]  # match tra id dizionario e id image_list
                        keyword_tag_list = list(
                            filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))
                        filtered2_keyword_tag_list = list(
                            filter(lambda x: token in x.tag.tag_value, keyword_tag_list))
                        print(filtered2_keyword_tag_list)
                        if len(filtered2_keyword_tag_list) > 0:

                            image_id = image.id
                            traduzione.append(image_id)
                            occorrenza = dizionario.get(image_id)['occorrenza']
                            dizionario_traduzione[image_id] = {
                                'frequenza': 1, 'occorrenza': occorrenza}
                            synonym_tag_list = list(
                                filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                            general_tag_list = list(
                                filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                            # synonym_tag_dict[image.id] = [
                            #     item.tag_id for item in synonym_tag_list]
                            # general_tag_dict[image.id] = [
                            #     item.tag_id for item in general_tag_list]
                            tok.remove(token)
                            flag = True
                        if flag == True:
                            break

        print('DIZIONARIO TRADUZIONE')
        print(dizionario_traduzione)
        
        # sc_output_immagine
        cs_output_image_id_list = []
        
        dict_image_position=[]
        
        for image_id in dizionario_traduzione.keys():
            img_syn=[]
            diction={}
            img_syn.append(ImageModel.find_by_id(image_id))
            for i in ImageSynonymModel.query.filter(or_(ImageSynonymModel.image_id==image_id,ImageSynonymModel.image_syn_id==image_id)).all():
                if(i.image_id==image_id):
                    img_syn.append(ImageModel.find_by_id(i.image_syn_id))
                if(i.image_syn_id==image_id):
                    img_syn.append(ImageModel.find_by_id(i.image_id))
            print(f'sinonime: {img_syn}')
            img_syn=list(OrderedDict.fromkeys(img_syn))
            image=None       
            im_c=self.search_image_custom(img_syn,id_patient)
            print('im_c')
            print(im_c)
            if im_c!=None:
                image=im_c
                diction['img']=im_c
            else:
                im_c=self.search_image_prefer(img_syn,id_patient)
                if im_c!=None: #se è presente nei log del paziente allora prendo quella
                    image=im_c
                    diction['img']=im_c
                else:
                    im_c=self.search_imageLog(img_syn,id_patient)
                    if im_c!=None: #se è presente nei log del paziente allora prendo quella
                        image=im_c
                        diction['img']=im_c
                    else:#se non è presente nei log del paziente allora rimane quella estratta da cs_log_out
                        image=image_id
                        diction['img']=image_id

            stem_occ = [x for x in dizionario_traduzione[image_id].get(
                'occorrenza')]
            
            print("# TEST ")
            print(f"pos tag m list: {[x.lemma for x in pos_tag_m_list]}")
            print(f"stem occ: {stem_occ}")
            stem_occ_list = []
            for i in stem_occ:
                t = i.split(" ")
                for k in t:
                    stem_occ_list.append(ps.stem(k.lower()))
            
            print(f"stem occ list: {stem_occ_list}")

            # pos_tag_token = list(filter(lambda x: ps.stem(
            #     x.lemma.lower()) in stem_occ_list, pos_tag_m_list))

            pos_tag_token = list(filter(lambda x: any(element in x.lemma for element in stem_occ_list), pos_tag_m_list))
            

            # print(f"[13092023] traduzione: {traduzione}")
            # print(f"[13092023] diction.img: {diction['img']}")
            # print(f"[13092023] pos_tag_token: {pos_tag_token}")


            initial_position = 0
            image_to_order = ImageModel.find_by_id(diction['img'])
            
            for index, pos_tag in enumerate(pos_tag_m_list):
                print(f"[14092023] image label stem: {ps.stem(image_to_order.label)}")
                print(f"[14092023] lemma: {pos_tag.lemma}")
                if(ps.stem(pos_tag.lemma) in image_to_order.label):
                    print(f"[14092023] image label stem [OK]: {ps.stem(image_to_order.label)}")
                    initial_position = index

            # print(pos_tag_token[0])
            diction['pos']=initial_position
            cs_output_image = CsOutputImageModel(pos_tag_token[0].token,
                                                 pos_tag_token[0].grammatical_type_id,
                                                 cs_id,
                                                 diction['img'],
                                                 None,  # Immagine sostituita
                                                 1,  # ID stato Confirmed
                                                 initial_position,
                                                 None,  # Posizione finale
                                                 )
            print("CS OUTPUT IMAGE SAVED")
            cs_output_image_id = cs_output_image.save_to_db()
            cs_output_image_id_list.append(cs_output_image_id)
            dict_image_position.append(diction)
        
        
        dict_image_position=sorted(dict_image_position, key=lambda x: x['pos'])
        caa_images_sorted=[ImageModel.find_by_id(id['img']) for id in dict_image_position]


        # Creo una lista con tutte le occorrenze delle immagini risultanti
        # Controllo che tutte i lemmi contengano almeno un occorrenza delle immagini
        occurrency_list = set([lemma for element in dizionario.values() for lemma in element['occorrenza']])
        pos_tag_m_list = list(filter(lambda x: x.grammatical_type.tint_tag != 'RI' and x.grammatical_type.tint_tag != 'RD', pos_tag_m_list))
        lemmas_not_found = list(filter(lambda x: not any(occ in x for occ in occurrency_list), [pos_m.lemma for pos_m in pos_tag_m_list]))
        lemmas_not_found = list(filter(lambda x: x != '?' and x != '!', lemmas_not_found))

        print(f"[DEBUG] Lemmas Not found : {lemmas_not_found}")



        # gestiamo log sessione comunicativa
        communicative_session = ComunicativeSessionModel.find_by_id(cs_id)
        if in_table:
            session_log = SessionLogModel.find_by_title(log_find_in_table)
        else:
            session_log = SessionLogModel.find_by_title(log_out_of_table)
        communicative_session.cs_logs.append(session_log)
        if not_in_db:
            session_log = SessionLogModel.find_by_title(log_not_present_in_db)
            communicative_session.cs_logs.append(session_log)
        communicative_session.update_to_db()

        #suggested_id_dict = {}
        #tag_general__traduzione = []
        # print(f"TRADUZIONE: {traduzione}")
        # print(f"IMMAGINI: {diction['img']}")

        # DEVO RITORNARLI DIZIONARIO_TRADUZIONE
        #caa_images = []
        #caa_images = [ImageModel.find_by_id(id) for id in traduzione]

        # if(len(dict_image_position)>0):
        # Aggiungo i pittogrami relativi a token speciali
        check_special_character = False
        special_character = ""
        special_character_image_id = 0
        if '?' in final_token_list:
            caa_image = ImageModel.find_by_id_arasaac(3418)
            caa_images_sorted.append(caa_image)
            special_character = "?"
            special_character_image_id = caa_image.id
            check_special_character = True
        if '!' in final_token_list:
            caa_image = ImageModel.find_by_id_arasaac(3417)
            caa_images_sorted.append(caa_image)
            check_special_character = True
            special_character = "!"
            special_character_image_id = caa_image.id

        if check_special_character:
            initial_position = len(communicative_session.cs_output_images.all())
            cs_output_image = CsOutputImageModel(special_character,
                                        42,
                                        cs_id,
                                        special_character_image_id,
                                        None,  # Immagine sostituita
                                        1,  # ID stato Confirmed
                                        initial_position,
                                        None,  # Posizione finale
                                        )
            cs_output_image_id = cs_output_image.save_to_db()
            cs_output_image_id_list.append(cs_output_image_id)
            dict_image_position.append(diction)

        print(f"TEST LEMMAS NOT FOUND: {lemmas_not_found}")
        return {
            "caa_images": [caa_image.json() for caa_image in caa_images_sorted],
            "cs_output_image_id_list": cs_output_image_id_list,
            "lemmas_not_found" : lemmas_not_found,
            "cs_id": cs_id
        }, 200