# tools for natural language processing

import re
from allennlp.commands.elmo import ElmoEmbedder

class Vectorizer(object):

    def __init__(self):
        self.elmo = ElmoEmbedder()

    def sentence_split(self, s):
        sentences = re.split('[.\n!?"\f]', s)
        return [s for s in sentences if len(s.strip())>0]

    def tokenize(self, s):
        tokens = re.findall(r'\w+', s)
        return tokens

    def vectorize(self, string):

        print("vectorizing doc")
        sentences = self.sentence_split(string)
        vectors = []
        for sentence in sentences:
            sentence_tokens = self.tokenize(sentence)
            sentence_vectors = self.elmo.embed_sentence(sentence_tokens)
            vectors.append(sentence_vectors)
        vectors_data = {"sentences": sentences, "vectors": vectors}

        return vectors_data

class Tokenizer(object):
    """
    A simple, fast, regular expression based tokenizer.
    """

    def __init__(
        self,
        regex=r'\w+', #r'\w+|\$[\d\.]+|\S+'
        ):
        self.tokenizer = re.compile(regex)
        pass

    def tokenize(
        self,
        string
        ):
        return self.tokenizer.findall(string)



# parsers to pull out specific topics of interest
def housing_parser():
    keywords = [
        'residential',
        'housing',
        'incentive program',
        'subdivision'
        'Deferred Improvement Agreement'
        ]

def zoning_parser():
    # pull out parcel numbers NNN-NNN-NNN
    keywords = [
        'zoning',
        'rezoning',
        'parcel',
        'parcels',
        'APN'
    ]


def staff_parser():
    keywords = [
        'vacancy',
        'vacancies',
        'appointment',
        'candidate',
        'candidates'
    ]

def resolution_parser():
     # pull out resolutions 2019-R-026
     keywords = 'resolution'