#!/usr/bin/env python
# coding: utf-8

# In[1]:


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
import sys

elmo = ElmoEmbedder()


# In[36]:


def read_metadata():
    table = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-documents')
    s3_client = boto3.client('s3')
    
    response = table.scan()
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    metadata = pd.DataFrame(data)
    metadata["date"] = [datetime.strptime(d, '%Y-%m-%d') for d in metadata["date"]]
    metadata['local_path_pkl'] = metadata['local_path_txt'].apply(lambda x: "vectors"+x[4:-3]+"pkl")
    return metadata
metadata = read_metadata()
print(metadata["local_path_pkl"][0])


# In[41]:


# s3.Object('autolocal-documents', 'cities.csv').load()


# In[15]:


def read_local(s3_path):
    return pickle.load(open(os.path.join("../data/pkls/", os.path.basename(s3_path)), 'rb'))


# In[18]:


def get_local_pkl(s3_path):
    return os.path.join("../data/pkls/", os.path.basename(s3_path))


# In[38]:


metadata_subset = metadata[metadata["date"] >= datetime.strptime('2019-09-01', '%Y-%m-%d')]
metadata_subset = metadata_subset[metadata_subset["city"] == "San Jose"]
print(metadata_subset.shape)


# In[27]:


s3 = boto3.resource('s3')
s3.meta.client.download_file('autolocal-documents', 'cities.csv', 'tmp.txt')


# In[ ]:


# s3_client.upload_file('autolocal-documents', , )


# In[ ]:


print("processing docs")
for i, row in tqdm(metadata_subset.iterrows()):
    txt_filename = row['local_path_txt']
    pkl_filename = row['local_path_pkl']
    try:
        s3.Object('autolocal-documents', pkl_filename).load()
        print("already uploaded: {}".format(pkl_filename))
    except:
        try:
            read_local(pkl_filename)
            print("already processed: {}".format(pkl_filename))
        except:
            print("processing doc")
            doc_string = read_doc(txt_filename)
            if doc_string:
                sentences = sentence_spit(doc_string)
                vectors = []
                for sentence in sentences:
                    sentence_tokens = tokenize(sentence)
                    sentence_vectors = elmo.embed_sentence(sentence_tokens)
                    vectors.append(sentence_vectors)
                write({"sentences": sentences, "vectors": vectors}, pkl_filename)
        print("uploading doc")
        s3 = boto3.resource('s3')
        s3.meta.client.upload_file(get_local_pkl(pkl_filename), 'autolocal-documents', pkl_filename)


# In[ ]:




