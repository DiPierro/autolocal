#!/usr/bin/env python
# coding: utf-8

import re

from allennlp.commands.elmo import ElmoEmbedder
import boto3
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from autolocal.parsers.nlp import Tokenizer
import pickle
import numpy as np
from  tqdm import tqdm
import os

elmo = ElmoEmbedder()
# dims: (LAYERS(3), TOKENS(6), DIMENSIONS(1024))
"""
https://towardsdatascience.com/elmo-helps-to-further-improve-your-word-embeddings-c6ed2c9df95f
In the ELMo paper, there are 3 layers of word embedding,
layer zero is the character-based context independent layer,
followed by two Bi-LSTM layers. The authors have empirically
shown that the word vectors generated from the first Bi-LSTM
layer can better capture the syntax, and the second layer can
capture the semantics better.
"""


# In[119]:


s3 = boto3.resource('s3')
autolocal_docs_bucket = s3.Bucket('autolocal-documents')
def read_doc(s3_path):
    try:
        return autolocal_docs_bucket.Object(s3_path).get()['Body'].read().decode("ascii", "ignore")
    except:
        return None


# In[190]:


def read_metadata():
    table = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-documents')
    s3_client = boto3.client('s3')
    metadata = pd.DataFrame(table.scan()["Items"])
    metadata["date"] = [datetime.strptime(d, '%Y-%m-%d') for d in metadata["date"]]
    metadata['local_path_pkl'] = metadata['local_path_txt'].apply(lambda x: x[:-3]+"pkl")
    return metadata
metadata = read_metadata()


# In[222]:


def read(s3_path):
    return np.load(os.path.join("pkls/", os.path.basename(s3_path)))

def write(array, s3_path):
    pickle.dump(array, open(os.path.join("pkls/", os.path.basename(s3_path)), 'wb'))


# In[168]:


# simple_tokenizer = Tokenizer("")

def sentence_spit(s):
    sentences = re.split('[.\n!?"\f]', s)
    return [s for s in sentences if len(s)>0]

def tokenize(s):
    tokens = re.findall(r'\w+', s)
    return tokens


# In[169]:


starting_dates_for_filtering = {
    'upcoming_only': datetime.now() + timedelta(days=0.5),
    'upcoming': datetime.now() + timedelta(days=0.5),
    'this_week': datetime.now() - timedelta(weeks=1),
    'this_year': datetime.now() - timedelta(days=365),
    'this_month': datetime.now() - timedelta(weeks=5),
    'past_six_months':datetime.now() - timedelta(days=183),
    'past': None,
    'all': None
}


# In[170]:


metadata_past_six_months = metadata[metadata["date"] >= starting_dates_for_filtering['past_six_months']]


# In[223]:


count = 0
for i, row in tqdm(metadata_past_six_months.iterrows()):
    if count >= 0:
        txt_filename = row['local_path_txt']
        pkl_filename = row['local_path_pkl']
        doc_string = read_doc(txt_filename)
        if doc_string:
            sentences = sentence_spit(doc_string)
            vectors = []
            for sentence in sentences:
                sentence_tokens = tokenize(sentence)
                sentence_vectors = elmo.embed_sentence(sentence_tokens)
                vectors.append(sentence_vectors)
            write({"sentences": sentences, "vectors": vectors}, pkl_filename)
    print(count)
    count += 1


# In[172]:


# class DocTextReader():
#     def __init__(self, log_every=100):
#         self.log_every = log_every
#         s3 = boto3.resource('s3', region_name='us-west-1')
#         self.bucket = s3.Bucket('autolocal-documents')

#     def read_docs(self, s3_paths):
#         # read all documents that we know about
#         # tokenize each document
#         # return list of documents

#         documents = {}
#         n_docs_total = len(s3_paths)

#         i = 0
#         n_docs_read = 0
#         for s3_path in s3_paths:
#             try:
#                 doc_string = read_doc(s3_path)
#                 doc_tokens = simple_tokenizer.tokenize(doc_string)
#                 filename_npy = s3_path[:-3] + "npy"
#                 documents[s3_path] = {
#                     "original_text": doc_string,
#                     "tokens": doc_tokens,
#                     "vectors": read_npy(filename_npy)
#                 }
#             except Exception as e:
#                 if i < 10:
#                     print("Key not found: {}".format(s3_path))
#                 elif i == 10:
#                     print("More than 10 keys not found")
#                     print(e)
#                     break
#                 i+=1
#             if n_docs_read % self.log_every == 0:
#                 print("{} of {} documents read".format(n_docs_read, n_docs_total))
#             n_docs_read+=1

#         return documents


# # In[173]:


# def read_queries():
#     table = boto3.resource('dynamodb', region_name='us-west-2').Table('autoLocalNews')
#     queries = table.scan()["Items"]
#     return queries


# # In[174]:


# def find_relevant_filenames(queries, metadata): 
    
#     # filter metadata to only those files that match the query municipality and time_window
#     municipalities_by_time_window = {}
#     for query in queries:
#         time_window = query['Time Window']
#         if time_window in municipalities_by_time_window:
#             municipalities_by_time_window[time_window].update(query['Municipalities'])
#         else:
#             municipalities_by_time_window[time_window] = set(query['Municipalities'])
            
#     relevant_filenames = set()
#     for time_window in municipalities_by_time_window:
#         starting_date = starting_dates_for_filtering[time_window]
#         potential_documents = metadata
#         if starting_date:
#             potential_documents = potential_documents[potential_documents["date"] >= starting_date]
#         cities = municipalities_by_time_window[time_window]
#         potential_documents = potential_documents[[(c in cities) for c in potential_documents["city"]]]
#         relevant_filenames.update(potential_documents['local_path_txt'])
#     return relevant_filenames


# # In[225]:


# print("reading queries")
# queries = read_queries()
# queries = [q for q in queries if ('Status' in q and q['Status'] == 'just_submitted')]
# print(queries)
# print("reading metadata")
# metadata = read_metadata()
# print("setting up reader")
# doc_text_reader = DocTextReader(log_every=100)
# # used cached idf and only read relevant documents
# print("finding relevant filenames")
# relevant_filenames = find_relevant_filenames(queries, metadata)
# # (not actually *all*, but all the ones we care about for queries)
# print("reading relevant documents")
# all_docs = doc_text_reader.read_docs(relevant_filenames)


# # In[ ]:





# # In[ ]:





# # In[ ]:




