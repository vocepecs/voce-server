from codecs import getencoder
import nltk
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer, SnowballStemmer
import re
import subprocess
import json
import requests
from datetime import datetime

from utils.pos_tagging import PosTagger


from models.grammatical_type import GrammaticalTypeModel
from models.comunicative_session.tense import TenseModel
from models.comunicative_session.verbal_form import VerbalFormModel
from models.comunicative_session.pos_tagging import PosTaggingModel


class NlpPreprocess:

    def tokenize(self, phrase):
        p = requests.get(url='http://localhost:8012/tint', params={
            'text': phrase,
            'format': 'json'
        })

        token_dict = {}
        # list_id_token_composti=[]
        tokens = p.json()["sentences"][0]["tokens"]
        # list_parole_composte=p.json().get('cat_tasks')
        # for i in list_parole_composte:
        #     if i.get('taskName')=='POLIREMATICHE':
        #         token_composti.append(i.get('texts'))

        # print(token_composti)
        for token in tokens:

            if token["ud_pos"] != 'AUX':
                lemma = token["lemma"]
                grammatical_type = token["pos"]
                token_features = token.get("features")
                tense = ''
                verb_form = ''
                gender = ''
                number = ''

                if grammatical_type == 'V':

                    verb_form = token_features.get("VerbForm")
                    tense = token_features.get("Tense")
                    number = token_features.get("Number")
                else:
                    number = token_features.get("Number")
                    gender = token_features.get("Gender")

                token_dict[token.get("word")] = {
                    'lemma': lemma,
                    'grammatical_type': grammatical_type,
                    'gender': gender,
                    'number': number,
                    'verbform': verb_form,
                    'tense': tense,
                }
        return token_dict

    @classmethod
    def tokenizeRegex(cls, phrase):

        pattern = r'''\w+|\?'''
        custom_tokenizer = RegexpTokenizer(pattern)
        output = custom_tokenizer.tokenize(phrase)

        return output

    def elimination_stop_word_general(self, keyword):
        it_stop_words = nltk.corpus.stopwords.words('italian')
        it_stop_words.remove("o")
        it_stop_words.remove("non")
        it_stop_words.append('il')

        new_list = list(
            filter(lambda x: x not in it_stop_words, keyword.split()))
        return new_list

    def elimination_stop_word(self, tokenized_phrase):
        it_stop_words = nltk.corpus.stopwords.words('italian')
        # print('STOP WORDS')
        # print(it_stop_words)
        tokenized_phrase_2 = {}
        tokenized_phrase_2.update(tokenized_phrase)
        it_stop_words.remove("o")
        it_stop_words.remove("non")
        it_stop_words.append('il')
        word_tokenized_no_sw = []
        for key, value in tokenized_phrase_2.items():
            if value.get('lemma') in it_stop_words:
                del tokenized_phrase[key]
                # word_tokenized_no_sw.append(value.get('lemma'))
        return tokenized_phrase

    def get_token_lemmas(self, phrase):

        # Tokenizzazione della frase
        phrase_tokenized_dict = self.tokenize(phrase=phrase)

        # Eliminazione dell stop word
        phrase_wsw = self.elimination_stop_word(phrase_tokenized_dict)
        
        # Lista per memorizzare i risultati del pos-tagging
        pos_tag_m_list = []

        for i in phrase_wsw.keys():
            tipo_grammaticale = phrase_wsw[i].get("grammatical_type")
            grammatical_type_id = GrammaticalTypeModel.find_by_tint_tag(
                tipo_grammaticale).id
            
            tense_id = None
            verbal_form_id = None

            if tipo_grammaticale == 'V':                
                if phrase_wsw[i].get("verbform")[0] != "Inf":
                    tense = TenseModel.find_by_value(str(phrase_wsw[i].get("tense")[0]).upper())
                    tense_id = tense.id

                verbal_form = VerbalFormModel.find_by_value(
                    phrase_wsw[i].get("verbform")[0])
            
                verbal_form_id = verbal_form.id if verbal_form else None
            
            # Ricerca del pos-tag nel database
            pos_tag_from_db = PosTaggingModel.find_by_composite_id(
                i, grammatical_type_id)
            if pos_tag_from_db:
                pos_tag_m_list.append(pos_tag_from_db)
            else:
                # Creazione di un nuovo pos-tag se non esiste nel database
                pos_tag_m = PosTaggingModel(
                    i,
                    grammatical_type_id,
                    phrase_wsw[i].get("lemma"),
                    tense_id,
                    verbal_form_id,
                    phrase_wsw[i].get("gender"),
                    phrase_wsw[i].get("number"),
                )
                pos_tag_m.save_to_db()
                pos_tag_m_list.append(pos_tag_m)

        # Estrazione dei lemmi dai risultati del pos-tagging
        token_lemmas = [x.lemma for x in pos_tag_m_list]

        return [phrase_wsw, token_lemmas, pos_tag_m_list]
