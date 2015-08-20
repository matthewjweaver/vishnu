#!/usr/bin/env python

from PlayerPlugin import PlayerPlugin
import ConfigParser
import linkcache.linkcache

class UrlSnarferPlugin(PlayerPlugin):
    def __init__(self):
        PlayerPlugin.__init__(self)
        config = ConfigParser.ConfigParser()
        config.read('linkcache.ini')
        self.cache = linkcache.linkcache.LinkCache(config)

    def start(self):
        self.map("StageTalkEvent")
        self.map("GeneralEvent")
        self.map("TalkEvent")

    def die(self):
        try:
            self.database.flush()
        except Exception, e:
            pass

    def react(self, event):
        line = event.message

        if event.from_who != "vishnu":
            try:
                response = self.cache.parse_line(line, event.from_who)
            except Exception, e:
                self.say(event, str(e))
                raise

            if not response:
                return

            self.say(event, response.shorturl)
            description = unicode(response)
            if description:
                self.say(event, description)
            event.socket.command(";#212:_fromVishnu(\"" + response.url + "\")")
# vim: ts=4 sw=4 et
