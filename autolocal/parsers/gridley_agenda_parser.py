import os, re
import numpy as np
import pandas as pd
import dateutil.parser as dparser
from tqdm import tqdm

# Gridley-specific header info
all_section_headers = [
    'CALL TO ORDER',
    'ROLL CALL',
    'PLEDGE OF ALLEGIANCE',
    'INVOCATION',
    'PROCLAMATIONS',
    'COMMUNITY PARTICIPATION FORUM',
    'CONSENT AGENDA',    
    'ANNOUNCEMENT OF NEW EMPLOYEES AND PROMOTIONS',
    'NEW AND PROMOTED EMPLOYEES',
    'ANNOUNCEMENT OF NEW AND PROMOTED EMPLOYEES',    
    'INTRODUCTION OF NEW OR PROMOTED EMPLOYEES',
    'NEW AND PROMOTED EMPLOYEES',
    'PUBLIC HEARING',
    'ITEMS FOR COUNCIL CONSIDERATION',
    'CITY STAFF AND COUNCIL COMMITTEE REPORTS',
    'POTENTIAL FUTURE CITY COUNCIL ITEMS',
    'CLOSED SESSION',
    'ADJOURNMENT',
    'NOTE 1',
    'NOTE 2'
]
mtg_vars = [
    'MTG_TYPE',
    'MTG_DATETIME',
    'MTG_LOCATION',
    'DOC_NUM_PAGES',
]
footer_start = 'GRIDLEY CITY COUNCIL AGENDA'
head_suffixes = [
    r'\s+[\x2d\u2013\u2014]',
    r':',
    r'',
]
strip_patterns = [
    r'\n',
    r'[0-9]\.',
    r'Brief updates from City staff and brief reports on conferences, seminars, and meetings attended by the Mayor and City Council members, if any.',
    r'\(Appearing on the Agenda within 30-90 days\):',
]
nan_values = [
    'None',
    ''
]

# get all Gridley agendas
def get_agenda_paths(data_dir, required_substrings):
    matches_substrings = lambda s: all([ss in s for ss in required_substrings])
    doc_list = [s for s in os.listdir(data_dir) if matches_substrings(s)]
    doc_paths = [os.path.join(data_dir, doc) for doc in doc_list]
    return doc_paths


def parse_txt(doc):

    # remove inserted characters
    doc = re.sub(r'\(cid:[0-9]\)','', doc)
    
    # the number of pages is the last character on the first page
    page_break_re = re.compile('\f')
    page_breaks = [m.start() for m in page_break_re.finditer(doc)]
    page_count_re = re.compile(r'Page\s[\d]\sof\s[\d]')
    n0, n1 = zip(*[[int(d) for d in s[5:].split(' of ')] for s in page_count_re.findall(doc)])
    num_pages = n0[np.where(np.array(n0)==np.array(n1))[0][0]]
    
    # trim extraneous pages and remove page footers
    agenda = doc[:page_breaks[num_pages-1]+1]
#     agenda = re.sub(footer_start + '[^()]*\x0c', '', agenda)
#     agenda = re.sub('Page\s[\d]\sof\s[\d][\s\n\t]*\x0c', '', agenda)    
    agenda = re.sub(footer_start +'(.*\n?)', '', agenda)
    agenda = re.sub(r'Page\s[\d]\sof\s[\d]', '', agenda)
    agenda = re.sub('\f', '', agenda)
    
    # get section breaks in document
    all_section_starts = [agenda.find(h) for h in all_section_headers]
    section_heads, section_starts = zip(*[(k,t) for k, t in zip(all_section_headers, all_section_starts) if t>0])
    
    # sort sections
    sort_idx = np.argsort(section_starts)
    headers = list(np.array(section_heads)[sort_idx])
    breaks = list(np.array(section_starts)[sort_idx]) + [len(agenda)]    
    
    # get section ranges
    section_ranges = [('HEADER', 0, breaks[0])]
    section_ranges.extend([(headers[i], breaks[i], breaks[i+1]) for i in range(len(headers))])
    
    # store section

    sections = {}
    for head, start, end in section_ranges:
        section = agenda[start:end]
        if head=='HEADER':
            header = section.split('\n')
            header = [h for h in header if h.strip()]
        else:
            for s in head_suffixes:                
                section = re.sub(head+s, '', section)
            for s in strip_patterns:                
                section = re.sub(s, '', section)
            section = section.strip()
            sections[head] = section
        
        for v in mtg_vars:
            if v=='MTG_TYPE':
                for s in ['regular', 'special', 'amended']:
                    if s in header[0].lower():
                        sections[v] = s 
            elif v=='MTG_DATETIME':
                sections[v] = dparser.parse(header[1])
            elif v=='MTG_LOCATION':            
                sections[v] = header[2]
            elif v=='DOC_NUM_PAGES':
                sections[v] = num_pages
        sections['HEADER'] = header
        
    return sections

def parse_docs(doc_paths, save_path):
    segmented_docs = []
    for path in tqdm(doc_paths):
        with open(path, 'r') as f:
            doc = f.read()
        sections = parse_txt(doc)
        segmented_docs.append(sections)

    data = pd.DataFrame(segmented_docs, columns=mtg_vars + all_section_headers)
    # for s in nan_values:
    #     data[data==s] = np.nan
    data = data.sort_values('MTG_DATETIME', ascending=False).reset_index(drop=False, )

    data.to_csv(save_path)
    return data

if __name__=='__main__':
    data_dir =  '../data/docs/gridley/'
    save_path = '../data/misc/gridley_agendas.csv'
    required_substrings = ['Gridley', 'Agenda', 'City-Council', '.txt']
    doc_paths = get_agenda_paths(data_dir, required_substrings)
    doc_df = parse_docs(doc_paths, save_path)


