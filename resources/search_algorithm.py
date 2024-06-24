from email.mime import image
from token import NL
from tokenize import Token, tokenize
from flask_restful import Resource, reqparse, request
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
from models.user import UserModel
from models.autism_centre import AutismCentreModel
from utils.nlp_preprocess import NlpPreprocess
from nltk.stem import SnowballStemmer
from utils.association_tables import ass_image_context, ass_image_grammatical_type
import nltk
from datetime import datetime
from sqlalchemy.orm import defer
from sqlalchemy import or_

from difflib import SequenceMatcher

from flask_jwt_extended import jwt_required

_search_parser = reqparse.RequestParser()
_search_parser.add_argument(
    'phrase',
    type=str,
    required=False,
    help='This field cannot be blank',
)
_search_parser.add_argument('user_id', type=int, required=False)
_search_parser.add_argument(
    'patient_list',
    type=int,
    action='append'
)


# Constants
IMAGE_SEARCH_PRIVATE = 'IMAGE_SEARCH_PRIVATE'
IMAGE_SEARCH_STANDARD = 'IMAGE_SEARCH_STANDARD'
ps = SnowballStemmer('italian')


class Search(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument("phrase", type=str, required=True)
        self.parser.add_argument("user_id", type=int, required=False)
        self.parser.add_argument("patient_list", type=int, action="append")
        self.parser.add_argument("patient_id", type=int, required=False)
        
    def sort_by_similarity(self, image, token_lemmas):
            """
            Sorts the given image by similarity to the token lemmas.

            Parameters:
            image (Image): The image to be sorted.
            token_lemmas (list): The list of token lemmas to compare with.

            Returns:
            int: The maximum similarity score between the image and token lemmas.
            """
            keyword_tags = [tag.tag.tag_value for tag in image.image_tag if tag.tag_type == 'KEYWORD']
            
            if len(token_lemmas) > 1:
                token_counts = [sum(1 for token in token_lemmas if SequenceMatcher(None, token, tag).ratio() > 0.5) for tag in keyword_tags]
                return max(token_counts) if token_counts else 0
            
            similarities = [SequenceMatcher(None, token, tag).ratio() for token in token_lemmas for tag in keyword_tags]
            return max(similarities) if similarities else 0

    def preprocessing(self, phrase):
        """
        Preprocesses the given phrase by tokenizing, eliminating stop words, and extracting lemmas.

        Args:
            phrase (str): The input phrase to be preprocessed.

        Returns:
            list: A list of token lemmas after preprocessing.
        """
        nlp_preprocess = NlpPreprocess()

        phrase_tokenized = nlp_preprocess.tokenize(phrase)
        phrase_wsw = nlp_preprocess.elimination_stop_word(phrase_tokenized)
        
        token_lemmas = []

        for key, value in phrase_wsw.items():
            if value.get("grammatical_type") == "V":
                token_lemmas.append(value.get("lemma"))
            else:
                token_lemmas.append(key)

        return token_lemmas


    @jwt_required()
    def post(self):
            """
            Perform an image search algorithm based on the given parameters.
            
            Returns:
                A dictionary containing the search results.
            """
            args = self.parser.parse_args()
            phrase = args.get('phrase')
            user_id = args.get('user_id')
            patient_id = args.get('patient_id')

            token_lemmas = self.preprocessing(phrase)
            if len(token_lemmas) == 0:
                return {
                    "message" : "no-token-found",
                    "description" : "The phrase is empty or it contains only stop words"
                }, 500
            
            image_list = []
            for token in token_lemmas:
                search = f"%{token.lower()}%"
                
                # Search Primary Key tags
                pk_tag_images = [caa_image for caa_image in
                     ImageModel.query.options(defer(ImageModel.string_coding))
                     .join(ImageTagModel)
                     .join(TagModel)
                     .filter(TagModel.tag_value.like(search),ImageTagModel.tag_type == 'KEYWORD').all()
                     ]
                
                label_images = [caa_image for caa_image in
                                ImageModel.query.options(defer(ImageModel.string_coding))
                                .filter(ImageModel.label.ilike(f"%{token.lower()}%")).all()]
                
                image_list.extend(pk_tag_images)
                image_list.extend(label_images)
                
            # Remove images that belong to other users or other centres
            user_model = UserModel.find_by_id(user_id)
            user_id_list = [user_id]
            if user_model.autism_centre_id:
                autism_centre = AutismCentreModel.find_by_id(user_model.autism_centre_id)
                user_id_list.extend([user.id for user in autism_centre.users])
            
            image_list = list(filter(lambda x: x.user_id in user_id_list or x.user_id == None, image_list))
            
            # Remove images that belong to any patients
            if not patient_id:
                images_no_patient = []
                for image in image_list:
                    if len(image.patients) == 0:
                        images_no_patient.append(image)
                image_list = images_no_patient
            
            # Remove images that belong to other patients
            else:
                images_include_patient = []
                for image in image_list:
                    if any(patient_id == patient.id for patient in image.patients):
                        images_include_patient.append(image)
                    if len(image.patients) == 0:
                        images_include_patient.append(image)
            
            image_list = list(set(image_list))
            image_list.sort(key=lambda image: self.sort_by_similarity(image,token_lemmas), reverse=True)
                
            return {
            "caa_images": [caa_image.json() for caa_image in image_list],
            }, 200


class Translate(Resource):

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
        ktl_splitted = [nlp_preprocess.elimination_stop_word_general(
            x.tag.tag_value) for x in keyword_tag_list]

        print(f'ktl_splitted: {ktl_splitted}')
        ktl_splitted_tmp = []

        # CALCIO DI RIGORE
        # ktl_splitted = [[calcio,di,rigore],[dare un calcio],[calcio]]

        #

        # TODO Funziona se la keyword è una sola
        for sublist in ktl_splitted:
            for item in sublist:
                print(f'item in sublist: {item}')
                ktl_splitted_tmp.append(ps.stem(item))
                # ktl_splitted_tmp.append(item)

        # [calc, di, rig,]

        print(f'N TOKEN =  {len(ktl_splitted_tmp)}')
        print(f'ktl_splitted_tmp: {ktl_splitted_tmp}')
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
                if (k_token not in dizionario[image.id].get):
                    print('Token non presente tra le occorrenze dell\'immagine')
                    # if ps.stem(k_token) not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                    #     print('STEM del Token non presente tra le occorrenze STEMMATE dell\'immagine')
                    dizionario[image.id].get.append(k_token)

        print('END get_image_dictionary_v1: ', datetime.now())
        return dizionario

    def get_final_image_dictionary(self, image_list, stem_token_lemmas, dizionario):
        for image in image_list:

            # Mi salvo tutte le keyword, sinonimi, tag generali dell'immagine i-esima
            keyword_tag_list = list(
                filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))

            dizionario = self.get_image_dictionary_v1(keyword_tag_list=keyword_tag_list,
                                                      stem_token_lemmas=stem_token_lemmas,
                                                      dizionario=dizionario,
                                                      image=image,
                                                      )

            print(f'V1 - In tabella: {dizionario}')

        return dizionario

    def get_out_of_context_image_list(self, token):
        search = "%{}%".format(token)

        return ImageModel.query.join(ImageTagModel).join(TagModel).filter(
            ImageTagModel.tag_type == 'KEYWORD',
            TagModel.tag_value.ilike(search)
        ).all()

    def get_image_dictionary_out_of_context(self, out_context_image_list, token, token_stem, dizionario):

        for image in out_context_image_list:
            if (image.id in dizionario.keys()) == False:
                dizionario[image.id] = {
                    'frequenza': 1, 'occorrenza': [token]}
            else:
                if (token not in dizionario[image.id].get):
                    if token_stem not in [ps.stem(x) for x in dizionario[image.id].get]:
                        dizionario[image.id].get.append(token)
        return dizionario

    def get_left_over_tokens(self, dizionario, token_lemmas):
        oc_list = [x['occorrenza'] for x in list(dizionario.values())]

        occ_list = []
        for sublist in oc_list:
            occ_list.extend(sublist)

        # print(occ_list)
        # token filtered sono i token non trovati all'interno delle immagini in tabella
        token_filtered = list(
            filter(lambda x: ps.stem(x) not in occ_list, token_lemmas))
        return token_filtered

    def create_image_dictionary(self, id_table, token_list):

        # RECUPER LE IMMAGINI DALLA TABELLA IN USO
        caa_table = caa_table = CaaTableModel.find_by_id(id_table)
        image_list = self.get_image_list_from_table(caa_table=caa_table)

        # istanzio un oggetto di tipo SnowballStemmer utile per il processo di stemming
        stem_token_list = []

        # token stemmatizzati
        for token in token_list:
            stem_token_list.append(ps.stem(token))

        synonym_tag_dict = {}
        general_tag_dict = {}
        dizionario = {}

        # QUESTO CICLO MI TROVA TUTTI I POSSIBILI MATCH TRA PAROLE E KEYWORD IMMAGINI DENTRO LA TABELLA
        print('Ricerca in tabella: Start ', datetime.now())
        dizionario = self.get_final_image_dictionary(
            image_list=image_list,
            stem_token_lemmas=stem_token_list,
            dizionario=dizionario
        )
        print('DIZIONARIO')
        print(dizionario)
        print('Fine ricerca immagini in tabella', datetime.now())

        # Per tutti token non trovati all'interno della tabella, vedo fuori della tabella e considero i contesti della tabella
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
                print('Fine ricerca immagini fuori contesto', datetime.now())

        return dizionario, image_list, stem_token_list

    @jwt_required()
    def post(self):

        data = _search_parser.parse_args()
        phrase = data['phrase']
        id_table = request.args.get("id_table", None)
        id_patient = request.args.get("id_patient", None)
        id_user = request.args.get("id_user", None)
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
        )

        if(len(dizionario) == 0):
            return {
                "message": "Nessuna immagine trovata"
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
                print('Set OCCORRENZE:')
                print(set(newDict[key].get))
                print(f'Set TOKEN: {set(tok)}')

                if len(set(newDict[key].get).intersection(set(tok))) > 0:

                    traduzione.append(key)

                    for j in newDict[key].get:
                        # j_stem = ps.stem(PosTagger.tag_text(j)[0])
                        # print(f'POS TAGGER: {j_stem}')
                        # print(f'TOK: {tok}')
                        if j in tok:
                            tok.remove(j)

            print(tok)

            if len(tok) != 0:
                for token in tok:
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
                            break

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
        for image_id in dizionario_traduzione.keys():
            stem_occ = [x for x in dizionario_traduzione[image_id].get(
                'occorrenza')]
            stem_occ_list = []
            for i in stem_occ:
                t = i.split(" ")
                for k in t:
                    stem_occ_list.append(ps.stem(k))

            pos_tag_token = list(filter(lambda x: ps.stem(
                x.lemma) in stem_occ_list, pos_tag_m_list))
            # print(pos_tag_token[0])
            initial_position = traduzione.index(image_id)
            cs_output_image = CsOutputImageModel(pos_tag_token[0].token,
                                                 pos_tag_token[0].grammatical_type_id,
                                                 cs_id,
                                                 image_id,
                                                 None,  # Immagine sostituita
                                                 1,  # ID stato Confirmed
                                                 initial_position,
                                                 None,  # Posizione finale
                                                 )
            print("CS OUTPUT IMAGE SAVED")
            cs_output_image_id = cs_output_image.save_to_db()
            cs_output_image_id_list.append(cs_output_image_id)

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
        print(traduzione)

        # DEVO RITORNARLI DIZIONARIO_TRADUZIONE
        caa_images = []
        caa_images = [ImageModel.find_by_id(id) for id in traduzione]

        # caa_images_sorted = []
        # if len(caa_images) > 0:
        #     caa_images_sorted = self.sortCaaImageList(caa_images,token_list=token_lemmas)

        caa_images_sorted = []
        if len(caa_images) > 0:
            caa_images_sorted = self.sortCaaImageList(image_list=caa_images,
                                                      image_dict=dizionario_traduzione,
                                                      token_list=token_lemmas,
                                                      )

        return {
            "caa_images": [caa_image.json() for caa_image in caa_images_sorted],
            "cs_output_image_id_list": cs_output_image_id_list,
            "cs_id": cs_id
        }, 200


class ContextTable(Resource):
    
    @jwt_required()
    def get(self):
        id_table = request.args.get("id_table", None)
        image_list = []
        if id_table:
            # Lavoro sulla tabella
            caa_table = CaaTableModel.find_by_id(id_table)
            sector_list = caa_table.table_sectors
            for sector in sector_list:
                # print(sector)
                for image in sector.images:
                    image_list.append(image.json())

        lista_contesti = {}
        #  for image in image_list:
        #     for context in image.get('image_context'):
        #         if context.get('context_type') not in lista_contesti.keys():
        #             lista_contesti[context.get('context_type')]=1
        #             print('ok')
        #         else:
        #             lista_contesti[context.get('context_type')]=lista_contesti[context.get('context_type')]+1

        for image in image_list:
            # print(image.get('label'))
            general_tag_list = list(filter(lambda x: (x.get == 'GENERAL' and ((x.get != 'comunicazione') and ('verbo' not in x.get) and (x.get != 'linguaggio') and (x.get != 'vocabolario di base'))), image.get))
            for tag in general_tag_list:
                # print('TAG')
                if tag.get not in lista_contesti.keys():
                    lista_contesti[tag.get] = 1

                    # print(tag.get('tag_value'))
                else:
                    print('OK')
                    lista_contesti[tag.get] = lista_contesti[tag.get] + 1

        lista_contesti = sorted(lista_contesti.items(), key=lambda x: x[1])
        print(lista_contesti)
        # print(lista_contesti.values()/len(lista_contesti))

        return {
            # lista_contesti
        }, 200

        # image_list = [caa_image.json() for caa_image in ImageModel.query.all()]
        # if(len(tok)>0):
        #     image_list = [caa_image.json() for caa_image in ImageModel.query.all()]
        #     dizionario={}
        #     for k in tok:
        #          for i in image_list:
        #              for j in i.get('tag_list'):
        #                  if j.get('tag_type')=='KEYWORD' :
        #                      tokens=j.get('tag_value').split()
        #                      for s in tokens:
        #                          token_key=PosTagger.tag_text(s)
        #                          #print(tags)
        #                          #s_w=treetaggerwrapper.make_tags(tags)[0][2]
        #                          #print(s_w)
        #                          if token_key==k:
        #                              if (i.get('id') in dizionario.keys())==False:
        #                                  dizionario[i.get('id')]={'frequenza':1,'occorrenza':[k]}
        #                              else:
        #                                  print(dizionario[i.get('id')].get('frequenza'))
        #                                  dizionario[i.get('id')]['frequenza']=dizionario[i.get('id')].get('frequenza')+1
        #                                  dizionario[i.get('id')].get('frequenza')+1
        #                                  if (k not in dizionario[i.get('id')].get('occorrenza')):
        #                                      dizionario[i.get('id')].get('occorrenza').append(k)

        #     #print(dizionario)
        #     #massimo=max([int(i['frequenza']) for i in dizionario.values()])
        #     massimo2=max([len(i['occorrenza']) for i in dizionario.values()])
        #     newDict = dict(filter(lambda elem: ( (len(elem[1]['occorrenza']))==massimo2) , dizionario.items()))
        #     #print(newDict)

        #     for key in newDict:
        #         #print(newDict[key].get('occorrenza'))
        #         if len(set(newDict[key].get('occorrenza')).intersection(set(tok)))>0:
        #             traduzione.append(key)
        #             for j in newDict[key].get('occorrenza'):
        #                 if j in tok:
        #                     tok.remove(j)

        # print(traduzione)

        # Lavoro su tutto il set di immagini
