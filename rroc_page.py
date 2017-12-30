# coding: utf-8

import requests
import json
import threading
import atexit
import siproll.siproll as siproll
from flask import Flask, request, redirect, url_for, render_template, g

blocked_numbers = []
POOL_TIME = 5
CALL_TIMEOUT = 30

callQueue = []
dataLock = threading.Lock()
callThread = threading.Thread()

app = Flask(__name__) 

def interrupt():
    global callThread
    callThread.cancel()

def doCall():
    global callThread
    with dataLock:
        #do stuff
        if len(callQueue) > 0:
            numberToCall = callQueue.pop(0)
            print "Rolling the number: %i" % numberToCall
            siproll.do_call('sip:%i@voip.eventphone.de' % numberToCall, CALL_TIMEOUT)
        else:
            print "No numbers in Queue, idling a bit..."
        
    callThread = threading.Timer(POOL_TIME, doCall, ())
    callThread.start()

def initDoCall():
    callThread = threading.Timer(POOL_TIME, doCall, ())
    callThread.start()
    
initDoCall()
atexit.register(interrupt)

@app.errorhandler(Exception)
def unhandled_exception(exception):
    with open('queue_save.json', 'w') as qs:
        global callQueue
        qs.write(json.dumps(callQueue))

#########
# req ctx

@app.route('/')
def index():
    return render_template('present.html', numbers=[])

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    print query
    if not query:
        return render_template('present.html', numbers=[])
    return lookup(query)

def lookup(query):
    params = {
        'event': '34C3',
        's': query,
        'installedonly': 1,
        'format': 'json'
    }
    r = requests.get('https://eventphone.de/guru2/phonebook', params=params)
    return render_template('present.html', numbers=r.json())

@app.route('/call/<number>', methods=['GET'])
def call(number):
    # well we better not call important numbers...
    if not len(number) == 4: return 'only 4 digits pls'

    def try_parse_int(s, base=10, val=None):
        try:
            return int(s, base)
        except ValueError:
            return val

    n = try_parse_int(number)
    if not n: return 'only numeric pls'
    if n < 2000: return 'dont fuck with important numbers'
    if n in blocked_numbers: return 'sorry, this number is blacklisted'

    if not n in callQueue:
        callQueue.append(n)
    place = callQueue.index(n)
    return render_template('queued.html', target=n, place=place)

