from datetime import datetime
from flask_restful import Resource, reqparse, request
from models.comunicative_session.pos_tagging import PosTaggingModel
from models.tag import TagModel
from models.tag import ImageTagModel
from models.image import ImageModel
from models.grammatical_type import GrammaticalTypeModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.session_log import SessionLogModel
from utils.association_tables import ass_image_grammatical_type
from utils.nlp_preprocess import NlpPreprocess
from nltk.stem import SnowballStemmer

from flask_jwt_extended import jwt_required


_translate_parser = reqparse.RequestParser()
_translate_parser.add_argument(
    'text',
    type=str,
    required=True,
    help = 'Field - text - cannot be blank'
)


valid_options = ['TRANSLATE', 'SOCIAL_STORY']
ps = SnowballStemmer('italian')

class TranslateAlgorithm(Resource):

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

    def get_image_dictionary_v1(self, keyword_tag_list, stem_token_lemmas, dizionario, image):
        print('START get_image_dictionary_v1: ', datetime.now())
        # TODO eliminare stop-words ?
        for k_tag in keyword_tag_list:
            print(f'TAG KEYWORD: {k_tag.tag.tag_value}')
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
            print(f'IMAGE: {image.label}')
            # Recupero i tag KEYWORD dell'immagine i-esima
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


    def translate_social_story(self,final_token_list):
        dizionario = {}
        # istanzio un oggetto di tipo SnowballStemmer utile per il processo di stemming
        stem_token_list = []
        out_context_image_list = []

        # token stemmatizzati
        for token in final_token_list:
            stem_token_list.append(ps.stem(token))
        
        for token in final_token_list:
            out_context_image_list.extend(self.get_out_of_context_image_list(token=token))
            pos_tag_token = PosTaggingModel.find_by_composite_id(token, 22)

            for image in out_context_image_list:
                print(f'IMAGE OUT OF CONTEXT: {image.label}')

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

            for image in out_context_image_list:
                print(f'FINAL IMAGE OUT OF CONTEXT: {image.label}')

            print('Ricerca fuori contesto: Start ', datetime.now())
            dizionario = self.get_final_image_dictionary(
                image_list=out_context_image_list,
                stem_token_lemmas=stem_token_list,
                dizionario=dizionario
            )
        print('DIZIONARIO')
        print(dizionario)
        print('Fine ricerca immagini fuori contesto', datetime.now())

        return dizionario, out_context_image_list, stem_token_list


    def massimo_function(self,dizionario,image_list,token_lemmas):
        max_token_occurence = max([len(i['occorrenza']) for i in dizionario.values()])
        result = []

        if max_token_occurence > 1:
            pass
        else:
            print(f'token_lemmas: {token_lemmas}')
            print(f'dizionario: {dizionario}')
            print(f'image_list: {image_list}')
               


    @jwt_required()
    def post(self):
        data = _translate_parser.parse_args()
        text = data['text']
        id_table = request.args.get("id_table", type=int, default=None)
        id_patient = request.args.get("id_patient", type=int, default=None)
        id_user = request.args.get("id_user", type=int, default=None)
        option = request.args.get('option', type=str, default='TRANSLATE')

        if option.upper() not in valid_options:
            return {
                "message" : "Invalid option",
                "valid_options" : ["TRANSLATE","SOCIAL_STORY"]
            }, 400
        
        # TODO elimiare token lemmas, sono gia inclusi in posttag m list
        npl_preprocess = NlpPreprocess()
        token_dict, token_lemmas, pos_tag_m_list = npl_preprocess.get_token_lemmas(
            phrase=text)
        
        print(f'TOKEN LEMMAS : {token_dict}')

        final_token_list = []
        for token in token_dict.items():
            if(token[1]['grammatical_type'] == 'V'):
                final_token_list.append(token[1]['lemma'])
            else:
                final_token_list.append(token[0])
        

        communicative_session = ComunicativeSessionModel(
            id_user,
            id_patient,
            id_table,
            text,
            datetime.now(),
        )
        cs_id = communicative_session.save_to_db()

        if option.upper() == 'SOCIAL_STORY':
            print(final_token_list)
            dizionario, image_list, stem_token_lemmas = self.translate_social_story(final_token_list)

        if(len(dizionario) == 0):
            return {
                "message": "Nessuna immagine trovata"
            }, 404   
        
        
        massimo2 = max([len(i['occorrenza']) for i in dizionario.values()])
        print('MASSIMO')
        print(massimo2)
        traduzione = []
        #tok = token_lemmas
        print(f'Image list output: {image_list}')
        print(f'dizionario prima dell\'algoritmo finale:\n{dizionario}')

        if massimo2 > 1:
            tok = []
            tok.extend(stem_token_lemmas)

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
                    stem_occ_list.append(k)

            print(f'POS_TAG_M_LIST: {pos_tag_m_list}')
            print(f'STEM_OCC_LIST: {stem_occ_list}')
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