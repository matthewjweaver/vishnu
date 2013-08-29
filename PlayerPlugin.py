#!/usr/bin/env python


from morpheus import MorpheusPlugin

class PlayerPlugin(MorpheusPlugin):
    def __init__(self):
        MorpheusPlugin.__init__(self)

    def say(self, event, text):
        event.socket.command("listsay \"" + text + "\"")

    def private(self, event, text):
        event.socket.command("~%s %s " % (event.from_who, text))

    def social(self, event, social, target=None, _with=None):
        if not target:
            target = event.from_who
        text = "%s %s" % (social, target)
        if _with:
            text += " with %s" % _with

        event.socket.command(text)


# vim: ts=4 sw=4 et
