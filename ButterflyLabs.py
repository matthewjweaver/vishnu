#!/usr/bin/env python

import re
import mechanize
import VishnuBrowser
import urllib2
from bs4 import BeautifulSoup

class ButterflyLabs:
    url = "https://forums.butterflylabs.com/blogs/bfl_jody/"
    def __init__(self):
        self.browser = VishnuBrowser.VishnuBrowser()

    def parse(self, html):
        s = BeautifulSoup(html)

        lines = []
        try:
            p = s.find('a', 'blogtitle').contents
            if p:
                lines.append(p[0])
        except Exception, e:
            pass

        p = s.find('blockquote', "blogcontent")

        x = re.sub("\n", "", str(p))
        x = re.sub("<br */*>", "\n", x)

        for item in x.split('\n'):
            line = re.sub("</*[^>]+>", "", str(item)).strip()
            m = re.search("^(Jalapeno|Little Single|Single)", line)
            if m:
                lines.append(line)
        return lines

    def fetch(self):
        f = self.browser.open(self.url)
#        f = open('input')

        html = f.read()
        return self.parse(html)


if __name__ != '__main__':
    from PlayerPlugin import PlayerPlugin
    class ButterflyLabsPlugin(PlayerPlugin, ButterflyLabs):
        def __init__(self):
            PlayerPlugin.__init__(self)
            ButterflyLabs.__init__(self)

        def start(self):
            self.map("StageTalkEvent")

        def react(self, event):
            msg = event.message
            if event.to_who == 'vishnu' and msg == "bfl":
                try:
                    for line in self.fetch():
                        self.say(event, line)
                except mechanize.BrowserStateError, e:
                    self.say(event, "Browser error: %s" % str(e))
                except urllib2.URLError, e:
                    self.say(event, "URL error: %s" % str(e))
else:
    b = ButterflyLabs()
    res = b.fetch()
    print res

# vim: ts=4 sw=4 et
