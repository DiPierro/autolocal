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