import os
import urllib

from copy import deepcopy

import pandas as pd
import numpy as np

from autolocal import DocumentManager

legistar_document_dir = '../data/scraping/2019-11-19_scraped_tables'

def extract_doc_list(legistar_table_fname):
    city_name = documents._parse_city_dir(legistar_table_fname[:-4])
    doc_list_path = os.path.join(doc_list_dir, '{}.csv'.format(legistar_table_fname[:-4]))
    print('City: {}'.format(city_name))
    
    # read csv
    parse_dates = 'Meeting Date Text'
    df = pd.read_csv(os.path.join(legistar_document_dir, legistar_table_fname), parse_dates=[parse_dates])
    print(' ...found {} meeting records'.format(len(df)))
#     print('Columns:')
#     print(df.columns)
    
    doc_list = []
    for i, row in df.iterrows():
        data = {
            'city': city_name,
            'date': row['Meeting Date Text'],
            'committee': row['Name Text'],
            'doc_format': 'pdf',
        }        
        url_col_pairs = [
            ('Agenda', 'Agenda URL'),
            ('Minutes', 'Minutes URL'),
            ('Minutes', 'Official Minutes URL')
        ]
        for doc_type, url_col in url_col_pairs:
            try:
                url = row[url_col]
                if isinstance(url, str):
                    row_data = deepcopy(data)
                    row_data['url'] = url
                    row_data['doc_type'] = doc_type
                    doc_list.append(row_data)
            except:
                pass
                
    print(' ...found {} documents'.format(len(doc_list)))
    print('')

    # save new csv    
    pd.DataFrame(doc_list).to_csv(doc_list_path)   
    
    return doc_list 

# make document list
doc_list_dir = legistar_document_dir + '_doc_lists'
if not os.path.exists(doc_list_dir):
    os.mkdir(doc_list_dir)

# instantiate document manager
documents = DocumentManager()

# iterate over cities
legistar_table_fnames = os.listdir(legistar_document_dir)
num_docs = 0
for legistar_table_fname in legistar_table_fnames:
    doc_list = extract_doc_list(legistar_table_fname)
    num_docs = num_docs + len(doc_list)
    
print('Found {} documents in total'.format(num_docs))

doc_list_paths = [os.path.join(doc_list_dir, f) for f in os.listdir(doc_list_dir)]

for p in doc_list_paths:
    documents.add_docs_from_csv(p)
