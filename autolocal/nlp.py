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
        string
        ):
        return self.tokenizer.findall(string)