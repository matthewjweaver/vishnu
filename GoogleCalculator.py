#!/usr/bin/env python
# vim: ts=4 sw=4 et

import VishnuBrowser
from urllib import urlencode
import sys

url = r"https://www.google.com/ig/calculator?%s"

class GoogleCalculator:
    def __init__(self, browser):
        self.browser = browser

    def solve(self, expression):
        terms = urlencode({"hl": "en", "q": expression})
        f = self.browser.open(url % terms)
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

if __name__ == '__main__':
    browser = VishnuBrowser.VishnuBrowser()
    gcalc = GoogleCalculator(browser)

    for expression in sys.argv[1:]:
        print gcalc.solve(expression)
