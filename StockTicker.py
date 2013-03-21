#!/usr/bin/env python

import re
import sys
import time
import mechanize
import csv
import urllib
from urllib import *
import urllib2
import mtgox

import VishnuBrowser


fieldmap = {
    "a"  : "Ask",
    "b"  : "Bid",
    "b4" : "Book Value",
    "c1" : "Change",
    "c8" : "After Hours Change (Real-time)",
    "d2" : "Trade Date",
    "e7" : "EPS Estimate Current Year",
    "f6" : "Float Shares",
    "j"  : "52-week Low",
    "g3" : "Annualized Gain",
    "g6" : "Holdings Gain (Real-time)",
    "j1" : "Market Capitalization",
    "j5" : "Change From 52-week Low",
    "k2" : "Change Percent (Real-time)",
    "k5" : "Percebt Change From 52-week High",
    "l2" : "High Limit",
    "m2" : "Day's Range (Real-time)",
    "m5" : "Change From 200-day Moving Average",
    "m8" : "Percent Change From 50-day Moving Average",
    "o"  : "Open",
    "p2" : "Change in Percent",
    "q"  : "Ex-Dividend Date",
    "r2" : "P/E Ratio (Real-time)",
    "r7" : "Price/EPS Estimate Next Year",
    "s7" : "Short Ratio",
    "t7" : "Ticker Trend",
    "v1" : "Holdings Value",
    "w1" : "Day's Value Change",
    "y"  : "Dividend Yield",
    "a2" : "Average Daily Volume",
    "b2" : "Ask (Real-time)",
    "b6" : "Bid Size",
    "c3" : "Commission",
    "d"  : "Dividend/Share",
    "e"  : "Earnings/Share",
    "e8" : "EPS Estimate Next Year",
    "g"  : "Day's Low",
    "k"  : "52-week High",
    "g4" : "Holdings Gain",
    "i"  : "More Info",
    "j3" : "Market Cap (Real-time)",
    "j6" : "Percent Change From 52-week Low",
    "k3" : "Last Trade Size",
    "l"  : "Last Trade (With Time)",
    "l3" : "Low Limit",
    "m3" : "50-day Moving Average",
    "m6" : "Percent Change From 200-day Moving Average",
    "n"  : "Name",
    "p"  : "Previous Close",
    "p5" : "Price/Sales",
    "r"  : "P/E Ratio",
    "r5" : "PEG Ratio",
    "s"  : "Symbol",
    "t1" : "Last Trade Time",
    "t8" : "1 yr Target Price",
    "v7" : "Holdings Value (Real-time)",
    "w4" : "Day's Value Change (Real-time)",
    "a5" : "Ask Size",
    "b3" : "Bid (Real-time)",
    "c"  : "Change & Percent Change",
    "c6" : "Change (Real-time)",
    "d1" : "Last Trade Date",
    "e1" : "Error Indication (returned for symbol changed / invalid)",
    "e9" : "EPS Estimate Next Quarter",
    "h"  : "Days High",
    "g1" : "Holdings Gain Percent",
    "g5" : "Holdings Gain Percent (Real-time)",
    "i5" : "Order Book (Real-time)",
    "j4" : "EBITDA",
    "k1" : "Last Trade (Real-time) With Time",
    "k4" : "Change From 52-week High",
    "l1" : "Last Trade (Price Only)",
    "m"  : "Day's Range",
    "m4" : "200-day Moving Average",
    "m7" : "Change From 50-day Moving Average",
    "n4" : "Notes",
    "p1" : "Price Paid",
    "p6" : "Price/Book",
    "r1" : "Dividend Pay Date",
    "r6" : "Price/EPS Estimate Current Year",
    "s1" : "Shares Owned",
    "t6" : "Trade Links",
    "v"  : "Volume",
    "w"  : "52-week Range",
    "x"  : "Stock Exchange",
}

revmap = {}
for key in fieldmap:
    revmap[fieldmap[key]] = key

class StockTicker:
    baseurl = "http://quote.yahoo.com/d/quotes.csv"
    # name, current price, change in price, change in pct
    defattrs = "nl1c6p2rj1"
    def __init__(self):
        self.browser = VishnuBrowser.VishnuBrowser()
    
    def get_sym(self, event, sym, attrs=defattrs):
        attrmap = []
        short = True

        # If the caller sent a list of names instead of a formatted
        # string, split it out
        if isinstance(attrs, list):
            short = False
            a = ""
            for attr in attrs:
                a += revmap[attr]
                attrmap.append(revmap[attr])
            attrs = a
        else:
            attr = attrs
            while attr != "":
                m = re.match("([a-z][0-9]?)", attr) 
                if m:
                    attrmap.append(m.group(1))
                    attr = re.sub(m.group(1), "", attr)

        opts = urllib.urlencode( { 's' : sym, 'f' : 's' + attrs } )
        try:
            f = self.browser.open(self.baseurl + "?" + opts)
        except mechanize.BrowserStateError, e:
            self.say(event, "Error: %s" % str(e))
        except urllib2.URLError, e:
            self.say(event, "Error: %s" % str(e))

        reader = csv.reader(f)

        response = {}

        try:
            for row in reader:
                sym = row[0]
                i = 0
                for val in row[1:]:
                    attr = attrmap[i]
                    if short:
                        response[attr] = val
                    else:
                        response[fieldmap[attr]] = val
                    i += 1

                response['array'] = row[1:]

                
        except csv.Error, e:
            raise

        return response

if __name__ != '__main__':
    from PlayerPlugin import PlayerPlugin
    class StockTickerPlugin(PlayerPlugin, StockTicker):
        def __init__(self):
            PlayerPlugin.__init__(self)
            StockTicker.__init__(self)

        def start(self):
            self.map("StageTalkEvent")
            self.map("GeneralEvent")
            self.map("TalkEvent")

        #>>> pprint.pprint(mtgox.ticker())
        #{u'avg': {u'display_short': u'$61.91', u'value_int': 6190703},
        #u'buy': {u'display_short': u'$63.00', u'value_int': 6300100},
        #u'high': {u'display_short': u'$66.00', u'value_int': 6600000},
        #u'last': {u'display_short': u'$63.70', u'value_int': 6370003},
        #u'last_all': {u'display_short': u'$63.70', u'value_int': 6370003},
        #u'last_local': {u'display_short': u'$63.70', u'value_int': 6370003},
        #u'last_orig': {u'display_short': u'$63.70', u'value_int': 6370003},
        #u'low': {u'display_short': u'$57.70', u'value_int': 5770200},
        #u'now': u'1363823793330687',
        #u'sell': {u'display_short': u'$63.70', u'value_int': 6370003},
        #u'vol': {u'display_short': u'92,207.23\xa0BTC', u'value_int': 9220723363798L},
        #u'vwap': {u'display_short': u'$61.99', u'value_int': 6198618}}

        def mtgox_ticker(self):
            now = time.localtime(time.time())
            open = int(time.mktime((now[0], now[1], now[2],
                                    0, 0, 0,
                                    now[6], now[7], now[8])))
            res = mtgox._specific('trades?since=%d000000' % open, 'USD')
            opening_price = res[0]['price_int']

            ticker = mtgox.ticker()
            current_value = ticker['last_all']['value_int']
            change = current_value - opening_price
            percentage = change / float(ticker['last_all']['value_int'])

            sym = {
                'n' : "MT.GOX",
                'l1' : "%.02f" % (float(current_value) / 100000),
                'c6' : "%+.02f" % (float(change) / 100000),
                'p2' : "%+.02f%%" % (percentage * 100)
            }
            return sym

        def react(self, event):
            msg = event.message

            if event.__class__.__name__ == "GeneralEvent":
                msg = re.sub("^[^\|]+\|\s+", "", msg)

            if event.from_who == "vishnu":
                return

            m = re.match("ticker (\S+)", msg)
            if not m:
                return

            if m.group(1).upper() == "OHGOD":
                sym = {
                    'n' : "GoonSwarm",
                    'l1' : "OH GOD BEES!",
                    'c6' : "1",
                    'p2' : '100%'
                }
            elif m.group(1).upper() == "XCOM":
                sym = {
                    'n' : "XCOM",
                    'l1' : "XCOM",
                    'c6' : "1",
                    'p2' : "JOY/PAIN=100%?"
                }
            elif m.group(1).upper() == "MTGOX":
                sym = self.mtgox_ticker()
            else:
                sym = self.get_sym(event, m.group(1))

            print m.group(1).upper()
            change = float(sym['c6'])
            color = ""

            if change == 0:
                color = ""
            elif change > 0:
                color = "\\\\g"
            else:
                color = "\\\\r"

            if sym['p2'] != "N/A":
                msg = "%s%s: " % (color, sym['n'])
                msg += "%s (%s %s" % (sym['l1'], sym['c6'], sym['p2'])
                if 'r' in sym and sym['r'] != "N/A":
                    msg += " P/E %s" % sym['r']
                if 'j1' in sym and sym['j1'] != "N/A":
                    msg += " Cap %s" % sym['j1']
                msg += ")"
                self.say(event, msg)
            else:
                self.social(event, "moon", event.from_who, "Invalid symbol %s" % sym['n'])


if __name__ == '__main__':
    st = StockTicker()

    sym = 'FB'
    if len(sys.argv) > 1:
        sym = sys.argv[1]

    resp = st.get_sym(None, sym)
    print resp
    if resp['p2'] != "N/A":
        msg = "%s: " % (resp['n'])
        msg += "%s (%s %s" % (resp['l1'], resp['c6'], resp['p2'])
        if 'r' in resp and resp['r'] != "N/A":
            msg += " P/E %s" % resp['r']
        if 'j1' in resp and resp['j1'] != "N/A":
            msg += " Cap %s" % resp['j1']
        msg += ")"
        print msg
    else:
        print "Invalid symbol %s" % sym

# vim: ts=4 sw=4 et
