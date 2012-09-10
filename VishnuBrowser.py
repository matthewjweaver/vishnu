#!/usr/bin/env python
import mechanize
import config
import socket

# This is a singleton browser implementation

class VishnuBrowser:
    __instance = None

    def __init__(self, cookiejar=config.cookiejar, passwords=config.passwords):
        if VishnuBrowser.__instance is None:
            __instance = VishnuBrowser.__impl(cookiejar, passwords)
            VishnuBrowser.__instance = __instance
            self.__dict__['_VishnuBrowser__instance'] = __instance

    def __getattr__(self, attr):
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        return setattr(self.__instance, attr, value)

    class __impl(mechanize.Browser):
        def __init__(self, cookiejar, passwords):
            mechanize.Browser.__init__(self)
            cj = None
            if cookiejar:
                cj = mechanize.MozillaCookieJar()
                cj.load(cookiejar)
                self.set_cookiejar(cj)

            self.cj = cj

            socket.setdefaulttimeout(10)

            for url in passwords:
                self.add_password(url, passwords[url][0], passwords[url][1])
            self.set_handle_robots(False)
            self.set_handle_refresh(False)
            self.addheaders = [
                ('User-agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SLCC1; .NET CLR 2.0.50727; .NET CLR 3.0.04506; InfoPath.2)')
            ]

if __name__ == '__main__':
    b = VishnuBrowser(config.cookiejar)

    f = b.open("http://www.ice-nine.org/matt/pics/mjw/2007/10/26")

    print f.read()

# vim: ts=4 sw=4 et
