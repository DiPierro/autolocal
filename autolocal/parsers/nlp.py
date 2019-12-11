# tools for natural language processing

import re

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