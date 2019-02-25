import glob
import os
import cPickle as pickle

from PIL import Image
import fitz

from helper_eink_render import load_doc, get_page, make_page

#open previous structured data, type in title, author, check cover page and start page and update.  Save to new metadata tag.
#first script generates images for cover for epub files, but not for pdfs.  This will render a

try:
    print 'loading structured data...'
    structured_data, _, _ = pickle.load(open('models/pdf_database.pkl', 'rb'))
    print 'found and loaded existing tagged document data'
except:
    print 'Cannot find structured data'


final_data = []

for book in structured_data:

    #book should have file, title, text, last_accessed, cover_page, current_page
    print '\n'
    print 'assessing ' + book['file']
    print book['title']
    print '\n'

    title = raw_input("enter title:")
    book['title_print'] = title

    author = raw_input("enter author:")
    book['author_print'] = author

    doc = load_doc(book['file'])

    found_cover = False
    n=0

    if type(book['cover_page']) is int:
        while not found_cover:
            get_page(doc, n).show()
            cover = raw_input("Cover? (y/n):")

            if 'n' not in cover.lower(): found_cover = True
            else: n = n + 1

        book['cover_page'] = get_page(doc, n)

    else:
        print 'already have cover, attempting to show.'
        try:
            book['cover_page'] = make_page(book['cover_page'])
            book['cover_page'].show()
        except Exception as e:
            print 'Failed ' + e

    n = n + 1
    found_firstpage = False

    while not found_firstpage:
        get_page(doc, n).show()
        firstpage = raw_input("First Page? (y/n):")

        if 'n' not in firstpage.lower(): found_firstpage = True
        else: n = n + 1

    book['first_page'] = n
    book['current_page'] = n

    final_data.append(book)
    pickle.dump(final_data, open('models/book_metadata.pkl', 'wb'))

for book in final_data:
    del book['text']
    book['interested'] = False
    book['not_interested'] = False
    book['completed'] = False
    book['days_shown'] = 0
    book['days_interacted'] = 0
    book['pages_per_interaction_day'] = []
    book['time_per_interaction_day'] = []
    book['pickups_per_interaction_day'] = []

pickle.dump(final_data, open('models/simple_book_metadata.pkl', 'wb'))
