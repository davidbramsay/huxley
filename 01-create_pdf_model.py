from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO, BytesIO

from ebooklib import epub
from bs4 import BeautifulSoup

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize

import glob
import os
import cPickle as pickle

from helper_epub_cover import get_cover_image

#trains model on text, analyzes all epub and pdf files in './pdfs/' folder
#spits out trained model for Doc2Vec in './models' folder, saves structured data
#along with tagged_text and tagged_title objects in models folder as well

#structured data-- if epub, pulls text directly from epub, but converts to a
#pdf and saves in './pdfs/epub_pdfs' and saves the file link to that file. It
#also extracts an image of the cover and saves that as 'cover_page' instead of
#an integer that represents the page to load from the pdf (because the pdf
#conversion frequently messes up the cover page).  In future steps, check
#type of 'cover_page', load if int, display as PIL image otherwise.

def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = BytesIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue().decode('utf8')

    fp.close()
    device.close()
    retstr.close()

    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')

    return text


def convert_epub_to_txt(path):
    book = epub.read_epub(path)

    text = ''
    for doc in book.get_items():
        text += BeautifulSoup(doc.content, "lxml").text

    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')

    return text


def get_pdfs(path='./pdfs/'):
    files = glob.glob(path + '*.pdf')
    return files


def get_epubs(path='./pdfs/'):
    files = glob.glob(path + '*.epub')
    return files


def get_pdfs_epubs(path='./pdfs/'):
    files = glob.glob(path + '*.epub')
    files += glob.glob(path + '*.pdf')
    return files

def convert_epub_pdf(filepath, newpath='./pdfs/epub_pdfs/', margin='.5in', fontsize=20, font='Helvetica'):
    newpath = newpath + filepath.split('/')[-1]
    newpath = newpath[:-4] + 'pdf'
    print 'converting/saving ' + newpath
    os.system('pandoc "' + filepath + '" -o "' + newpath + '" --pdf-engine=xelatex -V documentclass=scrartcl -V mainfont="' + font + '" -V fontsize="' + str(fontsize) + 'pt" -V geometry:margin=' + margin)
    return newpath



def get_title_tokens(title):
    #accept folder/*.pdf and give back tokenized filename
    title = title[title.rfind('/')+1:title.rfind('.')]

    title = title.replace('_', ' ')
    title = title.replace('-', ' ')
    title = title.replace('.', ' ')
    title = title.replace(',', ' ')
    title = title.replace('(', ' ')
    title = title.replace(')', ' ')
    title = title.replace('[', ' ')
    title = title.replace(']', ' ')

    return word_tokenize(title.lower())


def structure_data(file):

    assert('.pdf' in file or '.epub' in file), 'must be either epub or pdf'

    if '.pdf' in file:
        text = word_tokenize(convert_pdf_to_txt(file).lower())
        cover_page = 0
    else:
        text = word_tokenize(convert_epub_to_txt(file).lower())

        if file.startswith('./'): cover_page = get_cover_image(file[2:])
        else: cover_page = get_cover_image(file)

        file = convert_epub_pdf(file)


    return {
        'file' : file,
        'title' : get_title_tokens(file),
        'text': text,
        'cover_page': cover_page,
        'last_accessed': 0,
        'first_page': 1,
        'current_page': 1
    }


def build_data(path='./pdfs/'):
    #build a gensim doc2vec model given a pdf folder path

    pdfs = get_pdfs_epubs(path)

    structured_pdfs = []
    for p in pdfs:
        print 'analyzing ' + p + '...'
        try:
            structured_pdfs.append(structure_data(p))
        except Exception as e:
            print 'FAILED'
            print e.message, e.args

    tagged_texts = [TaggedDocument(words=data['text'], tags=[str(i)]) for i, data in enumerate(structured_pdfs)]
    tagged_titles = [TaggedDocument(words=data['title'], tags=[str(i)]) for i, data in enumerate(structured_pdfs)]

    return structured_pdfs, tagged_texts, tagged_titles


def train_model(tagged_data, save_name=None, epochs=100, latent_size=5, alpha=0.025, min_alpha=0.00025, min_count=1, dm=1):

    model = Doc2Vec(size=latent_size,
                    alpha=alpha,
                    min_alpha=min_alpha,
                    min_count=min_count,
                    dm=dm)

    model.build_vocab(tagged_data)

    for epoch in range(epochs):
        if not int(epoch)%25: print('iteration {0}'.format(epoch))
        model.train(tagged_data,
                    total_examples=model.corpus_count,
                    epochs=model.iter)
        # decrease the learning rate
        model.alpha -= 0.0002
        # fix the learning rate, no decay
        model.min_alpha = model.alpha

    if save_name is not None: model.save('models/' + save_name + ".model")

    return model


if __name__=='__main__':

    ## SIMPLE TEST PDF
    #pdfs = get_pdfs()
    #for p in pdfs: print get_title_tokens(p)
    #print '----'
    #print convert_pdf_to_txt(pdfs[0])

    ## SIMPLE TEST EPUB
    #epubs = get_epubs()
    #for p in epubs: print get_title_tokens(p)
    #print '----'
    #print convert_epub_to_txt(epubs[0])

    try:
        structured_data, tagged_texts, tagged_titles = pickle.load(open('models/pdf_database.pkl', 'rb'))
        print 'found and loaded existing tagged document data'
    except:
        print 'no existing data found, building database...'
        structured_data, tagged_texts, tagged_titles = build_data()
        print 'saving...'
        pickle.dump((structured_data, tagged_texts, tagged_titles), open('models/pdf_database.pkl', 'wb'))

    print 'training model on text...'
    train_model(tagged_texts, 'texts_temp', 10000)
    train_model(tagged_titles, 'titles_temp', 10000)

