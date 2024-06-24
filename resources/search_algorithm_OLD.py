from email.mime import image
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
from utils.nlp_preprocess import NlpPreprocess
from nltk.stem import SnowballStemmer
from utils.association_tables import ass_image_context, ass_image_grammatical_type
import nltk
from datetime import datetime
from sqlalchemy.orm import defer
from sqlalchemy import or_

from flask_jwt_extended import jwt_required

_search_parser = reqparse.RequestParser()
_search_parser.add_argument(
    'phrase',
    type=str,
    required=True,
    help='This field cannot be blank',
)
_search_parser.add_argument(
    'patient_list',
    type=int,
    action='append'
)


class Search(Resource):
    
    @jwt_required()
    def get(self):
        # PRE-PROCESSING FRASE(Tokenizzazione, eliminazione stop word, Pos tagging, dependecy parsing)
        data = _search_parser.parse_args()
        phrase = data['phrase']
        patient_list = data['patient_list']

        phrase_tokenized = NlpPreprocess.tokenize(phrase)
        phrase_wsw = NlpPreprocess.elimination_stop_word(phrase_tokenized)
        token_lemmas = []
        for i in phrase_wsw.keys():
            token_lemmas.append(phrase_wsw[i].get.lower())

        print(token_lemmas)

        # Restringo il campo di ricerca per velocizzare la ricerca delle immagini e salvo il tutto in un dizionario
        image_list = []

        for k in token_lemmas:
            search = "%{}%".format(k)
            print(search)
            image_list.extend(
                [caa_image for caa_image in
                 ImageModel.query.options(defer(ImageModel.string_coding))
                 .join(ImageTagModel)
                 .join(TagModel)
                 .filter(or_(TagModel.tag_value.like(search), ImageModel.label.ilike(f"%{k}%"))).all()
                 ])

            print(f'IMAGE LIST: {image_list}')
            print(f'patient list: {patient_list}')



            image_list = list(filter(lambda z:
                                len(z.patients) == 0 or 
                                list(filter(lambda x:
                                            x.id in patient_list,
                                            z.patients
                                            )),
                                image_list)
                         )

        # Algoritmo di ricerca, ciclo sui token e trovo il match con le immagini con stessa keyword
        # all'interno del dizionario creato precedentemente
        for token in token_lemmas:
            match = list(filter(lambda z:
                                list(filter(lambda x:
                                            (x.tag_type == 'KEYWORD' and
                                             token in x.tag.tag_value.split(' ')) or token in z.label.lower(),
                                            z.image_tag
                                            )),
                                image_list)
                         )

        # print(match)
        print(f'lista immagini: {len([caa_image for caa_image in match])}')
        return {
            "caa_images": [caa_image.json() for caa_image in match],
        }, 200


class Translate(Resource):
    def filter_key_word_list(self, image, token_lemma):
        return list(filter(lambda x: (x.tag_type == 'KEYWORD'
                                      and (any(PosTagger.tag_text(z)[0] == token_lemma for z in x.tag.tag_value.split()))),
                           image.image_tag))

    @jwt_required()
    def get(self):

        data = _search_parser.parse_args()
        phrase = data['phrase']
        id_table = request.args.get("id_table", None)
        id_patient = request.args.get("id_patient", None)
        id_user = request.args.get("id_user", None)
        communicative_session = ComunicativeSessionModel(
            id_user, id_patient, id_table, phrase, datetime.now())
        cs_id = communicative_session.save_to_db()

       # PROCESSING FRASE

        phrase_tokenized_dict = NlpPreprocess.tokenize(phrase)

        phrase_wsw = NlpPreprocess.elimination_stop_word(phrase_tokenized_dict)
        # CREAZIONE postagging model
        dizionario_grammatical_type = {	'A': 'ADJECTIVE',
                                        'S': 'NOUN',
                                        'V': 'VERB',
                                        'B': 'ADVERB',
                                        'FS': 'PUNTUACTION',
                                        'PQ': 'PRONOUN',
                                        'PC': 'PRONOUN',
                                        'CC': 'PRONOUN'
                                        }
        pos_tag_m_list = []
        for i in phrase_wsw.keys():
            grammatical_type = dizionario_grammatical_type.get(
                phrase_wsw[i].get)
            grammatical_type_id = GrammaticalTypeModel.find_by_value(
                grammatical_type).id
            tense = TenseModel.find_by_value(phrase_wsw[i].get)
            tense_id = tense.id if tense else None
            verbal_form = VerbalFormModel.find_by_value(
                phrase_wsw[i].get)
            verbal_form_id = verbal_form.id if verbal_form else None
            pos_tag_from_db = PosTaggingModel.find_by_composite_id(
                i, grammatical_type_id)
            if pos_tag_from_db:
                pos_tag_m_list.append(pos_tag_from_db)
            else:
                pos_tag_m = PosTaggingModel(i, grammatical_type_id, phrase_wsw[i].get, tense_id, verbal_form_id, phrase_wsw[i].get, phrase_wsw[i].get)
                pos_token, pos_grammatical_type_id = pos_tag_m.save_to_db()
                pos_tag_m_list.append(pos_tag_m)
                print(f'new pos token {pos_token}')
                print(f'new gramm type id token {pos_grammatical_type_id}')
                print(f'tokken lemma {pos_tag_m.lemma}')

        phrase_tokenized = [x.lemma for x in pos_tag_m_list]

        token_lemmas = phrase_tokenized

        image_list = []

        # Lavoro sulla tabella scelta, estraggo le immagini della tabella. Tabella che sarà il primo step per la traduzione
        caa_table = CaaTableModel.find_by_id(id_table)
        sector_list = caa_table.table_sectors
        for sector in sector_list:
            # print(sector)
            for image in sector.images:
                image_list.append(image)
        # convertire in set-> list(set())
        dizionario = {}

        # istanzio un oggetto di tipo SnowballStemmer utile per il processo di stemming
        ps = SnowballStemmer('italian')
        stem_token_lemmas = []

        # Stampa dei token a seguito di pre-processing
        print('TOKEN FRASE ')
        print(token_lemmas)

        # token stemmatizzati
        for token in pos_tag_m_list:
            stem_token_lemmas.append(ps.stem(token.lemma))

        synonym_tag_dict = {}
        general_tag_dict = {}

        # QUESTO CICLO MI TROVA TUTTI I POSSIBILI MATCH TRA PAROLE E KEYWORD IMMAGINI DENTRO LA TABELLA
        print('Ricerca in tabella: Start ', datetime.now())
        for image in image_list:

            # Mi salvo tutte le keyword, sinonimi, tag generali dell'immagine i-esima
            keyword_tag_list = list(
                filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))

            # Per ogni keyword dentro la lista delle keyword di quella determinata immagine
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

                        #dizionario[image.id]['frequenza'] = dizionario[image.id].get('frequenza')+1
                        # dizionario[image.id].get('frequenza')+1
                        if (token not in dizionario[image.id].get('occorrenza')):
                            if ps.stem(token) not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                                dizionario[image.id].get(
                                    'occorrenza').append(token)
        print('DIZIONARIO')
        print(dizionario)
        print('Fine ricerca immagini in tabella', datetime.now())

        # Per tutti token non trovati all'interno della tabella, vedo fuori della tabella e considero i contesti della tabella

        oc_list = [x['occorrenza'] for x in list(dizionario.values())]

        occ_list = []
        for sublist in oc_list:
            for item in sublist:
                occ_list.append(ps.stem(item))

        # print(occ_list)
        # token filtered sono i token non trovati all'interno delle immagini in tabella
        token_filtered = list(
            filter(lambda x: ps.stem(x) not in occ_list, token_lemmas))

        print(token_filtered)

        # FLAG PER STATO LOG
        in_table = True
        not_in_db = False
        log_find_in_table = 'FIND_IN_TABLE'
        log_out_of_table = 'FIND_OUT_OF_TABLE'
        log_not_present_in_db = 'IMAGE_NOT_PRESENT_IN_DB'

        context_list = [ctx.context_type for ctx in caa_table.context]
        # print('contesti')
        # print((context_list))

        # QUESTA CONDIZIONE MI SERVE PER CAPIRE SE CI SONO TOKEN NON PRESENTI DENTRO LA TABELLA
        # ENTRANDO NELL'IF LA LA MIE IMMAGINI DIVENTANO QUELLE FORNITE DAL CONTESTO DELLA TABELLA

        # image_list conterrà le immagini della tabella pù tutti i verbi, punto interrogativo e le immagini che comprendono
        # il contesto della tabella
        print('Ricerca fuori tabella considerando contesti', datetime.now())
        tmp_image_list = []
        if len(token_filtered) > 0:
            # cambio stato flag per log
            in_table = False

            print('IMMAGINI NON IN TABELLA')
            # contesti per le immagini
            context_list = [ctx.context_type for ctx in caa_table.context]

            image_list.extend(ImageModel.query
                              .join(ImageTagModel)
                              .join(TagModel)
                              .filter(ImageTagModel.tag_type == 'GENERAL', TagModel.tag_value.in_((context_list))).all())

            # Aggiunta dei verbi
            # image_list.extend(ImageModel.query
            #                   .join(ass_image_grammatical_type)
            #                   .join(GrammaticalTypeModel)
            #                   .filter(GrammaticalTypeModel.id == 22).all())

            # Aggiunta punto interrogativo
            image_list.extend([ImageModel.find_by_id(29218)])
            image_list.extend([ImageModel.find_by_id(28862)])
            print(f'dimensione lista: {len(image_list)}')
            list(set(image_list))

            token_l = []
            token_l.extend(token_filtered)

            for token in token_l:

                pos_tag_token = PosTaggingModel.find_by_composite_id(token, 22)
                if token == '?':

                    tmp_image_list.extend([ImageModel.find_by_id(29218)])

                elif token == 'o':
                    tmp_image_list.extend([ImageModel.find_by_id(28862)])
                elif pos_tag_token:
                    tmp_image_list.extend(ImageModel.query
                                          .join(ass_image_grammatical_type)
                                          .join(GrammaticalTypeModel)
                                          .filter(GrammaticalTypeModel.id == 22).all())

                else:
                    # contesti per le immagini
                    context_list = [
                        ctx.context_type for ctx in caa_table.context]

                    tmp_image_list.extend(ImageModel.query
                                          .join(ImageTagModel)
                                          .join(TagModel)
                                          .filter(ImageTagModel.tag_type == 'GENERAL', TagModel.tag_value.in_((context_list))).all())

                print('token')
                print(token)

                for image in tmp_image_list:

                    # print(image.id)
                    # qui dentro vado a vedere se i token sono presenti all'interno della nuova image_list
                    # keyword_tag_list = list(
                    #     filter(lambda x: x.tag_type == 'KEYWORD', image.image_tag))

                    # [[mangiare],[vietato,mangiare]] => [mangiare,vietato]

                    # Risultato query
                    # [[mangiare,un,panino],[mangiare]] => [mangiare,un,panino]

                    keyword_tag_list = TagModel.query.join(ImageTagModel).join(ImageModel).filter(
                        ImageModel.id == image.id,
                        ImageTagModel.tag_type == 'KEYWORD'
                    ).all()

                    # print(f'KEYWORD TAG LIST: {keyword_tag_list}')
                    ktl_splitted = [x.tag_value.split()
                                    for x in keyword_tag_list]

                    ktl_splitted_tmp = []
                    for sublist in ktl_splitted:
                        for item in sublist:
                            ktl_splitted_tmp.append(ps.stem(item))

                    # print(f'KEYWORD TAG LIST SPLITTED: {ktl_splitted_tmp}')

                    token_list = list(filter(lambda x: (
                        x in stem_token_lemmas), ktl_splitted_tmp))

                    for k_token in token_list:
                        image_id = image.id
                        if (image.id in dizionario.keys()) == False:
                            dizionario[image.id] = {
                                'frequenza': 1, 'occorrenza': [k_token]}
                        else:
                            # print(dizionario[i.get('id')].get('frequenza'))
                            dizionario[image.id]['frequenza'] = dizionario[image.id].get(
                                'frequenza')+1
                            dizionario[image.id].get('frequenza')+1
                            if (k_token not in dizionario[image.id].get('occorrenza')):
                                if ps.stem(k_token) not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                                    dizionario[image.id].get(
                                        'occorrenza').append(k_token)
                    # if len(token_list) > 0:
                    #     break

                    # for keyword_tag in keyword_tag_list:

                    #     token_list = list(filter(lambda x: (
                    #         ps.stem(x) in stem_token_lemmas), keyword_tag.tag.tag_value.split()))

                    #     for k_token in token_list:
                    #         image_id = image.id
                    #         if (image.id in dizionario.keys()) == False:
                    #             dizionario[image.id] = {
                    #                 'frequenza': 1, 'occorrenza': [k_token]}
                    #         else:
                    #             # print(dizionario[i.get('id')].get('frequenza'))
                    #             dizionario[image.id]['frequenza'] = dizionario[image.id].get(
                    #                 'frequenza')+1
                    #             dizionario[image.id].get('frequenza')+1
                    #             if (k_token not in dizionario[image.id].get('occorrenza')):
                    #                 if ps.stem(k_token) not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                    #                     dizionario[image.id].get(
                    #                         'occorrenza').append(k_token)
                    #     if len(token_list) > 0:
                    #         break

        oc_list = [x['occorrenza'] for x in list(dizionario.values())]

        occ_list = []
        for sublist in oc_list:
            for item in sublist:
                occ_list.append(ps.stem(item))

        token_filtered = list(
            filter(lambda x: ps.stem(x) not in occ_list, token_lemmas))

        image_list.extend(tmp_image_list)
        print('FINE Ricerca fuori tabella  considerando contesti', datetime.now())

        # QUESTO ULTIMO STEP MI PERMETTE DI TROVARE PAROLE CHE NON SONO ESISTENTI ALL'INTERNO DEL DB MA CHE SONO SIMILI
        # AD ALTRE PRESENTI

        print(
            'Inizio Ricerca fuori tabella e contesi considerando contesti', datetime.now())

        out_context_image_list = []
        if(len(token_filtered) != 0):
            # flag log stato
            not_in_db = True

            print('PAROLA INESISTENTE')

            for i in token_filtered:
                #flag_1 = False
                print(i)
                token_stem = ps.stem(i)
                search = "%{}%".format(token_stem)

                out_context_image_list = ImageModel.query.join(ImageTagModel).join(TagModel).filter(
                    ImageTagModel.tag_type == 'KEYWORD',
                    TagModel.tag_value_stem.ilike(search)
                ).all()

                for image in out_context_image_list:
                    image_id = image.id
                    if (image.id in dizionario.keys()) == False:
                        dizionario[image.id] = {
                            'frequenza': 1, 'occorrenza': [i]}
                    else:
                        print(dizionario[i.get].get(
                            'frequenza'))
                        dizionario[image.id]['frequenza'] = dizionario[image.id].get + 1
                        dizionario[image.id].get('frequenza')+1
                        if (i not in dizionario[image.id].get('occorrenza')):
                            if token_stem not in [ps.stem(x) for x in dizionario[image.id].get('occorrenza')]:
                                dizionario[image.id].get(
                                    'occorrenza').append(i)

        image_list.extend(out_context_image_list)
        print(
            'FINE Ricerca fuori tabella e contesto  considerando contesti', datetime.now())

        massimo2 = max([len(i['occorrenza']) for i in dizionario.values()])
        print('MASSIMO')
        print(massimo2)
        traduzione = []
        #tok = token_lemmas
        print(dizionario)

        # PARTE IN CUI TROVO IL MATCH UNIVOCO WORD-IMMAGINI BASANDOMI SULLA LEN DI OCCORRENZA DEL DIZIONARIO
        # POSSO AVERE DUE SISTUAZIONI, AD UN IMMAGINE SONO ASSOCIATE PIù DI UN TOKEN(IF) , A TUTTE LE IMMAGINI
        # SONO ASSOCIATE UNO E UN SOLO TOKEN
        if massimo2 > 1:
            tok = []
            tok.extend(token_lemmas)
            newDict = dict(filter(lambda elem: (
                (len(elem[1]['occorrenza'])) == massimo2), dizionario.items()))

            print(newDict)

            for key in newDict:
                if len(set(newDict[key].get).intersection(set(tok))) > 0:
                    traduzione.append(key)
                    for j in newDict[key].get:
                        if PosTagger.tag_text(j)[0] in tok:
                            tok.remove(PosTagger.tag_text(j)[0])

            print(tok)
            if len(tok) != 0:
                for token in tok:
                    flag = False
                    for image in image_list:
                        keyword_tag_list = list(filter(lambda x: x.tag_type == 'KEYWORD' and (
                            image.id in dizionario.keys()), image.image_tag))
                        for keyword_tag in keyword_tag_list:
                            if ps.stem(keyword_tag.tag.tag_value) == ps.stem(token):
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
                                synonym_tag_dict[image.id] = [
                                    item.tag_id for item in synonym_tag_list]
                                general_tag_dict[image.id] = [
                                    item.tag_id for item in general_tag_list]
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
                        occorrenza = dizionario.get['occorrenza']
                        flag = True
                        dizionario_traduzione[image_id] = {
                            'frequenza': 1, 'occorrenza': occorrenza}
                        dizionario[image.id] = {
                            'frequenza': 1, 'occorrenza': occorrenza}
                        synonym_tag_list = list(
                            filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                        general_tag_list = list(
                            filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                        synonym_tag_dict[image.id] = [
                            item.tag_id for item in synonym_tag_list]
                        general_tag_dict[image.id] = [
                            item.tag_id for item in general_tag_list]
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
                            occorrenza = dizionario.get['occorrenza']
                            dizionario_traduzione[image_id] = {
                                'frequenza': 1, 'occorrenza': occorrenza}
                            synonym_tag_list = list(
                                filter(lambda x: x.tag_type == 'SYNONYM', image.image_tag))
                            general_tag_list = list(
                                filter(lambda x: x.tag_type == 'GENERAL', image.image_tag))
                            synonym_tag_dict[image.id] = [
                                item.tag_id for item in synonym_tag_list]
                            general_tag_dict[image.id] = [
                                item.tag_id for item in general_tag_list]
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

            print('stem_list')
            print(stem_occ_list)
            for i in pos_tag_m_list:
                print(ps.stem(i.lemma))

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

        return {
            "caa_images": [caa_image.json() for caa_image in caa_images],
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
