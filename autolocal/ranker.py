# Import statements

import pandas as pd
import numpy as np
from gensim.models.word2vec import Word2Vec
import gensim.downloader as gensim
from sklearn.metrics.pairwise import cosine_similarity
import json

from datetime import *
import os
from autolocal.parsers.nlp import Tokenizer
from gensim.parsing.preprocessing import *

from autolocal.databases import S3DocumentManager
import boto3
from decimal import *
from  tqdm import tqdm

import re
import editdistance

# set up word vectors
# (this takes a loooong time)
def setup_word_vectors():
  print("loading language model")
  # load language model (this takes a few minutes)
  model = gensim.load('word2vec-google-news-300')
  print("model loaded")

  vectors = model.wv
  del model
  vectors.init_sims(True) # normalize the vectors (!), so we can use the dot product as similarity measure

  print('embeddings loaded ')
  print('loading docs ... ')
  return vectors

def read_metadata():
    table = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-documents')
    s3_client = boto3.client('s3')
    metadata = pd.DataFrame(table.scan()["Items"])
    metadata["date"] = [datetime.strptime(d, '%Y-%m-%d') for d in metadata["date"]]
    return metadata

casing = "lower_non_acronyms"
# casing = "lower_non_acronyms"
# TODO: is lowercasing necessary?

def casing_function():
    if casing=="cased":
        return lambda x: x
    elif casing=="lower":
        return lambda x: x.lower()
    elif casing=="lower_non_acronyms":
        return lambda x: x if x.isupper() else x.lower()
    else:
        raise Exception

preprocess_filters = [
    casing_function(),
    strip_punctuation,
    strip_numeric,
    strip_non_alphanum,
    strip_multiple_whitespaces,
#     strip_numeric,
    remove_stopwords,
#     strip_short
]

class DocTextReader():
    def __init__(self, log_every=100):
        self.log_every = log_every
        s3 = boto3.resource('s3', region_name='us-west-1')
        self.bucket = s3.Bucket('autolocal-documents')

    def read_document_string(self, s3_path):
        return self.bucket.Object(s3_path).get()['Body'].read()

    def read_docs(self, s3_paths):
        # read all documents that we know about
        # tokenize each document
        # return list of documents

        documents = {}
        n_docs_total = len(s3_paths)

        i = 0
        n_docs_read = 0
        for s3_path in s3_paths:
            try:
                doc_string = self.read_document_string(s3_path)
                doc_tokens = preprocess_string(doc_string, filters=preprocess_filters)
                documents[s3_path] = {
                    "original_text": doc_string,
                    "tokens": doc_tokens
                }
            except Exception as e:
                if i < 10:
                    print("Key not found: {}".format(s3_path))
                elif i == 10:
                    print("More than 10 keys not found")
                    print(e)
                    break
                i+=1
            if n_docs_read % self.log_every == 0:
                print("{} of {} documents read".format(n_docs_read, n_docs_total))
            n_docs_read+=1

        return documents


def read_queries(query_source):
    if query_source == "actual":
        table = boto3.resource('dynamodb', region_name='us-west-2').Table('autoLocalNews')
    elif query_source == "quick":
        table = boto3.resource('dynamodb', region_name='us-west-1').Table('quick_queries')
    else:
        raise Exception
    queries = table.scan()["Items"]
    return queries


def read_history():
    try:
        table = boto3.resource('dynamodb', region_name='us-west-1').Table('history')
        history = table.scan()["Items"]
    except:
        history = []
    return history


def read_cached_idf():
    s3 = boto3.resource('s3', region_name='us-west-1')
    bucket = s3.Bucket('autolocal-documents')
    idf = json.load(bucket.Object('idf_{}.json'.format(casing)).get()['Body'])
    return idf

def cache_idf(idf):
    s3 = boto3.resource('s3')
    object = s3.Object('autolocal-documents', 'idf_{}.json'.format(casing))
    object.put(Body=json.dumps(idf))


def calculate_idf(all_docs): 
    # for each word, how many unique docs does it show up in?
    from collections import Counter
    
    doc_freq = {}
    for document in all_docs: 
        tokens = all_docs[document]["tokens"]
        for token in tokens:
            if token in doc_freq:
                doc_freq[token] += 1
            else:
                doc_freq[token] = 1
    
    inverse_doc_freq = {}
    for word in doc_freq:
        inverse_doc_freq[word] = 1./doc_freq[word]
    
    return inverse_doc_freq

time_windows = {
    'upcoming_only': datetime.now() + timedelta(days=0.5),
    'this_week': datetime.now() - timedelta(weeks=1),
    'this_year': datetime.now() - timedelta(days=365),
    'past_six_months':datetime.now() - timedelta(days=183),
    'all': None
}

def find_relevant_filenames(queries, metadata): 
    
    # filter metadata to only those files that match the query municipality and time_window
    municipalities_by_time_window = {}
    for query in queries:
        time_window = query['Time Window']
        if time_window in municipalities_by_time_window:
            municipalities_by_time_window[time_window].update(query['Municipalities'])
        else:
            municipalities_by_time_window[time_window] = set(query['Municipalities'])
            
    relevant_filenames = set()
    for time_window in municipalities_by_time_window:
        starting_date = time_windows[time_window]
        potential_documents = metadata
        if starting_date:
            potential_documents = potential_documents[potential_documents["date"] >= starting_date]
        cities = municipalities_by_time_window[time_window]
        potential_documents = potential_documents[[(c in cities) for c in potential_documents["city"]]]
        relevant_filenames.update(potential_documents['local_path_txt'])
    return relevant_filenames


def select_relevant_docs(municipalities, time_window, all_docs, metadata):
    # filter metadata to only those files that match the query municipality and time_window
    starting_date = time_windows[time_window]
    potential_documents = metadata
    if starting_date:
        potential_documents = potential_documents[potential_documents["date"] >= starting_date]
    potential_documents = potential_documents[[(c in municipalities) for c in potential_documents["city"]]]
    # filter all docs to only filenames in subset of metadata
    return [{**all_docs[f], 'filename':f} for f in potential_documents['local_path_txt'] if f in all_docs]


# TODO: Play with section length
# TODO: smart sectioning that's sensitive to multiple line breaks and other section break signals
# TODO: extract sections that overlap with each other
def segment_docs(relevant_docs):
    doc_sections = []
    approx_section_length = 100 # tokens
    min_section_length = 5
    
    for doc in relevant_docs:
        doc_tokens = doc["tokens"]
        original_text = doc["original_text"].decode('utf-8')
        filename = doc["filename"]
        
        doc_section_lines = []
        doc_section_tokens = []
        starting_page = 0
        starting_line = 0
        pages = original_text.split('\f')
        for p, page in enumerate(pages):
            lines = page.split('\n')
            for lnum, line in enumerate(lines):
                line_tokens = preprocess_string(line, filters=preprocess_filters)
                doc_section_tokens += line_tokens
                doc_section_lines.append(line)
                if len(doc_section_tokens) >= approx_section_length:
                    doc_sections.append({
                        **doc,
                        'starting_page': starting_page,
                        'starting_line': starting_line,
                        'ending_page': p,
                        'ending_line': lnum,
                        'section_text': '\n'.join(doc_section_lines),
                        'section_tokens': doc_section_tokens
                    })
                    doc_section_lines = []
                    doc_section_tokens = []
                    # have we reached the last line of this page?
                    if lnum == (len(lines)-1):
                        # next section starts at top of next page
                        starting_page = p+1
                        starting_line = 0
                    else:
                        # next section starts on next line of this page
                        starting_page = p
                        starting_line = lnum+1
        # end of the document
        if len(doc_section_tokens) >= min_section_length:
            doc_sections.append({
                **doc,
                'starting_page': starting_page,
                'starting_line': starting_line,
                'ending_page': p,
                'ending_line': lnum,
                'section_text': '\n'.join(doc_section_lines),
                'section_tokens': doc_section_tokens
            })
            
    return doc_sections

# TODO: use vectors to find closes words to keywords
def score_doc_sections(doc_sections, keywords, idf):
    # vectorize etc.
    # only consider keywords that have idf weights
    keywords = [keyword for keyword in keywords if (keyword in idf and keyword in vectors)]
    keyword_vectors = np.array([vectors[keyword] for keyword in keywords])
    keyword_weights = np.array([idf[keyword] for keyword in keywords])
    doc_sections_scores = []
    for s, section in enumerate(doc_sections):
        score = None
        section_tokens = section["section_tokens"]
        # TODO: Zipf to figure out what the cutoff should be for normal communication
        # If the number of unique tokens in the section is too small, it's probably not an interesting section
        if len(set(section_tokens))<20:
            score = 0
        else:
            section_vectors = np.array([vectors[t] for t in section_tokens if (t in idf and t in vectors)])
            if section_vectors.shape[0]>0:
    #             section_weights = np.array([inverse_doc_props[t] for t in section_tokens if t in inverse_doc_props])
                similarities = cosine_similarity(section_vectors, keyword_vectors)
    #             similarities = similarities * section_weights
    #             similarities = similarities*(similarities>0.2)
                keyword_similarities = np.mean(similarities, axis=0)
    #             keyword_similarities = np.average(similarities, axis=0, weights=section_weights)
                score = np.sum(keyword_similarities*keyword_weights)
        doc_sections_scores.append(score)

    return doc_sections_scores

def text_is_too_similar(a, b):
    # if there are only 2 edits to get from one text to the other, it's not good
    return editdistance.eval(a, b) < 20

# make sure we're not giving similar text among the top k (e.g. shows up on both minutes and agenda)
def check_repeated_text(top_k, section_text):
    for old in top_k:
        if text_is_too_similar(old[1]["section_text"], section_text):
            return True
    return False

def select_top_k(doc_sections, doc_sections_scores, k, user_history):
    sorted_sections = sorted(zip(doc_sections_scores, doc_sections), key=lambda pair: pair[0], reverse=True)
    top_k = []
    text_returned = []
    for x in sorted_sections:
        filename = x[1]["filename"]
        starting_page = x[1]["starting_page"]
        starting_line = x[1]["starting_line"]
        ending_page = x[1]["ending_page"]
        ending_line = x[1]["ending_line"]
        section_text = x[1]["section_text"]
        if filename in [x['filename'] for x in user_history]:
            print("this user has already seen their top file ({})".format(filename))
        elif check_repeated_text(top_k, section_text):
            print("this excpert has already been returned")
        else:
            top_k.append(x)
        if len(top_k) >= k:
            break
    return top_k

def update_with_top_k(history, top_k_sections, query):
    for section in top_k_sections:
        x = section[1]
        x.update(query)
        history.append(x)
    return history

def row2item(row):
    row = dict(row)
    item = {}
    for k,v in row.items():
        if k in ['local_path_pdf', 'local_path_txt']:
            v = v[8:]
        if isinstance(v, str):
            item[k] = v
        elif np.isnan(v):
            pass
    return item

def write_history(history):
    try:
        table = boto3.resource('dynamodb', region_name='us-west-1').Table('history')
        table.scan()
    except:
        table_args = {
            'TableName': 'autolocal-documents',
            'KeySchema': [
                {
                    'AttributeName': 'doc_id',
                    'KeyType': 'HASH'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'doc_id',
                    'AttributeType': 'S'
                }        
            ],
            'ProvisionedThroughput':
            {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        }
        table = dynamodb.create_table(**table_args)
    with table.batch_writer() as batch:
        for i, row in tqdm(history.iterrows()):
            item = row2item(row)
            batch.put_item(Item=item)

def send_emails(results): 
    pass

if __name__=='__main__':
    # TODO: contextual vectors
    vectors = setup_word_vectors()
    run_queries(use_cached_idf=True, query_source="quick")