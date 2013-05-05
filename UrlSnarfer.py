#!/usr/bin/env python
import re
import sys
import time
import string
import mechanize
import traceback
import MySQLdb
import getpass
import urllib2
from urllib import urlencode
from BeautifulSoup import BeautifulSoup
import gzip
from optparse import OptionParser
import HTMLParser


import VishnuBrowser
from config import *

ipAddressRegex = re.compile(r"^((((([0-9]{1,3})\.){3})([0-9]{1,3}))((\/[^\s]+)|))$")
urlRegex = re.compile(r"\s*(([\!\~\^]+)|)(((([\w\-]+\.)+)([\w\-]+))(((/[\w\-\.%\(\)~]*)+)+|\s+|[\!\?\.,;]+|$)|https?://[^\]>\s]*)")
selfRefRegex = re.compile(r"http://(www.|)ice-nine.org/(l|link.php)/([A-Za-z0-9]+)")
httpUrlRegex = re.compile(r"(https?://[^\]>\s]+)", re.I)
googleRegex = re.compile(r"^(\w*\s*\|\s*|)@google (.*)", re.I)

helpers = []
class UrlHelper(object):
    def __init__(self):
        self.clear_title = False
    def match(self, url, type):
        return False
    def fetch(self, snarfer, url, resp):
        return {'url': None,
                'title': None,
                'description': None };

class ImgUrUrlHelper(UrlHelper):
    def __init__(self):
        UrlHelper.__init__(self)
        self.clear_title = True
        self.url_regex = re.compile("imgur.com/(\S+)\....")

    def match(self, url):
        if self.url_regex.search(url):
            return True
        return False

    def fetch(self, snarfer, url, resp):
        m = self.url_regex.search(url)
        url = "http://imgur.com/gallery/%s" % (m.group(1))

        r = snarfer.open_url(url)
        title = snarfer.browser.title()
        if title is not None:
            title = " ".join(title.split())
        return {'description': title}

class TwitterUrlHelper(UrlHelper):
    def __init__(self):
        UrlHelper.__init__(self)
        self.clear_title = True
        self.url_regex = re.compile("twitter.com/.*/status")

    def match(self, url):
        if self.url_regex.search(url):
            return True
        return False

    def fetch(self, snarfer, url, resp):
        url = re.sub("/#!", "", url)
        url = re.sub("^https", "http", url)
        resp = snarfer.open_url(url)
        html = resp.read()
        s = BeautifulSoup(html)
        p = s.findAll('p', 'tweet-text')
        text = None
        if p:
            for part in p[0].contents:
                if text is None:
                    text = ""
                text += str(part)
            text = re.sub(r'<[^>]*?>', '', text)

        #print html

        p = s.findAll('strong', 'fullname')
        print p
        if p:
            name = p[0].contents[0]
        if text and name:
            desc = "%s: %s" % (str(name), text.strip()) 
            return {'description': desc}
        return None

class ReadabilityUrlHelper(UrlHelper):
    def __init__(self):
        UrlHelper.__init__(self)
        self.clear_title = True
        self.url_regex = re.compile("readability.com/articles/.*")

    def match(self, url):
        if self.url_regex.search(url):
            return True
        return False

    def fetch(self, snarfer, url, resp):
        url = re.sub("/#!", "", url)
        url = re.sub("^https", "http", url)
        resp = snarfer.open_url(url)
        html = resp.read()
        s = BeautifulSoup(html)

        links = s.findAll("link")

        for link in links:
            if link['rel'] == 'canonical':
                original = urllib2.urlopen(link['href']).read()
                sO = BeautifulSoup(original)

                return {'title': sO.title.string, 'url': link['href']}

        return None

class ShortUrlHelper(UrlHelper):
    def __init__(self):
        UrlHelper.__init__(self)
        self.clear_title = True

        domains = [ "bit\.ly",   # Bitly
                    "goo\.gl",   # Google
                    "kck\.st",   # Kickstarter
                    "sbn\.to"    # SBNation
                  ];

        self.url_regex = re.compile("(" + string.join(domains,"|") + ")/.*")

    def match(self, url):
        if self.url_regex.search(url):
            return True
        return False

    def fetch(self, snarfer, url, resp):
        url = re.sub("/#!", "", url)
        url = re.sub("^https", "http", url)

        target = urllib2.urlopen(url)
        targeturl = target.geturl()

        sO = BeautifulSoup(target.read())

        return {'title': sO.title.string, 'url': targeturl }


helpers.append(ImgUrUrlHelper())
helpers.append(TwitterUrlHelper())
helpers.append(ReadabilityUrlHelper())
helpers.append(ShortUrlHelper())

def find_url_helper(url):
    for helper in helpers:
        if helper.match(url) is True:
            return helper
    return None
        
class UrlDB(object):
    def __init__(self):
        return

    def get_by_url(self, url):
        return None
    def get_by_id(self, id):
        return None
    def increment_count(self, id):
        return None
    def add_url(self, url, user, title, nsfw, priv, type, desc):
        return None

class MysqlUrlDb(UrlDB):
    def __init__(self, host, db, user, passwd):
        self.host = host
        self.db = db
        self.user = user
        self.passwd = passwd
        try:
            self.sqlDb = MySQLdb.connect(db=db, user=user,
                             passwd=passwd, host=host, charset='utf8')
        except ImportError:
            raise callbacks.Error, 'You need python-mysql installed'
        except Exception, e:
            print e
            raise


    def reconnect(self):
        self.sqlDb = MySQLdb.connect(db=self.db, user=self.user,
                                     passwd=self.passwd, host=self.host, charset='utf8')

    def get_by_url(self, url):
        query  = """SELECT id, nick, count, UNIX_TIMESTAMP(first_seen), """
        query += """title, UNIX_TIMESTAMP(), alive, nsfw, private, type, description """
        query += """FROM url WHERE url = %s"""

        for i in [0, 1]:
            try:
                cursor = self.sqlDb.cursor()
                cursor.execute(query, [url])
            except MySQLdb.OperationalError, e:
                self.reconnect()
            except Exception, e:
                print "cursor.execute failed: " + str(e)
                raise
            else:
                break

        if cursor.rowcount == 0:
            return None
        elif cursor.rowcount == 1:
            row = cursor.fetchone()
        else:
            print "Rows %d" % cursor.rowcount
            raise Exception, "Invalid SQL Results"

        response = UrlSnarferResponse(url)
        response.id = row[0]
        response.user = row[1]
        response.count = int(row[2])
        response.timestamp = time.gmtime(row[3])
        response.title = row[4]
        response.request_timestamp = time.gmtime(row[5])
        response.alive = row[6]
        response.url = url
        response.nsfw = int(row[7])
        response.private = row[8]
        response.type = row[9]
        response.description = row[10]

        return response

    def get_by_id(self, id):
        query  = """SELECT url, nick, count, UNIX_TIMESTAMP(first_seen), """
        query += """title, UNIX_TIMESTAMP(), alive, nsfw, private, type, description """
        query += """FROM url WHERE id = %s"""

        for i in [0, 1]: 
            try: 
                cursor = self.sqlDb.cursor()
                cursor.execute(query, [id])
                if cursor.rowcount == 0:
                    return None
                elif cursor.rowcount == 1:
                    row = cursor.fetchone()
                else:
                    print "Rows %d" % cursor.rowcount
                    raise Exception, "Invalid SQL Results"
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

        response = UrlSnarferResponse(row[0])
        response.id = id
        response.user = row[1]
        response.count = int(row[2])
        response.timestamp = time.gmtime(row[3])
        response.title = row[4]
        response.request_timestamp = time.gmtime(row[5])
        response.alive = row[6]
        response.nsfw = int(row[7])
        response.private = row[8]
        response.type = row[9]
        response.description = row[10]

        return response

    def increment_count(self, id):
        query = """UPDATE url SET count = count + 1 WHERE id = %s"""

        id = int(id)

        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, id)
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def clear_url_title(self, urlno):
        query = """UPDATE url SET title = %s WHERE id = %s"""

        args = ['', urlno]

        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, args)
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def set_url_desc(self, urlno, desc):
        query = """UPDATE url SET description = %s WHERE id = %s"""

        args = [desc, urlno]

        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, args)
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def set_url_nsfw(self, urlno, nsfw):
        query = """UPDATE url SET nsfw = %s WHERE id = %s"""

        args = [nsfw, urlno]

        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, args)
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def set_url_type(self, urlno, type):
        query = """UPDATE url SET type = %s WHERE id = %s"""

        args = [type, urlno]

        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, args)
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break


    def set_url_dead(self, id):
        query = """UPDATE url SET alive = 0 WHERE id = %s"""
        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, [id])
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def set_url_alive(self, id):
        query = """UPDATE url SET alive = 1 WHERE id = %s"""
        for i in [0, 1]:
            try:
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, [id])
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def add_url(self, url, user, title, nsfw, priv, type, desc):
        args = [url, user, title, nsfw, priv]

        query  = """INSERT INTO url (url, nick, first_seen, """
        query += """title, nsfw, private"""
        if type is not None:
            query += ",type"
            args.append(type)
        if desc is not None:
            query += ",description"
            args.append(desc)
        
        query += """) VALUES(%s, %s, NOW(), %s, %s, %s"""
        if type is not None:
            query += """, %s"""
        if desc is not None:
            query += """, %s"""
        
        query += """)"""

        for i in [0, 1]:
            try: 
                db = self.sqlDb
                cursor = db.cursor()
                cursor.execute(query, args)
                db.commit()
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

    def close(self):
        self.sqlDb.close()

    def flush(self):
        self.sqlDb.commit()
        self.sqlDb.close()

#class HttpUrlDb(UrlDB):
#    def __init__(self, url):
#        self.server = url
#
#    def _get(self, url, response):
#        if self.snarfer is None:
#            raise "BUG: Snarfer must add itself"
#        (text, server_ts) = self.snarfer.getUrl(url)
#
#        lines = text.split('\n')
#        for line in lines:
#            if line == "NO MATCH":
#                return None
#
#        if response is not None:
#            response.id = int(lines[0])
#            response.user = lines[1]
#            response.count = int(lines[2])
#            response.timestamp = time.gmtime(int(lines[3]))
#            response.title = lines[4]
#            response.url = lines[5]
#            response.request_timestamp = server_ts
#
#        return response
#
#    def get_by_url(self, url, response):
#        response.url = url
#        safeurl = urlencode({ 'byurl' : '', 'url' : url })
#        return self._get(self.server + safeurl, response)
#
#
#    def get_by_id(self, id, response):
#        safeurl = urlencode({ 'byid' : "", 'id' : id })
#        return self._get(self.server + safeurl, response)
#
#    def increment_count(self, id):
#        safeurl = urlencode({ 'ping' : '', 'id' : id })
#        self._get(self.server + safeurl, None)
#
#    def add_url(self, url, user, title, nsfw=0, priv=False):
#        safeurl = urlencode({ 'add' : '', 'url' : url, 'nick' : user,
#                      'title' : title, 'nsfw' : nsfw, 'private' : priv})
#        self._get(self.server + safeurl, None)
#

# Some of these things need to be generalized...
class UrlSnarfer:
    def __init__(self, db):
        self.db = db
        db.snarfer = self
        self.browser = VishnuBrowser.VishnuBrowser()

    def url_to_id(id):
        map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
        num = 0
        base = 0
        for chr in id:
            val = map.index(chr)
            if base == 0:
                if val <= 0:
                    raise Exceptiom, "Out of range"
                base = val
            else:
                if val > base:
                    raise Exception, "Out of range(2)"
                val = map.index(chr)
                num *= base
                num += val
        return num
    url_to_id = staticmethod(url_to_id)

    def snarf(self, urlLine, user, update_count=True):
        interpolated = False

        match = googleRegex.match(urlLine)
        if match:
            terms = urlencode({'btnI' : "I'm Feeling Lucky", 'q': match.group(2)})
            urlLine = "http://www.google.com/search?hl=en&ie=ISO-8859-1&%s" % terms

        match = urlRegex.search(urlLine)
        if match is None:
            return None

        url = match.group(3)
        mods = match.group(1)

        private = False
        nsfw = 0
        if mods:
            if '!' in mods:
                nsfw = 2
            if '~' in mods:
                nsfw = 1
            if '^' in mods:
                private = True


        # URL without a protocol:// prefix
        if not httpUrlRegex.search(url):
            interpolated = True

            if re.search(r"^(([0-9]+)\.)+(|[0-9]+)$", url):
                m = ipAddressRegex.search(url)
                if not m:
                    return None

                ip = m.group(2)
                array = ip.split('.', 4)
                if int(array[0]) == 0:
                    return None

                for num in array:
                    if (int(num) >= 255):
                        return None

            url = "http://" + url

        # URL referencing the published short link
        m = selfRefRegex.search(url)
        if m is not None:
            id = UrlSnarfer.url_to_id(m.group(3))
            try:
                response = self.db.get_by_id(id)
                if response is None:
                    raise "*** No match for ID %d" % id
                self.db.increment_count(id)
                response.count += 1
            except Exception, e:
                raise
            return response

        try:
            response = self.fetch_and_add_url(url, user, nsfw, private,
                                              update_count)
            if response is None:
                raise Exception("*** %s: %s" % (url, str(e)))
        except urllib2.URLError, e:
            if not interpolated:
                raise Exception("*** %s: %s" % (url, str(e)))
            else:
                return None
        except Exception, e:
            if not interpolated:
                print traceback.print_exc(file=sys.stdout)
                raise Exception, url + ': ' + str(e)
            return None

        return response

    def get_type(self):
        try:
            type = None
            info = self.browser.response().info()
            if 'Content-type' in info:
                type = info['Content-type']
            else:
                print "No Content-type"

            return type

        except Exception, e:
            print str(e)

    def clear_title(self, url):
        h = find_url_helper(url)
        return h and h.clear_title

    def get_description(self, url, resp):
        description = None

        type = self.get_type()

        h = find_url_helper(url)
        if h is not None:
            print "Using %s" % str(h)

            result = h.fetch(self, url, resp)
    
            if result and 'description' in result:
                return result['description']
            else:
                return None
        if 'html' not in type:
            return None

        try:
            html = resp.read()
            s = BeautifulSoup(html)
            meta = s.findAll('meta')
            for tag in meta:
                desc = False
                for attr in tag.attrs:
                    if attr[0].lower() == 'property' and attr[1].lower() == 'og:description':
                        desc = True
                    if attr[0].lower() == 'name' and attr[1].lower() == 'description':
                        desc = True
                    if attr[0].lower() == 'content':
                        content = attr[1]
                    if desc:
                        description = content
        except Exception, e:
            print "EXCEPTION: %s" % str(e)

        return description

    def get_url(self, url, resp):
        h = find_url_helper(url)

        if h is not None:
            result = h.fetch(self, url, resp)
    
            if result and 'url' in result:
                return result['url']
            else:
                return None

        return None

    def get_title(self, url, resp):
        h = find_url_helper(url)

        if h is not None:
            result = h.fetch(self, url, resp)
    
            if result and 'title' in result:
                return result['title']
            else:
                return None

        return None

    def open_url(self, url):
        r = self.browser.open(url)
        try:
            headers = r.info()
            if 'Content-Encoding' in headers:
                if headers['Content-Encoding'] == 'gzip':
                    gz = gzip.GzipFile(fileobj = r, mode = 'rb')
                    html = gz.read()
                    gz.close()
                    headers['Content-Type'] = 'text/html; charset=utf-8'
                    r.set_data(html)
                    self.browser.set_response(r)
        except Exception, e:
            print e.__class__.__name__
            print e

        return r;

    def ping_url(self, url, response, nsfw, update_count=True):
        if update_count:
            response.count += 1
            self.db.increment_count(response.id)
        try:
            r = self.open_url(url)
            if not response.alive:
                response.alive = 1
                try:
                    self.db.set_url_alive(response.id)
                except Exception, e:
                    print "Failed to mark link alive."
            if response.type is None:
                type = self.get_type()
                self.db.set_url_type(response.id, type)
                response.type = type
            else:
                type = response.type

            if response.nsfw < nsfw:
                response.nsfw = nsfw
                self.db.set_url_nsfw(response.id, nsfw)

            if response.description == "" or response.description == None:
                print "Updating description"
                desc = self.get_description(url, r)
                if desc:
                    self.db.set_url_desc(response.id, desc)
                    if self.clear_title(url):
                        self.db.clear_url_title(response.id)
                    response.description = desc
            else:
                print response.description

        except urllib2.HTTPError, e:
            raise e
        except UnicodeDecodeError, e:
            print "UnicodeDecodeError: " + str(e)
            pass
        except Exception, e:
            print "EX %s" % str(e)
            print e.__class__.__name__
            response.alive = 0
            try:
                self.db.set_url_dead(response.id)
            except Exception, e:
                print "Failed to mark link dead: %s" % str(e)

    def fetch_and_add_url(self, url, user, nsfw, private, update_count=True):
        desc = None
        type = None
        try:
            response = self.db.get_by_url(url)
        except Exception, e:
            response = None

        if response is not None:
            self.ping_url(url, response, nsfw, update_count)
            return response

        try:
            r = self.open_url(url)
            self.browser.cj.save('cookies.txt')

            title = self.browser.title()
            if title is not None:
                title = " ".join(title.split())

        except urllib2.URLError, e:
            raise e
        except mechanize.BrowserStateError, e:
            title = ""
        except urllib2.HTTPError, e:
            print "Exception HTTPError " + str(e)
            title = ""
        except HTMLParser.HTMLParseError, e:
            title = ""

        type = self.get_type()
        desc = self.get_description(url, r)
        newUrl = self.get_url(url, r)
        newTitle = self.get_title(url, r)

        if newUrl is not None:
            url = newUrl

            # check if the unobfuscated url has already been recorded
            try:
                response = self.db.get_by_url(url)
            except Exception, e:
                response = None

            if response is not None:
                self.ping_url(url, response, nsfw, update_count)
                return response

        if newTitle is not None:
            title = newTitle

        if self.clear_title(url):
            title = None

        if title is None:
            title = ""

        self.db.add_url(url, user, title, nsfw, private, type, desc)
        response = self.db.get_by_url(url)
        if response is None:
            raise Exception, "Failed to add new entry"

        return response

    def getUrl(self, url):
        r = self.open_url(url)
        now = r.info().getdate("Date")[0:8] + (-1,)
        now = time.localtime(time.mktime(now))
        return (r.read(), now)

class UrlSnarferResponse:
    def __init__(self, user):
        self.url = None
        self.nsfw = 0
        self.private = False
        self.id = None
        self.count = None
        self.timestamp = None
        self.title = None
        self.first_seen = None
        self.request_timestamp = None
        self.urlLine = None
        self.user = user
        self.type = None
        self.description = None

    def shorturl(self):
        map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
        out = ""
        id = self.id
        base = id % 34 + 26
        while id > 0:
            index = id % base
            out = map[index] + out
            id = id / base

        out = map[base] + out
        return "http://ice-nine.org/l/" + out

    def timeAgo(self):
        ago = ""

        now_tm = self.request_timestamp
        then_tm = self.timestamp

        seconds = now_tm.tm_sec - then_tm.tm_sec
        minutes = now_tm.tm_min - then_tm.tm_min
        hours   = now_tm.tm_hour - then_tm.tm_hour
        days    = now_tm.tm_mday - then_tm.tm_mday
        months  = now_tm.tm_mon  - then_tm.tm_mon
        years   = now_tm.tm_year - then_tm.tm_year

        # We want all positives, so lets make it go
        if seconds < 0:
            seconds += 60
            minutes -= 1

        if minutes < 0:
            minutes += 60
            hours -= 1

        if hours < 0:
            hours += 24
            days -= 1

        if days < 0:
            if now_tm.tm_mon == 4 or now_tm.tm_mon == 6 or \
               now_tm.tm_mon == 9 or now_tm.tm_mon == 11:
                days += 30
            elif now_tm.tm_mon == 2:
                if now_tm.tm_year % 4 == 0 and \
                   now_tm.tm_year % 100 != 0:
                    days += 29
                else:
                    days += 28
            else:
                days += 31
            months -= 1

        if months < 0:
            months += 12
            years -= 1

        if years > 0:
            hours = minutes = seconds = 0
            ago = str(years) + "y"

        if months > 0:
            hours = minutes = seconds = 0
            if ago != "":
                ago += ", "
            ago += str(months) + "m"

        if days > 0:
            minutes = seconds = 0
            if ago != "":
                ago += ", "
            ago += str(days) + "d"

        if hours > 0:
            seconds = 0
            if ago != "":
                ago += ", "
            ago += str(hours) + "h"

        if minutes > 0:
            if ago != "":
                ago += ", "
            ago += str(minutes) + "m"

        if seconds > 0:
            if ago != "":
                ago += ", "
            ago += str(seconds) + "s"
        else:
            if ago == "":
                ago = "0s"
            ago += " ago"

        return ago

    def tostring(self, with_description=True):
        desc = ""
        if self.title:
            desc += '(' + self.title.replace("\n", "") + ')'
        if self.count > 1:
            if desc != "":
                desc += " "
            alive = ""
            if not self.alive:
                alive = " DEAD"
            desc += "[%dx, %s, %s%s] " % (self.count,
                                          self.user,
                                          self.timeAgo(),
                                          alive)
        str = self.shorturl()
        if with_description:
            str += "\n" + desc
        return str

    def pretty_title(self):
        title = self.title
        if title is None:
            title = ""
        else:
            title += ""
        if self.nsfw > 0 or self.private:
            title += "("
            
            if self.nsfw == 2:
                title += "NSFW"
            elif self.nsfw == 1:
                title += "~NSFW"
            elif self.nsfw != 0:
                title += "?NSFW"

            if self.private:
                if self.nsfw > 0:
                    title += ","
                title += "P"

            title += ")"
        return title

    def __str__(self):
        return self.tostring(True)

if __name__ != '__main__':
    from PlayerPlugin import PlayerPlugin
    class UrlSnarferPlugin(PlayerPlugin, UrlSnarfer):
        def __init__(self): 
            PlayerPlugin.__init__(self)
            self.db = MysqlUrlDb(db_host, db_name, db_user, db_pass)
            UrlSnarfer.__init__(self, self.db)

        def die(self):
            self.db.close()

        def start(self):
            self.map("StageTalkEvent")
            self.map("GeneralEvent")
            self.map("TalkEvent")

        def react(self, event):
            msg = event.message
        
            if event.from_who != "vishnu":
                try:
                    response = self.snarf(msg, event.from_who)
                except Exception, e:
                    self.say(event, str(e))
                    raise
                    
                if not response:
                    return

                desc = ""
                title = response.pretty_title()
                if title:
                    desc = '(' + title.replace("\n", "") + ')'
                elif response.description:
                    desc = '(' + response.description.replace("\n", "") + ')'
                if response.count > 1:
                    if desc != "":
                        desc += " "
                    alive = ""
                    if not response.alive:
                        alive = " DEAD"
                    desc += "[%dx, %s, %s%s] " % (response.count,
                                                  response.user,
                                                  response.timeAgo(),
                                                  alive)
                self.link(event, response.url, response.shorturl(), desc)

        def link(self, event, url, shorturl, description):
            self.say(event, shorturl)
            if description is not None and description != "":
                self.say(event, description)
            event.socket.command(";#212:_fromVishnu(\"" + url + "\")")

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-u", "--update", action="store_true", default=False)
    parser.add_option("-n", "--count", action="store", default=10)

    (options, urls) = parser.parse_args()

    user = getpass.getuser()
    db = MysqlUrlDb(db_host, db_name, db_user, db_pass)
    u = UrlSnarfer(db)

    if options.update:
        print "Update mode"
        q = "SELECT id, url FROM url ORDER BY id DESC LIMIT 0, %s" % (options.count)
#        q = "select * from url where url LIKE '%%imgur%%' ORDER BY ID DESC LIMIT 0,30"
        cursor = db.sqlDb.cursor()
        cursor.execute(q)

        for row in cursor.fetchall():
            print row
            id = row[0]
            url = row[1]
            resp = u.db.get_by_id(id)
            u.ping_url(url, resp, False)

        print "Done."

        sys.exit(0)

    default_url = "http://www.google.com/"
    if len(urls) == 0:
        print "No URL specified, testing with " + default_url
        urls = [default_url]

    for arg in urls:
        url = None
        print "Trying " + arg
        try:
            response = u.snarf(arg, user, False)
            print response
        except Exception, e:
            print e

# vim: ts=4 sw=4 et
