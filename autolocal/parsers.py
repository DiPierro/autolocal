
class Parser(object):

    def __init__(self):
        pass

    def parse(self, doc):
        pass


class GridleyAgendaParser(Parser):

    def __init__(self):            
        self.section_headers = [
            'CALL TO ORDER',
            'ROLL CALL',
            'PLEDGE OF ALLEGIANCE',
            'INVOCATION',
            'PROCLAMATIONS',
            'COMMUNITY PARTICIPATION FORUM',
            'CONSENT AGENDA',
            'PUBLIC HEARING',
            'ITEMS FOR COUNCIL CONSIDERATION',
            'CITY STAFF AND COUNCIL COMMITTEE REPORTS',
            'POTENTIAL FUTURE CITY COUNCIL ITEMS',
            'CLOSED SESSION',
            'ADJOURNMENT',
            'NOTE',
        ]


    def parse(self, doc):
        # keep first three lines as header


FOOTER = 'GRIDLEY CITY COUNCIL AGENDA'

