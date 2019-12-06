#!/usr/bin/env python
# coding: utf-8

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
from sklearn.metrics.pairwise import cosine_similarity
import json
from autolocal.emailer import send_emails
import editdistance
import re
import argparse

def single_vector_per_doc(vectors):
    # vectors is a list of np arrays where:
    # dims: (LAYERS(3), TOKENS(varies), DIMENSIONS(1024))
    """
    https://towardsdatascience.com/elmo-helps-to-further-improve-your-word-embeddings-c6ed2c9df95f
    In the ELMo paper, there are 3 layers of word embedding,
    layer zero is the character-based context independent layer,
    followed by two Bi-LSTM layers. The authors have empirically
    shown that the word vectors generated from the first Bi-LSTM
    layer can better capture the syntax, and the second layer can
    capture the semantics better.
    """
    vectors = np.concatenate([v[2] for v in vectors], 0)
    return vectors

def read_doc(s3_path):
    s3 = boto3.resource('s3')
    autolocal_docs_bucket = s3.Bucket('autolocal-documents')
    try:
        return autolocal_docs_bucket.Object(s3_path).get()['Body'].read().decode("ascii", "ignore")
    except:
        return None

def read_metadata():
    table = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-documents')
    s3_client = boto3.client('s3')
    metadata = pd.DataFrame(table.scan()["Items"])
    metadata["date"] = [datetime.strptime(d, '%Y-%m-%d') for d in metadata["date"]]
    metadata['local_path_pkl'] = metadata['local_path_txt'].apply(lambda x: x[:-3]+"pkl")
    return metadata

def read_vectors(s3_path):
    # print(os.path.join("../data/pkls/", os.path.basename(s3_path)))
    return pickle.load(open(os.path.join("../data/pkls/", os.path.basename(s3_path)), 'rb'))

def write_vectors(array, s3_path):
    pickle.dump(array, open(os.path.join("../data/pkls/", os.path.basename(s3_path)), 'wb'))

def sentence_split(s):
    sentences = re.split('[.\n!?"\f]', s)
    return [s for s in sentences if len(s.strip())>0]

def tokenize(s):
    tokens = re.findall(r'\w+', s)
    return tokens

def read_queries():
    table = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-user-queries')
    queries = table.scan()["Items"]
    return queries

def parse_dates(start_date, end_date):
    starting_dates_for_filtering = {
        'upcoming_only': datetime.now(),
        'upcoming': datetime.now(),
        'this_week': datetime.now() - timedelta(weeks=1),
        'this_year': datetime.now() - timedelta(days=365),
        'this_month': datetime.now() - timedelta(weeks=5),
        'past_six_months':datetime.now() - timedelta(days=183),
        'last_six_months':datetime.now() - timedelta(days=183),
        'past': None,
        'all': None
    }
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = starting_dates_for_filtering['upcoming']
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    return start_date, end_date

def find_relevant_filenames(queries, metadata, start_date=None, end_date=None):

    cities = set()
    
    # filter metadata to only those files that match the query municipality and time_window
    for query in queries:
        cities.update(query["Municipalities"])
            
    relevant_filenames = set()

    potential_documents = metadata
    potential_documents = potential_documents[potential_documents["date"] >= start_date]
    if end_date:
        potential_documents = potential_documents[potential_documents["date"] >= end_date]

    potential_documents = potential_documents[[(c in cities) for c in potential_documents["city"]]]
    relevant_filenames.update(potential_documents['local_path_txt'])
    return relevant_filenames

def read_docs(s3_paths):
    log_every = 100

    documents = {}
    n_docs_total = len(s3_paths)

    i = 0
    n_docs_read = 0
    for s3_path in s3_paths:
        try:
            doc_string = read_doc(s3_path)
            doc_sentences = sentence_split(doc_string)
            doc_tokens = []
            for sentence in doc_sentences:
                sentence_tokens = tokenize(sentence)
                doc_tokens.append(sentence_tokens)
            filename_pkl = s3_path[:-3] + "pkl"
            try:
                vectors = read_vectors(filename_pkl)
                documents[s3_path] = {
                    "original_text": doc_string,
                    "sentences": doc_sentences,
                    "vectors": vectors
                }
            except:
                print('missing vectors for: {}'.format(s3_path))
        except Exception as e:
            if i < 10:
                print("Key not found: {}".format(s3_path))
            elif i == 10:
                print("More than 10 keys not found")
                print(e)
                break
            i+=1
        if n_docs_read % log_every == 0:
            print("{} of {} documents read".format(n_docs_read, n_docs_total))
        n_docs_read+=1

    return documents

def select_relevant_docs(municipalities, all_docs, metadata, start_date=None, end_date=None):
    # filter metadata to only those files that match the query municipality and time_window
    potential_documents = metadata
    if start_date:
        potential_documents = potential_documents[potential_documents["date"] >= start_date]
    if end_date:
        potential_documents = potential_documents[potential_documents["date"] >= end_date]
    potential_documents = potential_documents[[(c in municipalities) for c in potential_documents["city"]]]
    # filter all docs to only filenames in subset of metadata
    filenames = list(potential_documents['local_path_txt'])
    urls = list(potential_documents['url'])
    docs_to_return = []
    for i in range(len(filenames)):
        f = filenames[i]
        u = urls[i]
        if f in all_docs:
            docs_to_return.append({**all_docs[f], 'filename':f, 'url':u})
    # return [{**all_docs[f], 'filename':f, 'url':"example.com"} for f in potential_documents['local_path_txt'] if f in all_docs]
    return docs_to_return

# TODO: [PRIORITY] include section numbers, extract overlapping sections, enforce no overlaps in returned content
# TODO: Play with section length
# TODO: smart sectioning that's sensitive to multiple line breaks and other section break signals
def segment_docs(relevant_docs):
    min_section_length = 50 # tokens
    # TODO: this cuts of end of doc
    
    sections = []
    for doc in relevant_docs:
        original_text = doc["original_text"]
        pages = original_text.split('\f')
        page_numbers = []
        for p, page in enumerate(pages):
            page_sentences = sentence_split(page)
            # for each sentence, what page was it on?
            for sentence in page_sentences:
                sentence_tokens = tokenize(sentence)
                page_numbers.append(p+1)
        doc_sentences = doc["sentences"]
        doc_sentences_with_extra = doc["vectors"]["sentences"]
        doc_vectors_with_extra = doc["vectors"]["vectors"]
        nonempty_sentence_indices = [i for i in range(len(doc_sentences_with_extra)) if len(doc_sentences_with_extra[i].strip())>0]
        doc_vectors = [doc_vectors_with_extra[i] for i in nonempty_sentence_indices]
        section = []
        section_tokens = 0
        if (len(doc_sentences) == len(doc_vectors)):
            for i in range(len(doc_sentences)):
                sentence = doc_sentences[i]
                page = page_numbers[i]
                sentence_vectors = doc_vectors[i]
                sentence_tokens = tokenize(sentence)
                section.append({
                    "sentence": sentence,
                    "page": page,
                    "sentence_vectors": sentence_vectors,
                    "sentence_tokens": sentence_tokens
                })
                section_tokens += len(sentence_tokens)
                if section_tokens >= min_section_length:
                    section_text = ". ".join([s["sentence"].strip() for s in section])
                    sections.append({
                        "sentences": section,
                        "section_text": section_text,
                        "filename": doc["filename"],
                        "url": doc["url"]
                    })
                    section = []
                    section_tokens = 0
    return sections

def set_casing(x, casing="lower_non_acronyms"):
    if casing=="cased":
        return x
    elif casing=="lower":
        return x.lower()
    elif casing=="lower_non_acronyms":
        return (x if x.isupper() else x.lower())
    else:
        raise Exception

# TODO: use vectors to find closes words to keywords
# TODO: why do shorter documents get higher scores?
def score_doc_sections(doc_sections, orig_keywords, elmo):
    orig_keywords = [k.strip() for k in orig_keywords]
    keywords = []
    for k in orig_keywords:
        words = k.split(" ")
        for word in words:
            keywords.append(word)
    keyword_vectors = single_vector_per_doc([elmo.embed_sentence(keywords)])
    # keyword_weights = []
    # fix_case = casing_function()
    # idf_smoothing_count = 10
    # for k in keywords:
    #     words = k.split(" ")
    #     if len(words) > 1:
    #         keyword_weights.append(1./idf_smoothing_count)
    #     else:
    #         k = fix_case(k)
    #         if k in idf:
    #             keyword_weights.append(1./(1./idf[k]+idf_smoothing_count))
    #         else:
    #             keyword_weights.append(1./idf_smoothing_count)
    doc_sections_scores = []
    for s, section in enumerate(doc_sections):
        section_vectors = single_vector_per_doc([s["sentence_vectors"] for s in section["sentences"]])
        section_text = section['section_text']
        no_keywords_found = True
        for k in orig_keywords:
            if bool(re.search("([^\w]|^)" + k + "([^\w]|$)", section_text)):
            # if k in section_text:
            #     TODO: consider casing
                no_keywords_found = False
        for k in orig_keywords:
            if k.islower():
                if bool(re.search("([^\w]|^)" + k + "([^\w]|$)", section_text.lower())):
                    no_keywords_found = False
        if no_keywords_found:
            score = 0
        elif section_vectors.shape[0]>0:
            similarities = cosine_similarity(section_vectors, keyword_vectors)
            # if threshold_similarity > -1:
            #     similarities = similarities*(similarities>threshold_similarity)
            keyword_similarities = np.mean(similarities, axis=0)
            # score = np.sum(keyword_similarities*keyword_weights)
            score = np.mean(keyword_similarities)
        else:
            score = 0
        doc_sections_scores.append(score)

    return doc_sections_scores

def text_is_too_similar(a, b):
    # if there are only 2 edits to get from one text to the other, it's not good
    return editdistance.eval(a, b) < 50

# make sure we're not giving similar text among the top k (e.g. shows up on both minutes and agenda)
def check_repeated_text(top_k, section_text):
    for old in top_k:
        if text_is_too_similar(old[1]["section_text"], section_text):
            return True
    return False

def select_top_k(doc_sections, doc_sections_scores, k):
    sorted_sections = sorted(zip(doc_sections_scores, doc_sections), key=lambda pair: pair[0], reverse=True)
    top_k = []
    text_returned = []
    for x in sorted_sections:
        score = x[0]
        if score > 0:
            filename = x[1]["filename"]
            starting_page = x[1]["sentences"][0]["page"]
            ending_page = x[1]["sentences"][-1]["page"]
            section_text = x[1]["section_text"]
            if check_repeated_text(top_k, section_text):
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

def run_queries(elmo, input_args):
    k = input_args.k 
    start_date, end_date = parse_dates(input_args.start_date, input_args.end_date)
    print("reading queries")
    queries = read_queries()
    queries = [q for q in queries if ('Status' in q and q['Status'] == 'just_submitted')]
    print("reading metadata")
    metadata = read_metadata()
    print("finding relevant filenames")
    relevant_filenames = find_relevant_filenames(queries, metadata, start_date = start_date, end_date = end_date)
    print("reading relevant documents")
    # (not actually *all*, but all the ones we care about for queries)
    all_docs = read_docs(relevant_filenames)

    results = []
    
    for q, query in enumerate(queries):
        print("running query {} of {}".format(q, len(queries)))
        user_id = query["id"]
        email_address = query["email_address"]
        print("email address: {}".format(email_address))
        keywords = query["Keywords"]
        municipalities = query["Municipalities"]
        relevant_docs = select_relevant_docs(municipalities, all_docs, metadata)
        print("segmenting documents")
        doc_sections = segment_docs(relevant_docs)
        print("scoring documents")
        doc_sections_scores = score_doc_sections(
            doc_sections,
            keywords,
            elmo
        )
        top_k_sections = select_top_k(doc_sections, doc_sections_scores, k)
        results = update_with_top_k(results, top_k_sections, query)
        
    print("sending emails")
    send_emails(results, args)
    print("finished")

if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Section documents and rank by relevance to queries')

    parser.add_argument('--email', type=str, required=True,
        help='Who should I send emails to?\nUse `--email P` to send to the actual addresses in the queries.')

    parser.add_argument('--start_date', type=str, default=None,
        help="".join([
            'Documents have dates associated with them. ',
            'What is the earliest date of the documents that we should return?\n',
            'Format is YYYY-MM-DD, e.g. 2019-12-4 for December 4, 2019.\n',
            'Default is to include Minutes from meetings that took place this ',
            'past week and Agendas for upcoming meetings'
        ]))

    parser.add_argument('--end_date', type=str, default=None,
        help="".join([
            'Documents have dates associated with them. ',
            'What is the latest date of the documents that we should return?\n',
            'Format is YYYY-MM-DD, e.g. 2019-12-4 for December 4, 2019.\n',
            'Default is to include *all* documents after the start date.'
        ]))

    parser.add_argument('--k', type=int, default=5,
        help="".join([
            'We will return the top k results. Default is k=5.'
        ]))

    args = parser.parse_args()
    print(args)

    elmo = ElmoEmbedder()

    run_queries(
        elmo=elmo,
        input_args=args
    )


