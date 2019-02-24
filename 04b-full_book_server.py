from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize

from flask import Flask
from flask_restful import Api, Resource, reqparse

import cPickle as pickle
import json
import time


# load models
# load state (books and page)
# connect to eink display #1 and #2
# set title
# load book function (render cover, get current page, render page)
# randomly choose and load a book
# change page forward/back function (log activity, save current page)


# serve an API to:
#   -get all books in huxley
#   -get history of interactions
#   -force huxley to be a book by title
#   -force huxley to be a book given a query
#   -force huxley new random book
#   -force huxley to update based on rules and query
#   ----load interaction history.
#   ----parse each book (#days shown, #days interacted, array of pages viewed
#   per interaction day, array of time spent per interaction day, array of
#   # pick-ups per interaction day (timeout ~15min)
#   ----shown/unknown if interested (no pickups), amount of days is inversely proportional
#   to selection probability. Expire in 24 hours.
#   ----show/interested but book likely bad. Only read for a short duration
#   once. Expire in 24 hours.
#   ----shown/interested and reading.
#   ---- if current book interacted with for a long duration or >1 pickup, timeout = 72
#   hours.
#   ---- if current book is timed out, likely bad book gets small probability
#   two weeks from previous exposure.
#   ---- current book, currentInterested =True means expire in 72 not 24 hours, if
#   interested=False expire in 24 hours, update timestamp based on switch to
#   book or last interaction.  Always tart at currentInterest=False and track
#   interactions in cache.
#   ---- probabilities - shown/unknown interest has probability proportional to
#   1/days shown, likely uninterested has no probability for 2 weeks, and then
#   small probability, likely interested has probability equal to 0 days of
#   being shown.


#every interaction, update state, update lastinteraction, set timeout for no activity and end of session

# button press monitor:
# short - move forward a page, log activity
# long - move back a page, log activity

TEXT_MODEL = 'models/texts_temp.model'
TITLE_MODEL = 'models/titles_temp.model'
PDF_DATABASE = 'models/pdf_database.pkl'

BOOK_METADATA = 'models/simple_book_metadata.pkl'

#['time_per_interaction_day',
# 'last_accessed',
# 'not_interested',
# 'pickups_per_interaction_day',
# 'cover_page',
# 'completed',
# 'current_page',
# 'days_interacted',
# 'days_shown',
# 'first_page',
# 'interested',
# 'title_print',
# 'file',
# 'pages_per_interaction_day',
# 'title',
# 'author_print']

TITLE_WEIGHTING = 0.2


app = Flask(__name__)
api = Api(app)

current_state = {
        'current_interest': False,
        'book_completed': False,
        'last_accessed': time.time(),
        'pickups': 0,
        'time_used': 0,
        'book_index': None,
        'book': None
        }

print 'loading models...'
text_model= Doc2Vec.load(TEXT_MODEL)
title_model= Doc2Vec.load(TITLE_MODEL)
structured_data, _, _ = pickle.load(open('models/pdf_database.pkl', 'rb'))


print 'cleaning titles and making book objects...'
for i in range(len(structured_data)):
    structured_data[i]['title'] = ' '.join(structured_data[i]['title'])
    structured_data[i]['id'] = str(i)
    structured_data[i]['text_vector'] = text_model.docvecs[str(i)].tolist()
    structured_data[i]['title_vector'] = title_model.docvecs[str(i)].tolist()


#-- HELPERS --

def getId(title):
    #return id from title
    for b in structured_data:
        if title in b['title']:
            return b['id']

    print title + ' not found'

    return 'ERROR: not found'


def getSimilarBooks(bookid, n=3):
    #get similar books given a bookid
    bookid = str(bookid)

    top_titles = title_model.docvecs.most_similar(bookid, topn=n)
    top_texts = text_model.docvecs.most_similar(bookid, topn=n)

    #combine title and text scores; bigger scores are better
    scores = {}
    for i in range(n):
        if top_titles[i][0] not in scores: scores[top_titles[i][0]] = 0.0
        if top_texts[i][0] not in scores: scores[top_texts[i][0]] = 0.0
        scores[top_titles[i][0]] += TITLE_WEIGHTING * top_titles[i][1]
        scores[top_texts[i][0]] += (1.0-TITLE_WEIGHTING) * top_texts[i][1]

    #put in list and sort
    score_list = [[k, v] for k, v in scores.items()]
    score_list.sort(key=lambda x: x[1], reverse=True)

    #limit to top n
    score_list = score_list[:n]

    #add in titles
    for i in range(n):
        score_list[i].insert(1, getObj(score_list[i][0])['title'])

    return score_list


def getObj(bookid):
    #return parsed object (structured data - text) given id
    intid = int(bookid)

    returnval = dict(structured_data[intid])
    del returnval['text']

    return returnval


def getText(bookid):
    #return text of book given id
    return " ".join(structured_data[int(bookid)]['text'])


def getFullObj(bookid):
    #return full object (structured data and text and similar books)
    returnval = dict(structured_data[int(bookid)])
    returnval['similar_books'] = getSimilarBooks(bookid)
    return returnval


def docvecQuery(query, n=10):
    #return ordered results [[bookid, title, score],...] of query
    title_v = title_model.infer_vector(query)
    top_titles = title_model.docvecs.most_similar([title_v], topn=n)

    text_v = text_model.infer_vector(query)
    top_texts = text_model.docvecs.most_similar([text_v], topn=n)

    #combine title and text scores; bigger scores are better
    scores = {}
    for i in range(n):
        if top_titles[i][0] not in scores: scores[top_titles[i][0]] = 0.0
        if top_texts[i][0] not in scores: scores[top_texts[i][0]] = 0.0
        scores[top_titles[i][0]] += TITLE_WEIGHTING * top_titles[i][1]
        scores[top_texts[i][0]] += (1.0-TITLE_WEIGHTING) * top_texts[i][1]

    #put in list and sort
    score_list = [[k, v] for k, v in scores.items()]
    score_list.sort(key=lambda x: x[1], reverse=True)

    #limit to top n
    score_list = score_list[:n]

    #add in titles
    for i in range(n):
        score_list[i].insert(1, getObj(score_list[i][0])['title'])

    return score_list


#-- API --

class GetBookByTitle(Resource):
    #return book object given a partial title
    def get(self, title):
        return getObj(getId(title))

class GetBookByID(Resource):
    #return book object given a partial title
    def get(self, bookid):
        return getObj(bookid)

class GetBookIDByTitle(Resource):
    #return book id given a partial title
    def get(self, title):
        return getId(title)

class GetBookTextByID(Resource):
    # return book text given a bookid
    def get(self, bookid):
        return getText(bookid)

class GetSimilarBooksByID(Resource):
    #return similar book objects given a bookid
    def get(self, bookid):
        return getSimilarBooks(bookid)

class Query(Resource):
    #return most similar book objects and scores given a  query
    def get(self, query):
        print query
        query = query.replace('%20', ' ')
        query = query.replace('+', ' ')
        query = query.replace('_', ' ')

        query = word_tokenize(query.lower())

        results = docvecQuery(query)

        return results

class GetTitles(Resource):
    #return a list of available titles
    def get(self):
        return [b['title'] for b in structured_data]

class GetBooks(Resource):
    #return a list of available book objects
    def get(self):
        return [getObj(str(bookid)) for bookid in range(len(structured_data))]


api.add_resource(Query, '/query/<string:query>')

api.add_resource(GetTitles, '/getTitles')
api.add_resource(GetBooks, '/getBooks')

api.add_resource(GetBookByTitle, '/getBook/<string:title>')
api.add_resource(GetBookIDByTitle, '/getId/<string:title>')

api.add_resource(GetBookByID, '/id/<string:bookid>/book')
api.add_resource(GetBookTextByID, '/id/<string:bookid>/text')
api.add_resource(GetSimilarBooksByID, '/id/<string:bookid>/similar')


if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
