from models.comunicative_session.pos_tagging import PosTaggingModel
from models.tag import TagModel
from models.tag import ImageTagModel
from models.image import ImageModel
from utils.nlp_preprocess import NlpPreprocess
from nltk.stem import SnowballStemmer
from models.grammatical_type import GrammaticalTypeModel
from utils.association_tables import ass_image_grammatical_type
from datetime import datetime


### TODO Classe finale algoritmo di traduzione 
### TODO [REFACTORING DA ULTIMARE]

class VoceTranslate():
    
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, text):
        self.nlp_preprocess = NlpPreprocess()
        self.stemmer = SnowballStemmer('italian')
        nlp_preprocess_result = self.npl_preprocess.get_token_lemmas(phrase=text)
        self.token_dict = nlp_preprocess_result[0]
        self.token_lemmas = nlp_preprocess_result[1]
        self.pos_tag_m_list = nlp_preprocess_result[2]

        self.main_token_list = []
        for token in self.token_dict.items():
            if(token[1]['grammatical_type'] == 'V'):
                self.main_token_list.append(token[1]['lemma'])
            else:
                self.main_token_list.append(token[0])
        

        # ? Aggiungere creazione ComunicativeSession
    

    def get_out_of_context_image_list(self, token):
        search = "%{}%".format(token)

        return ImageModel.query.join(ImageTagModel).join(TagModel).filter(
            ImageTagModel.tag_type == 'KEYWORD',
            TagModel.tag_value.ilike(search)
        ).all()

    def social_story_translate(self):
        
        dizionario = {}
        stem_token_list = []
        for token in self.main_token_list:
            stem_token_list.append(self.stemmer.stem(token))

        for token in self.main_token_list_token_list:
            out_context_image_list = self.get_out_of_context_image_list(token=token)
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

        
    
        