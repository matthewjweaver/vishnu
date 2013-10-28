#!/usr/bin/env python
# vim: ts=4 sw=4 et

import VishnuBrowser
import mechanize
import re
import sys
import urllib2


class GoogleCalculator:
    url = r"https://www.google.com/ig/calculator?%s"
    def __init__(self):
        self.browser = VishnuBrowser.VishnuBrowser()

    def solve(self, expression):
        terms = urllib2.urlencode({"hl": "en", "q": expression})
        f = self.browser.open(self.url % terms)
        result = f.read()
        parsed_result = {}
        # Google doesn't return valid JSON (THANKS OBAMA); they don't quote the keys.
        # A result looks like: {lhs: "(24 / 6) * 8",rhs: "32",error: "",icc: false}
        # remove the braces and split on the ,
        for kvpair in result[1:-1].split(","):
            key, value = kvpair.split(':')
            # remove the leading space and the quotes
            parsed_result[key] = value[2:-1]

        if parsed_result["error"] != "":
            return "I have a solution for " + expression + ", but it is too large to fit here."

        return parsed_result["lhs"] + " = " + parsed_result["rhs"]

if __name__ != '__main__':
    from PlayerPlugin import PlayerPlugin
    class GoogleCalculatorPlugin(PlayerPlugin, GoogleCalculator):
        def __init__(self):
            PlayerPlugin.__init__(self)
            GoogleCalculator.__init__(self)

        def start(self):
            self.map("StageTalkEvent")

        def react(self, event):
            msg = event.message

            if event.__class__.__name__ == "GeneralEvent":
                msg = re.sub("^[^\|]+\|\s+", "", msg)

            if event.to_who == 'vishnu' and msg == "calc":
                try:
                    self.solve(msg)
                except urllib2.URLError, e:
                    self.say(event, "\"%s\" error: %s" % (msg, str(e)))
                except mechanize.BrowserStateError, e:
                    self.say(event, "Error: %s" % str(e))
                except Exception, e:
                    self.say(event, "Exception: %s" % str(e))
            if msg:
                self.say(event, msg)
            else:
                self.social(event, "moon", event.from_who, "Couldn't compute %s" % msg)

if __name__ == '__main__':
    gcalc = GoogleCalculator() 
    for expression in sys.argv[1:]:
        print gcalc.solve(expression)
