import helper_epd7in5
import helper_command
from helper_eink_render import load_doc, total_pages, get_page

import RPi.GPIO as GPIO
from PIL import Image,ImageDraw,ImageFont
from datetime import datetime
import cPickle as pickle
import threading
import time
import os

# - globals/state -

DEBUG = True
CACHE_LOCATION = 'models/cache_book_metadata.pkl'

try: book_data = pickle.load(open(CACHE_LOCATION, 'rb'))
except: book_data = pickle.load(open('models/simple_book_metadata.pkl', 'rb'))

epd_page = helper_epd7in5.EPD(cover=False)
epd_cover = helper_epd7in5.EPD(cover=True)

sleeping = True #whether sleeping or not
pickup_timer = None #records time at begining of pickup event
sleep_timeout = None #timer for timing out inactivity after 15 minutes (sleep display)
book_timeout = None #timer for timing out book change (24 hours from last activity for untouched/unintersted books, 72 for interested books)

s = {
    'current_interest': False, #interest level since start of book offering
    'session_start': None, #start of book offering (doesn't update each day)
    'current_pickups': 0, #accumulated pickups for day (updated each day)
    'current_pageviews': 0, #accumulated pickups for day (updated each day)
    'current_time_used': 0, #accumulated time for day (updated each day)
    'book_index': None, #book_data[s['book_index']] gives us the book object
    'doc': None #a fitz loaded document, to extract PDF pages from w/PyMuPDF
}

#protects pickup_timer, s['current_pickups'], and s['current_time_used']
s_lock = threading.RLock() #lock to deal with race condition of 15 min inactive session timeout with book switching or day-state update
#protects book_data like current_page, last_accessed, and s/book_data coherence when updating book_data from s
b_lock = threading.RLock() #lock to handle book updates and disable any page turns messing with the state nondeterministically

#we need to check if we're 'interested' based on num pickups/time read that day, and then update/clear pickups/time read.  During these evals/writes, it's possible for pickups and time read to be updated in the background
#not_interested is set if a book is interacted with the first time, and during that day they spend <5min with it over 1 session.  We assume they're not interested.
#interested behavior is any day with 2 pickups or a longer session than 5min. Showing interest ensures the not_interested flag is set to False and the Interested flag is set true.
#This is different than current_interest, which is interest since the book was rendered and available.  This is what determines whether the book timeout is 24 hours or 72 hours since last_active.  The main flags are stored to give easy training data about interest and to influence probabilities when picking a new book.


def log(statement):
    if DEBUG: print datetime.now.strftime('[%Y-%m-%dT%H:%M:%SZ] ' + statement)


def log_state():
    book = book_data[s['book_index']]
    if DEBUG:
        print datetime.now.strftime('[%Y-%m-%dT%H:%M:%SZ]')
        print '-'*10 + ' STATE' + '-'*10
        print 'current_interest:\t' + str(s['current_interest'])
        print 'session_start:\t' + str(s['session_start'])
        print 'current_pickups:\t' + str(s['current_pickups'])
        print 'current_pageviews:\t' + str(s['current_pageviews'])
        print 'current_time_used:\t' + str(s['current_time_used'])
        print 'book_index:\t' + str(s['book_index'])
        print '--'
        print 'time_per_interaction_day:\t' + str(book['time_per_interaction_day'])
        print 'pickups_per_interaction_day:\t' + str(book['pickups_per_interaction_day'])
        print 'pages_per_interaction_day:\t' + str(book['pages_per_interaction_day'])
        print 'last_accessed:\t' + str(book['last_accessed'])
        print 'interested:\t' + str(book['interested'])
        print 'not_interested:\t' + str(book['not_interested'])
        print 'completed:\t' + str(book['completed'])
        print 'current_page:\t' + str(book['current_page'])
        print 'days_shown:\t' + str(book['days_shown'])
        print 'days_interacted:\t' + str(book['days_interacted'])
        print '-'*8 + ' END STATE' + '-'*8


def cache_bookdata():
    log('saving book_data')
    log_state()
    pickle.dump(book_data, open(CACHE_LOCATION, 'rb'))


def inactive_15min_timeout():
    #inactivity timer for session/sleep
    global sleep_timeout
    sleep_timeout.cancel()
    sleep_timeout = None

    log('inactivity timeout')

    with s_lock:
        sleeping = True
        #pickup event done, add time to current_time_used
        s['current_time_used'] += time.time() -14*60 - pickup_timer
        pickup_timer = None

    #put epd to sleep
    log('sleeping...')
    epd_page.sleep()

    log_state()


def book_check_timeout():
    #called in 24 hour increments since start or since last-accessed,
    #whichever is sooner
    #i.e. called at (24HR,la=6 hours ago), (42HR,la=8 hours ago), (48HR, la=14
    #hours ago), (58HR, la=24hr ago)...
    #when book is completed, we will hijack this timer to expire 1 hour from
    #book completion.
    global book_timeout
    book_timeout.cancel()
    book_timeout = None

    with b_lock:

        now = time.time()
        last = book_data[s['book_id']]['last_accessed']
        if (last == 0): last = s['session_start']

        hrs_since_start = (now-s['session_start'])/(60.0*60.0)
        hrs_since_access = (now-last)/(60.0*60.0)

        log('book timeout:\t' + str(hrs_since_start) + 'hrs since session_start, ' + str(hrs_since_access) + ' hrs since last_access')

        def interested():
            log('current interest changed to interested.')
            s['current_interest'] = True
            book_data[s['book_id']]['interested'] = True
            book_data[s['book_id']]['not_interested'] = False

        #update current_interested (pickups, duration)
        #account for 15min timeout (if active, extra time since pickup_timer)
        if not s['current_interest']: #if we're not currently interested..
            with s_lock:
                if s['current_pickups'] > 1 or s['current_time_used'] > 5*60:
                    interested()
                elif not sleeping: #if we didn't do enough but we're active...
                    if s['current_time_used'] + (last - pickup_timer) > 5*60:
                        interested()

        #new book if completed
        if book_data[s['book_id']]['completed']:
            smart_choice_book()
            return
        #new book if not interested, and time is >=24hr since last-access
        if not s['current_interest'] and now - 23*60*60 > last:
            smart_choice_book()
            return
        #new book if interested and time >=72 hr since last-access
        if s['current_interest'] and now - 71*60*60 > last:
            smart_choice_book()
            return

        #otherwise, if 24hour increment, update_book_stats
        if not round(hrs_since_start)%24:
            log('24 hr increment, updating book_stats.')
            update_book_stats(new_book=False)

        #set next book_check_timer
        hrs_til_24_start = hrs_since_start - 24*math.floor(hrs_since_start/24)
        hrs_til_24_access = hrs_since_access - 24*math.floor(hrs_since_access/24)
        next_hr = min(hrs_til_24_start, hrs_til_24_access)

        log('setting new book timeout for ' + str(next_hr) + ' hrs from now.')

        book_timeout = threading.Timer(next_hr*60*60, book_check_timeout)
        book_timeout.start()


def update_book_stats(new_book=True):
    #shift book stats from local to book, zero out, save
    #new to know if switching away from book; if so we consider current session
    #while sleeping done, otherwise we assume it will be added to next book_stats

    log('update book stat call')

    def clear_active():
        if sleep_timeout is not None: sleep_timeout.cancel()
        sleep_timeout = None
        sleeping = True
        pickup_timer = None
        log('sleeping...')
        epd_page.sleep()

    with b_lock:
        with s_lock:

            #update not_interested if we only see evidence of 1 <5 min session
            if (sum(book_data[s['book_id']]['pickups_per_interaction_day']) == 0) and \
                (s['current_pickups'] == 1) and sleeping and s['current_time_used'] < 5*60:
                book_data[s['book_id']]['not_interested'] = True

            pickups = s['current_pickups']
            time_used = s['current_time_used']
            page_views = s['current_pageviews']

            s['current_pickups'] = 0
            s['current_time_used'] = 0
            s['current_pageviews'] = 0

            #if newbook, kill sleep and count active session
            if not sleeping and new_book:
                time_used += (book_data[s['book_id']]['last_accessed'] - pickup_timer)
                clear_active()
            #if not newbook don't kill sleep and active session rolls over
            elif not sleeping and not new_book:
                s['current_pickups'] = 1
                pickups -= 1

            book_data[s['book_id']]['pickups_per_interaction_day'].append(pickups)
            book_data[s['book_id']]['time_per_interaction_day'].append(time_used)
            book_data[s['book_id']]['pages_per_interaction_day'].append(page_views)

            book_data[s['book_id']]['days_shown'] += 1
            if pickups > 0: book_data[s['book_id']]['days_interacted'] += 1

        #save updates to book_data
        cache_bookdata()


def render_title(title_text):
    for i in range(3): #3 tries with 5 sec timeout
        success = Command('ssh pi@raspberrypi.local \'./papirus-fill.py "' + title_text + '"\'').run(timeout=5)
        if success:
            log('successfully wrote to spine')
            return True
        else: log('failed to write spine. trying again...')
    return False


def render_cover(img):
    try:
        #render cover, infrequent enough to always sleep/wake
        epd_cover.init()
        epd_cover.display(epd_cover.getbuffer(img))
        epd_cover.sleep()
        log('successfully wrote to cover')
        return True
    except:
        log('failed to write to cover.')
        return False


def render_page(doc, page):
    try:
        assert not sleeping, 'Cannot write to sleeping page!'
        #render page
        img = get_page(doc, page)
        epd_page.display(epd_page.getbuffer(img))
        log('successfully wrote to page')
        return True
    except:
        log('failed to write to page.')
        return False


def page_turn(forward=True):
    #if the timer is currently running to timeout inactivity, cancel and restart now
    #call 'inactive_timeout' when inactive for 15 minutes from last action

    with b_lock:
        #cancel existing sleep timeouts
        if sleep_timeout is not None: sleep_timeout.cancel()

        log('page turn, forward=' + str(forward))

        #check if we're waking
        if sleeping:
            #waking means new pickup event
            with s_lock:
                sleeping = False
                s['pickups'] += 1
                pickup_timer = time.time()
            #wake display
            log('waking...')
            epd_page.init()

        #start sleep timeout
        sleep_timeout = threading.Timer(60*15, inactive_15min_timeout)
        sleep_timeout.start()

        #update last action
        book_data[s['book_index']]['last_accessed'] = time.time()

        #get current page and update
        new_page = book_data[s['book_index']]['current_page']
        if forward: new_page += 1
        else: new_page -= 1

        #check if completed book
        if new_page >= total_pages(s['doc']):
            log('book completed.')
            #update completed flag
            book_data[s['book_index']]['completed'] = True
            #reset book_timeout timer for 1hr
            if book_timeout is not None: book_timeout.cancel()
            book_timeout = threading.Timer(60*60, book_check_timeout)
            book_timeout.start()

        elif new_page >= 0: #prevent from backing past page 0
            log('page turned to ' + str(new_page))
            #updated page_views, current_page, render page
            render_page(s['doc'], new_page)
            s['current_pageviews'] += 1
            book_data[s['book_index']]['current_page'] = new_page

        #save updates to book_data
        cache_bookdata()



def open_book(id=None, title=None):

    log('open book called, id=' + str(id) + ' title=' + str(title))

    #match by either ID or title
    if id is None:
        for i, b in enumerate(book_data):
            if title.lower() in " ".join(b['title']):
                id = i
                break

    assert (id is not None), 'must have a book'
    book = book_data[id]

    #reset all timers/timeouts, state
    if sleep_timeout is not None: sleep_timeout.cancel()
    sleep_timeout = None
    if book_timeout is not None: book_timeout.cancel()

    with b_lock:
        #check if we have unresolved state (i.e we weren't sleeping) and resolve
        update_book_stats()

        book_timeout = threading.Timer(24*60*60, book_check_timeout)
        book_timeout.start()

        #STATE
        s['doc'] = load_doc(book['file'])
        s['book_id'] = id
        s['session_start'] = time.time()
        s['current_interest'] = False
        s['current_pickups'] = 0
        s['current_pageviews'] = 0
        s['current_time_used'] = 0

        #render page, cover, spine
        render_cover(book['cover_page'])
        render_title(book['title_print'])

        #rendering first page shouldn't start a session, so we'll do a little hack
        with s_lock:
            sleeping = False
            epd_page.init()
            render_page(s['doc'], book['current_page'])
            epd_page.sleep()
            sleeping = True


def open_random_book():
    log('open random book called')
    open_book(random.randint(len(book_data)))


def smart_choice_book(query=None):
    #if no query, if query

    #avoid not_interested books, boost interested books, strongly favor books
    #that have not been shown.  Query should dominate though.
    log('smart choice book called')
    open_random_book()


#buttons - short press forward, long press back ,really long press new random book

#open a random book
open_random_book()

#set up button
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#wait for button presses
while True:
    timer = 0
    input_state = GPIO.input(16)

    while not input_state:
        timer += 1
        input_state = GPIO.input(16)

    if timer:
        log('Button Pressed: ' + str(timer))
        if timer < 150000:
            log('trigger page turn forward')
            page_turn()
        elif timer < 400000:
            log('trigger page turn backward')
            page_turn(forward=False)
        else:
            log('trigger new book')
            open_random_book()

        timer=0
        time.sleep(0.1)

#150000 = long press
