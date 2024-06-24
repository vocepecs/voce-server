from flask_restful import Resource, request
from nltk.corpus import wordnet as wn
from transformers.modeling_bert import BertModel, BertPreTrainedModel, BertConfig
from transformers import AutoTokenizer
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
import torch
from torch.nn.functional import softmax
from collections import namedtuple
import torch.multiprocessing as mp
from googletrans import Translator

ENABLED_STOPWORDS = [
    'still',
    'up',
    'take',
    'more',
    'put',
    'how',
    'are',
    'or',
    'what',
    'go',
    'please',
    'before',
    'after',
    'do',
    'over',
    'not',
    'again',
]

TAG_MAP = {
    'J': wn.ADJ,
    'V': wn.VERB,
    'N': wn.NOUN,
    'R': wn.ADV
}


class BertWSD(BertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)

        self.bert = BertModel(config).cuda()
        self.dropout = torch.nn.Dropout(config.hidden_dropout_prob)

        self.ranking_linear = torch.nn.Linear(config.hidden_size, 1)

        self.init_weights()


class WSDModel():

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.max_seq_length = 128
        self.gloss_selection_record = namedtuple("GlossSelectionRecord", [
                                            "guid", "sentence", "sense_keys", "glosses", "targets"])
        self.bert_input = namedtuple(
            "BertInput", ["input_ids", "input_mask", "segment_ids", "label_id"])

    def get_amb_words(self, sentence):
        nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
        doc = nlp(sentence)
        amb_words = []

        # Stop words filtered
        stop_words = list(
            filter(lambda x: x not in ENABLED_STOPWORDS, STOP_WORDS))

        # Remove Stopwords token
        tokens = list(filter(lambda x: str(x) not in stop_words, doc))

        for token in tokens:
            if token.tag_ in ('VB', 'VBG', 'VBD', 'VBN', 'VBP', 'VBZ'):
                t = (token.lemma_, token.tag_)
                amb_words.append(t)
            else:
                t = (str(token), token.tag_)
                amb_words.append(t)

        return amb_words

    def get_word_info(self, lemma, pos, info_type):
        results = dict()

        tag = pos[0].upper()
        wn_pos = TAG_MAP.get(tag)
        morphemes = wn._morphy(
            lemma, pos=wn_pos) if pos is not None and wn_pos is not None else []

        for synset in wn.synsets(lemma, pos=wn_pos):
            sense_key = None

            for l in synset.lemmas():
                if l.name().lower() == lemma.lower():
                    sense_key = l.key()
                    break
                # non dovrebbe mai entrarci se pos è None, potrebbe richiamare wn.morphy(lemma)
                elif l.name().lower() in morphemes:
                    sense_key = l.key()
            # assert sense_key is not None
            results[sense_key] = synset.examples(
            ) if info_type == 'examples' else synset.definition()

        return results

    def truncate_seq_pair(self, tokens_a, tokens_b, max_length):
        """Truncates a sequence pair in place to the maximum length."""

        # This is a simple heuristic which will always truncate the longer sequence
        # one token at a time. This makes more sense than truncating an equal percent
        # of tokens from each, since if one sequence is very short then each token
        # that's truncated likely contains more information than a longer sequence.
        while True:
            total_length = len(tokens_a) + len(tokens_b)
            if total_length <= max_length:
                break
            if len(tokens_a) > len(tokens_b):
                tokens_a.pop()
            else:
                tokens_b.pop()

    def create_features_from_records(self, records, max_seq_length, tokenizer, cls_token_at_end=False, pad_on_left=False,
                                     cls_token='[CLS]', sep_token='[SEP]', pad_token=0,
                                     sequence_a_segment_id=0, sequence_b_segment_id=1,
                                     cls_token_segment_id=1, pad_token_segment_id=0,
                                     mask_padding_with_zero=True, disable_progress_bar=False):
        """ Convert records to list of features. Each feature is a list of sub-features where the first element is
            always the feature created from context-gloss pair while the rest of the elements are features created from
            context-example pairs (if available)

            `cls_token_at_end` define the location of the CLS token:
                - False (Default, BERT/XLM pattern): [CLS] + A + [SEP] + B + [SEP]
                - True (XLNet/GPT pattern): A + [SEP] + B + [SEP] + [CLS]
            `cls_token_segment_id` define the segment id associated to the CLS token (0 for BERT, 2 for XLNet)
        """
        features = []
        for record in records:
            tokens_a = tokenizer.tokenize(record.sentence)

            sequences = [(gloss, 1 if i in record.targets else 0)
                         for i, gloss in enumerate(record.glosses)]

            pairs = []
            for seq, label in sequences:
                tokens_b = tokenizer.tokenize(seq)

                # Modifies `tokens_a` and `tokens_b` in place so that the total
                # length is less than the specified length.
                # Account for [CLS], [SEP], [SEP] with "- 3"
                self.truncate_seq_pair(tokens_a, tokens_b, max_seq_length - 3)

                # The convention in BERT is:
                # (a) For sequence pairs:
                #  tokens:   [CLS] is this jack ##son ##ville ? [SEP] no it is not . [SEP]
                #  type_ids:   0   0  0    0    0     0       0   0   1  1  1  1   1   1
                #
                # Where "type_ids" are used to indicate whether this is the first
                # sequence or the second sequence. The embedding vectors for `type=0` and
                # `type=1` were learned during pre-training and are added to the wordpiece
                # embedding vector (and position vector). This is not *strictly* necessary
                # since the [SEP] token unambiguously separates the sequences, but it makes
                # it easier for the model to learn the concept of sequences.
                #
                # For classification tasks, the first vector (corresponding to [CLS]) is
                # used as as the "sentence vector". Note that this only makes sense because
                # the entire model is fine-tuned.
                tokens = tokens_a + [sep_token]
                segment_ids = [sequence_a_segment_id] * len(tokens)

                tokens += tokens_b + [sep_token]
                segment_ids += [sequence_b_segment_id] * (len(tokens_b) + 1)

                if cls_token_at_end:
                    tokens = tokens + [cls_token]
                    segment_ids = segment_ids + [cls_token_segment_id]
                else:
                    tokens = [cls_token] + tokens
                    segment_ids = [cls_token_segment_id] + segment_ids

                input_ids = tokenizer.convert_tokens_to_ids(tokens)

                # The mask has 1 for real tokens and 0 for padding tokens. Only real
                # tokens are attended to.
                input_mask = [
                    1 if mask_padding_with_zero else 0] * len(input_ids)

                # Zero-pad up to the sequence length.
                padding_length = max_seq_length - len(input_ids)
                if pad_on_left:
                    input_ids = ([pad_token] * padding_length) + input_ids
                    input_mask = ([0 if mask_padding_with_zero else 1]
                                  * padding_length) + input_mask
                    segment_ids = ([pad_token_segment_id] *
                                   padding_length) + segment_ids
                else:
                    input_ids = input_ids + ([pad_token] * padding_length)
                    input_mask = input_mask + \
                        ([0 if mask_padding_with_zero else 1] * padding_length)
                    segment_ids = segment_ids + \
                        ([pad_token_segment_id] * padding_length)

                assert len(input_ids) == max_seq_length
                assert len(input_mask) == max_seq_length
                assert len(segment_ids) == max_seq_length

                pairs.append(
                    self.bert_input(input_ids=input_ids, input_mask=input_mask,
                                    segment_ids=segment_ids, label_id=label)
                )

            features.append(pairs)

        return features

    def get_predictions(self, model, tokenizer, sentence, amb_word, pos):
        sense_keys = []
        definitions = []

        word_info = self.get_word_info(
            amb_word, pos, info_type='gloss')
        

        print(f"Word Info Items {word_info.items()}")
        if len(word_info.items()) > 0:
            sense_keys, definitions = zip(*word_info.items())

            record = self.gloss_selection_record(
                "test", sentence, sense_keys, definitions, [-1])
            features = self.create_features_from_records([record], self.max_seq_length, tokenizer,
                                                        cls_token=tokenizer.cls_token,
                                                        sep_token=tokenizer.sep_token,
                                                        cls_token_segment_id=1,
                                                        pad_token_segment_id=0,
                                                        disable_progress_bar=True)[0]

            with torch.no_grad():

                logits = torch.zeros(
                    len(definitions), dtype=torch.double).to(self.device)

                # print(f"features len: {len(features)}")
                # print(f"features: {features}")

                # tqdm(list(enumerate(features)), desc="Progress"):
                for i, bert_input in list(enumerate(features)):
                    # print(f"input_ids: {bert_input.input_ids}")
                    # print(f"input_mask: {bert_input.input_mask}")
                    # print(f"segment_ids: {bert_input.segment_ids}")

                    logits[i] = model.ranking_linear(
                        model.bert(
                            input_ids=torch.tensor(
                                bert_input.input_ids, dtype=torch.long).unsqueeze(0).to(self.device),
                            attention_mask=torch.tensor(
                                bert_input.input_mask, dtype=torch.long).unsqueeze(0).to(self.device),
                            token_type_ids=torch.tensor(
                                bert_input.segment_ids, dtype=torch.long).unsqueeze(0).to(self.device)
                        )[1]
                    )
                scores = softmax(logits, dim=0)

            # print('Fine with')
            # print(datetime.now())

            return sorted(zip(sense_keys, definitions, scores), key=lambda x: x[-1], reverse=True)
        
        else: 
            return []

    def init_model(self):
        model = BertWSD.from_pretrained(
            "/var/www/html/vocecaa-rest/bert_large-augmented-batch_size=128-lr=2e-5-max_gloss=6")
        tokenizer = AutoTokenizer.from_pretrained(
            "/var/www/html/vocecaa-rest/bert_large-augmented-batch_size=128-lr=2e-5-max_gloss=6")

        print(f"device: {self.device}")
        model.to(self.device)
        model.eval()
        return [model, tokenizer]

    def wsd_algorithm(self, phrase):
        mp.set_start_method('spawn', force=True)
        # print(torch.cuda.memory_summary(device=None, abbreviated=False))
        # print(f"Memoria CUDA allocata: {torch.cuda.memory_allocated()}")
        # print(f"Memoria CUDA allocata: {torch.cuda.memory_reserved()}")
        # print(f"Memoria CUDA allocata: {torch.cuda.memory_cached()}")
        torch.cuda.empty_cache()
        translator = Translator()
        sentence = (translator.translate(
            phrase, src="it", dest="en")).text.lower()
        

        print(f"Frase tradotta: {sentence}")
        
        amb_word_list = self.get_amb_words(sentence)
        model, tokenizer = self.init_model()
        
        prediction_list = []
        for word in amb_word_list:
            predictions = self.get_predictions(
                model,
                tokenizer,
                sentence,
                word[0],
                word[1],
            )

            print(f"predictions dtype: {type(predictions)}")
            print(f"predictions: {predictions}")

            prediction_list.append(predictions)
        
        return prediction_list
