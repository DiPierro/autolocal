#!/usr/bin/env python
# coding: utf-8

# In[1]:


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

s3 = boto3.resource('s3')
autolocal_docs_bucket = s3.Bucket('autolocal-documents')
def read_doc(s3_path):
    try:
        return autolocal_docs_bucket.Object(s3_path).get()['Body'].read().decode("ascii", "ignore")
    except:
        return None


# In[ ]:


def read_metadata():
    table = boto3.resource('dynamodb', region_name='us-west-1').Table('autolocal-documents')
    s3_client = boto3.client('s3')
    metadata = pd.DataFrame(table.scan()["Items"])
    metadata["date"] = [datetime.strptime(d, '%Y-%m-%d') for d in metadata["date"]]
    metadata['local_path_pkl'] = metadata['local_path_txt'].apply(lambda x: x[:-3]+"pkl")
    return metadata
metadata = read_metadata()


# In[ ]:


def read(s3_path):
    # print(os.path.join("../data/pkls/", os.path.basename(s3_path)))
    return pickle.load(open(os.path.join("../data/pkls/", os.path.basename(s3_path)), 'rb'))

def write(array, s3_path):
    pickle.dump(array, open(os.path.join("../data/pkls/", os.path.basename(s3_path)), 'wb'))

def sentence_split(s):
    sentences = re.split('[.\n!?"\f]', s)
    return [s for s in sentences if len(s.strip())>0]

def tokenize(s):
    tokens = re.findall(r'\w+', s)
    return tokens


# In[ ]:


starting_dates_for_filtering = {
    'upcoming_only': datetime.now() + timedelta(days=0.5),
    'upcoming': datetime.now() + timedelta(days=0.5),
    'this_week': datetime.now() - timedelta(weeks=1),
    'this_year': datetime.now() - timedelta(days=365),
    'this_month': datetime.now() - timedelta(weeks=5),
    'past_six_months':datetime.now() - timedelta(days=183),
    'last_six_months':datetime.now() - timedelta(days=183),
    'past': None,
    'all': None
}


# In[ ]:


def read_queries():
    table = boto3.resource('dynamodb', region_name='us-west-2').Table('autoLocalNews')
    queries = table.scan()["Items"]
    return queries


# In[ ]:


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
        starting_date = starting_dates_for_filtering[time_window]
        potential_documents = metadata
        if starting_date:
            potential_documents = potential_documents[potential_documents["date"] >= starting_date]
        cities = municipalities_by_time_window[time_window]
        potential_documents = potential_documents[[(c in cities) for c in potential_documents["city"]]]
        relevant_filenames.update(potential_documents['local_path_txt'])
    return relevant_filenames


# In[ ]:


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
                vectors = read(filename_pkl)
                documents[s3_path] = {
                    "original_text": doc_string,
                    "sentences": doc_sentences,
#                     "tokens": doc_tokens,
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


# In[ ]:





# In[ ]:


def select_relevant_docs(municipalities, time_window, all_docs, metadata):
    # filter metadata to only those files that match the query municipality and time_window
    starting_date = starting_dates_for_filtering[time_window]
    potential_documents = metadata
    if starting_date:
        potential_documents = potential_documents[potential_documents["date"] >= starting_date]
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


# In[ ]:





# In[ ]:


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


# In[ ]:


#             page_tokens = simple_tokenizer.tokenize(page)
#             for t in page_tokens:
#                 page_numbers.append(p+1)
#         doc_tokens = doc["tokens"]
#         vectors = select_layer(doc["vectors"])
# #         print(vectors.shape)
#         filename = doc["filename"]
#         n_tokens = len(doc_tokens)
# #         print(n_tokens)
#         tokens_per_section = 100
#         n_sections = n_tokens // tokens_per_section
# #         n_sections = int(np.floor(tokens_per_section / n_tokens))
# #         print(n_sections)
#         for s in range(n_sections):
#             start_index = s*tokens_per_section
#             end_index = ((s+1)*tokens_per_section)
#             section_tokens = doc_tokens[start_index:end_index]
#             section_vectors = vectors[start_index:end_index,]
#             section_start_page = page_numbers[start_index]
#             section_end_page = page_numbers[min(len(page_numbers), end_index)-1]
#             doc_sections.append({
#                 'filename': doc['filename'],
#                 'url': doc['url'],
#                 'start_page': section_start_page,
#                 'end_page': section_end_page,
#                 'text': " ".join(section_tokens),
# #                 'tokens': section_tokens,
#                 'vectors': section_vectors
#             })
            
#     return doc_sections


# In[ ]:


# doc_sections = segment_docs(relevant_docs)
# print("sections: {}".format(len(doc_sections)))
# print(doc_sections[0]['section_text'])


# In[ ]:


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


# In[ ]:


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
#     keyword_weights = []
#     fix_case = casing_function()
# #     idf_smoothing_count = 10
#     for k in keywords:
# #         words = k.split(" ")
# #         if len(words) > 1:
# #             keyword_weights.append(1./idf_smoothing_count)
# #         else:
# #             k = fix_case(k)
# #             if k in idf:
# #                 keyword_weights.append(1./(1./idf[k]+idf_smoothing_count))
# #             else:
# #                 keyword_weights.append(1./idf_smoothing_count)
    doc_sections_scores = []
    for s, section in enumerate(doc_sections):
        section_vectors = single_vector_per_doc([s["sentence_vectors"] for s in section["sentences"]])
        section_text = section['section_text']
        no_keywords_found = True
        for k in orig_keywords:
            if bool(re.search("([^\w]|^)" + k + "([^\w]|$)", section_text)):
#             if k in section_text:
                # TODO: consider casing
                no_keywords_found = False
        for k in orig_keywords:
            if k.islower():
                if bool(re.search("([^\w]|^)" + k + "([^\w]|$)", section_text.lower())):
                    no_keywords_found = False
        if no_keywords_found:
            score = 0
        elif section_vectors.shape[0]>0:
            similarities = cosine_similarity(section_vectors, keyword_vectors)
#             if threshold_similarity > -1:
#                 similarities = similarities*(similarities>threshold_similarity)
            keyword_similarities = np.mean(similarities, axis=0)
#             score = np.sum(keyword_similarities*keyword_weights)
            score = np.mean(keyword_similarities)
        else:
            score = 0
        doc_sections_scores.append(score)

    return doc_sections_scores


# In[ ]:


# doc_sections_scores = score_doc_sections(
#     doc_sections,
#     keywords
# )
# # doc_sections_scores


# In[ ]:


def text_is_too_similar(a, b):
    # if there are only 2 edits to get from one text to the other, it's not good
    return editdistance.eval(a, b) < 50

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
        score = x[0]
        if score > 0:
            filename = x[1]["filename"]
            starting_page = x[1]["sentences"][0]["page"]
            ending_page = x[1]["sentences"][-1]["page"]
            section_text = x[1]["section_text"]
            # debugging parameter -- DO send the same thing multiple times if we're debugging
            if filename in [x[1]['filename'] for x in user_history]:
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


# 'original_text', 'tokens', 'filename', 'starting_page', 'starting_line', 'ending_page', 'ending_line', 'section_text', 'section_tokens', 'Municipalities', 'id', 'Keywords', 'Time Window'
def reformat_results(results):
    reformatted_results = {}
    # one per query
    for result in results:
        username = result['id']
        keywords = result['Keywords']
        query_id = username + ",".join(keywords) + ",".join(result['Municipalities']) + ",".join(result['Time Window'])
        if query_id not in reformatted_results:
            reformatted_results[query_id] = {
                'user_id': username,
                'document_sections': []
            }
        reformatted_results[query_id]['document_sections'].append({
            # TODO
            "section_id": "000",
            # TODO
            "doc_url": result['url'],
            "doc_name": os.path.basename(result['filename']),
            "user_id": username,
            "page_number": result["sentences"][0]["page"],
            "keywords": keywords,
            "text": result['section_text'].encode('ascii', errors='ignore').decode('ascii')
        })
    return [reformatted_results[r] for r in reformatted_results]

# vectors = setup_word_vectors()
def run_queries(elmo, k=3): 
    print("reading queries")
    queries = read_queries()
    queries = [q for q in queries if ('Status' in q and q['Status'] == 'just_submitted')]
    # print(queries)
    print("reading metadata")
    metadata = read_metadata()
    # print("setting up reader")
    # doc_text_reader = DocTextReader(log_every=100)
    print("finding relevant filenames")
    relevant_filenames = find_relevant_filenames(queries, metadata)
    # (not actually *all*, but all the ones we care about for queries)
    print("reading relevant documents")
    # all_docs = doc_text_reader.read_docs(relevant_filenames)
    all_docs = read_docs(relevant_filenames)
    print("reading history")
    # history = read_history()
    history = []

    results = []
    
    for q, query in enumerate(queries):
        print("running query {} of {}".format(q, len(queries)))
        user_id = query["id"]
        print("user id: {}".format(user_id))
        user_history = [x for x in history if x['id'] == user_id]
        keywords = query["Keywords"]
        print(keywords)
        time_window = query["Time Window"]
        municipalities = query["Municipalities"]
        relevant_docs = select_relevant_docs(municipalities, time_window, all_docs, metadata)
        print("segmenting documents")
        doc_sections = segment_docs(relevant_docs)
        print("scoring documents")
        doc_sections_scores = score_doc_sections(
            doc_sections,
            keywords,
            elmo
        )
        top_k_sections = select_top_k(doc_sections, doc_sections_scores, k, user_history)
        results = update_with_top_k(results, top_k_sections, query)
        history = update_with_top_k(history, top_k_sections, query)
        
    print("sending emails")
    r = reformat_results(results)
    # print(r)
    send_emails(r)
    # write_history(history)
    print("finished")


if __name__=='__main__':
    elmo = ElmoEmbedder()

    run_queries(
        elmo=elmo,
        k=5
    )


