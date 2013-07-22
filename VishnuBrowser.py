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
                ('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2')
            ]
#            self.set_debug_http(True)
            self.set_proxies({'http' : 'proxy.ice-nine.org:3128',
                              'https' : 'proxy.ice-nine.org:3128' })
           

if __name__ == '__main__':
    b = VishnuBrowser(config.cookiejar)

    f = b.open("http://www.ice-nine.org/matt/pics/mjw/2007/10/26")

    print f.read()

# vim: ts=4 sw=4 et
