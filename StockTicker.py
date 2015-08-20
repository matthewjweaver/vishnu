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
import MLBTicker
import NFLTicker
from campbx import CampBX
import simplejson as json

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
    defattrs = "nl1c6p2rj1r6e7"
    def __init__(self):
        self.browser = VishnuBrowser.VishnuBrowser()
        self.mlb = MLBTicker.MLBTicker(self.browser)
        self.nfl = NFLTicker.NFLTicker(self.browser)

        # Rate limit to once every 15 mins
        self.last_cbxusd_market_query_ts = 0
        self.last_cbxusd_market_query = None
    
    def get_sym(self, sym, attrs=defattrs):
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
                    attr = attr[len(m.group(1)):]
                else:
                    break

        opts = urllib.urlencode( { 's' : sym, 'f' : 's' + attrs } )
        f = self.browser.open(self.baseurl + "?" + opts)
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

    def get_ticker(self, symbol):
        symbol = symbol.upper()
        if symbol == "OHGOD":
            sym = {
                'n' : "GoonSwarm",
                'l1' : "OH GOD BEES!",
                'c6' : "1",
                'p2' : '100%'
            }
        elif symbol == "XCOM":
            sym = {
                'n' : "XCOM",
                'l1' : "XCOM",
                'c6' : "1",
                'p2' : "JOY/PAIN=100%?"
            }
        elif symbol == "MTGOX":
            sym = self.mtgox_ticker()
        elif symbol == "CAMPBX":
            sym = self.campbx_ticker()
        elif symbol[0:4] == "MLB.":
            return self.mlb.get_ticker(symbol[4:])
        elif symbol == "SOX":
            return self.mlb.get_ticker("BOS")
        elif symbol[0:4] == "NFL.":
            return self.nfl.get_ticker(symbol[4:])
        elif symbol == "PATS":
            return self.nfl.get_ticker("NE")
        else:
            sym = self.get_sym(symbol)

        try:
            value = float(sym['l1'])
            pct = float(sym['p2'].strip('%')) / 100
        except ValueError, e:
            return None

        try:
            change = float(sym['c6'])
        except ValueError:
            change = value - (value / (1+pct))
        color = ""

        if change == 0:
            color = ""
        elif change > 0:
            color = "\\\\g"
        else:
            color = "\\\\r"

        c = '\0'
        if change > 0:
            c = '+'

        pe = None
        cap = None
        btc = None
        if 'r' in sym and sym['r'] != "N/A":
            pe = float(sym['r'])
        if 'j1' in sym and sym['j1'] != "N/A":
            cap = sym['j1']
        if 'btc' in sym:
            btc = sym['btc']

        rate = 100
        if symbol[-2:] == ".L":
            exch = self.get_sym("GBPUSD=X")
            rate = float(exch['l1'])
            value *= rate / 100
            change *= rate / 100
            newcap = float(cap[:-1]) * rate
            unit = cap[:-1]
            cap = "%.2f%s" % (newcap, cap[-1:])
            pe = None

        msg = "%s%s: " % (color, sym['n'])
        msg += "%.2f (%c%.2f %c%.2f%%" % (value, c, change, c, pct *100)
        if pe is not None:
            msg += " P/E %.2f" % pe
        if cap is not None:
            msg += " Cap %s" % cap
        if btc is not None:
            msg += " Volume %s" % btc
        msg += ")"

        return msg

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
            'p2' : "%+.02f%%" % (percentage * 100),
            'btc' : ticker['vol']['display_short']
        }
        return sym

    def campbx_ticker(self):
        c = CampBX()

        t = c.xticker()

        now = time.localtime(time.time())
        open = int(time.mktime((now[0], now[1], now[2],
                                0, 0, 0,
                                now[6], now[7], now[8])))
        now = time.time()

        url = "http://api.bitcoincharts.com/v1/trades.csv?symbol=cbxUSD&start=%d" % open
        r = self.browser.open(url)
        opening_price = float(r.readlines()[0].split(',')[1])
        current_value = float(t['Last Trade'])

        change = current_value - opening_price
        percentage = change / current_value

        if self.last_cbxusd_market_query is None or \
           now - self.last_cbxusd_market_query_ts > 15*60*60:
            url = "http://api.bitcoincharts.com/v1/markets.json"
            r = self.browser.open(url)
            js = json.loads(r.read())
            for market in js:
                if market['symbol'].upper() == 'CBXUSD':
                    self.last_cbxusd_market_query = market
                    self.last_cbxusd_market_query_ts = now
                    break

        volume = "(unknown)"
        if self.last_cbxusd_market_query is not None:
            v = float(self.last_cbxusd_market_query['volume'])
            volume = "%.2f BTC" % v
        
        sym = {
            'n' : 'CAMPBX',
            'l1' : "%.02f" % current_value,
            'c6' : "%+.02f" % change,
            'p2' : "%+.02f%%" % (percentage * 100),
            'btc' : volume,
        }
        return sym


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

        def react(self, event):
            msg = event.message

            if event.__class__.__name__ == "GeneralEvent":
                msg = re.sub("^[^\|]+\|\s+", "", msg)

            if event.from_who == "vishnu":
                return

            m = re.match("\s*ticker (\S+)", msg)
            if not m:
                return

            try:
                msg = self.get_ticker(m.group(1))
            except urllib2.URLError, e:
                self.say(event, "\"%s\" error: %s" % (msg, str(e)))
            except mechanize.BrowserStateError, e:
                self.say(event, "Error: %s" % str(e))
            except Exception, e:
                self.say(event, "Exception: %s" % str(e))

            if msg:
                self.say(event, msg)
            else:
                self.social(event, "moon", event.from_who, \
                            "Invalid symbol %s" % m.group(1))

if __name__ == '__main__':
    st = StockTicker()

    args = [ 'FB' ]
    if len(sys.argv) > 1:
        args = sys.argv[1:]

    for sym in args:
        print st.get_ticker(sym)

# vim: ts=4 sw=4 et
