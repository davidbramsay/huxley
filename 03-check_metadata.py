import cPickle as pickle
from PIL import Image

from helper_eink_render import load_doc, get_page, make_page, binarize_img

#check our book data for each book

book_data = pickle.load(open('models/book_metadata.pkl', 'rb'))

for book in book_data:
    '''
    for k,v in book.items():
        if k == 'text': print k + ':\t' + str(len(v)) + ' words'
        elif k == 'cover_page': binarize_img(v).show()
        else: print k + ':\t' + str(v)
    '''

    doc = load_doc(book['file'])
    get_page(doc, book['first_page']).show()

    raw_input("enter to continue...")

