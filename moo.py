#!/usr/bin/env python
import re
import datetime
import time
import sgmllib

import UrlSnarfer
from UrlSnarfer import *
from StockTicker import StockTickerPlugin
from ButterflyLabs import ButterflyLabsPlugin

from morpheus import *
from config import *

ADMINS = ['jeffm', 'gib']

class Vishnu(MorpheusPlugin):
    priority = -1

    def initialize(self):
        global VISHNU, DB
        VISHNU = self
        self.socket = self.morpheus.registry[SOCKET_NAME]

    def set_property(self, name, value, flags="c"):
        args = {
            "name":name,
            "value":value,
            "flags":flags,
        }
        prop = '@prop me.%(name)s "" "%(flags)s"\n;me.%(name)s = "%(value)s"'
        cmd = prop % args
        self.send_command(cmd)

    def send_command(self, command):
        self.socket.command(command)

class Contextualize(MorpheusPlugin):
    priority = 0

    class MooEvent(MorpheusEvent):
        socket = None
        priority = 0
        message = ''
        from_who = ''
        from_who_objid = -1
        to_who = ''

        def __init__(self, event=None, message='', from_who='', from_who_objid=-1, to_who=''):
            MorpheusEvent.__init__(self, event)
            if isinstance(event, MorpheusNetwork.SocketEvent):
                self.socket = event.socket
            self.from_who = from_who
            self.from_who_objid = from_who_objid
            self.to_who = to_who
            self.message = message

        def __str__(self):
            return str.join(" ",
                    (self.name, self.from_who, self.to_who, self.message))

    class WhisperEvent(MooEvent):
        pass
    class PageEvent(MooEvent):
        pass
    class TalkEvent(MooEvent):
        pass
    class StageTalkEvent(MooEvent):
        pass
    class PasteEvent(MooEvent):
        pass
    class BeanEvent(MooEvent):
        pass
    class SocialEvent(MooEvent):
        pass
    class GeneralEvent(MooEvent):
        pass

    def initialize(self):
        self.map(SOCKET_EVENT_NAME)

    def react(self, event):
        if isinstance(event, MorpheusNetwork.SocketEvent):
            text = event.buffer
        lines = text.split('\n')
        for line in lines:
            if len(line):
                newevent = self.contextualize(event, line)
                newevent.dispatch()
        return REACT_CONTINUE

    def contextualize(self, event, line):
        print line
        split = line.split('$')
        # GeneralEvent
        if len(split) < 3:
            # this might be a spoof
            print "Bailing out: spoof detection"
            return self.GeneralEvent(event, line)
        # Not a General Event; parse message
        from_who_objid = split[0]
        from_who = split[1]
        offset = len(from_who_objid) + len(from_who) + 2
        message = line[offset:]
        # TalkEvent
        test = re.compile('^%s says, "(.*)"$' % from_who)
        match = test.match(message)
        if match:
            message = match.group(1)
            return self.TalkEvent(event, message, from_who, from_who_objid)
        # WhisperEvent
        test = re.compile('^%s whispers, "(.*)".$' % from_who)
        match = test.match(message)
        if match:
            message = match.group(1)
            return self.WhisperEvent(event, message, from_who, from_who_objid)
        # PageEvent
        test = re.compile('^(\[.+]\: |)%s pages, "(.*)"$' % from_who) 
        match = test.match(message)
        if match:
            message = match.group(2)
            return self.PageEvent(event, message, from_who, from_who_objid)
        # StageTalk
        test = re.compile('^%s \[to (.*)\]: (.*)$' % from_who)
        match = test.match(message)
        if match:
            to_who = match.group(1)
            message = match.group(2)
            return self.StageTalkEvent(event, message, from_who, from_who_objid, to_who)
        return self.GeneralEvent(event, message, from_who, from_who_objid)

#class GoogleHandler(MorpheusPlugin):
#    def start(self):
#        self.map("StageTalkEvent")
#        self.map("PageEvent")
#        self.map("GeneralEvent")
#
#    def react(self, event):
#        orig = event.message
#        m = re.compile("!google (.*)$")
#        match = m.match(event.message)
#        if match:
#            terms = match.group(1)
#            print "Hunting down %s" % event.message
#            self.morpheus.reactor.react(event)
#        else:
#            print "!google didn't match %s" % orig


class StageTalkHandler(MorpheusPlugin):
    def start(self):
        self.map("StageTalkEvent")

    def react(self, event):
        if event.to_who != "vishnu":
            return
	line = ""
        try:
            describeRe = re.compile(r"describe\s+([a-zA-Z0-9]+)\s+(.*)")
            m = describeRe.match(event.message)
            if m is not None:
                url = m.group(1)
                description = m.group(2)
                id = int(UrlSnarfer.urlToId(url))

                query = """UPDATE url SET title = %s WHERE id = %s"""
                cursor = db.execute(query, [description, id])
                line = "-%s description updated." % event.from_who
        except Exception, e:
            line = "-%s " % event.from_who
            line += str(e)
	if line != "":
		event.socket.command(line)

class WhisperHandler(MorpheusPlugin):
    def start(self):
        self.map("WhisperEvent")
        self.map("PageEvent")


    def react(self, event):
        try:
            if event.from_who in ADMINS and event.message == "reload":
                self.morpheus.reload(0)
            if event.from_who in ADMINS and event.message == "shutdown":
                self.morpheus.shutdown()

            passre = re.compile(r"passwd\s+(.*)")
            passwd = passre.match(event.message)
            if passwd is not None:
                password = passwd.group(1)
                query = "SELECT * from auth WHERE username=%s"

                cursor = db.execute(query, [event.from_who])

                if cursor.rowcount == 0:
                    query = "INSERT INTO auth VALUES(%s, PASSWORD(%s))"
                    cursor = db.execute(query, [event.from_who, password])
                elif cursor.rowcount == 1:
                    query = "UPDATE auth SET password=PASSWORD(%s) WHERE username=%s"
                    cursor = db.execute(query, [password, event.from_who])
                else:
                    raise Exception, "DB is broken!"


            evalre = re.compile(r"eval\s+(.*)")
            eval = evalre.match(event.message)
            if eval is not None:
                if event.from_who in ADMINS:
                    event.socket.command(eval.group(1))
                    return
                else:
                    event.socket.command("~" + event.from_who + " " +
                                         "Permission denied.")
                    return


            dore = re.compile(r"do\s+(\S*)\s*(.*)")
            do = dore.match(event.message)
#        else if dore is not None:
#            if do.group(1) == "update_socials":
#                socials = SocialUpdater()
#                soci
        except Exception, e:
            print e
            event.socket.command("~" + event.from_who + " " + str(e))
            raise


class Log(MorpheusPlugin):
    priority = 1

    def start(self):
        self.sessions = []
        self.map("GeneralEvent")

    def push_session(self):
        self.sessions.append([])

    def pop_session(self):
        session = self.sessions[-1]
        del self.sessions[-1]
        return session
    
    def react(self, event):
        if self.sessions:
            session = self.sessions[-1]
            session.append(event.message)
            self.sessions[-1] = session

##
## Connection classes
class NetworkConnection(MorpheusPlugin):
    priority = -10
    
    def initialize(self):
        self.socket = self.morpheus.network.socket(SOCKET_NAME)
        self.morpheus.regex.bind(SOCKET_EVENT_NAME)

    def start(self):
        self.socket.connect(HOST, PORT)

    def stop(self):
        self.socket.close()

class LoginPre(MorpheusPlugin):
    regex = '.*from the Tibetan "Book of the Dead".*'
    priority = -8
    
    def start(self):
        regex = re.compile(self.regex)
        self.morpheus.regex.create_and_chain(
            "LoginPreEvent", self.name, regex, self.priority)
    
    def react(self, event):
        cmd = 'co %s %s' % ('vishnu', '7357')
        event.socket.command(cmd)
        return REACT_UNCHAIN_AND_BREAK

class LoginPost(MorpheusPlugin):
    regex = '.*to read just new news.*'
    priority = -7
    properties = {
        "__VERSION__":1,
        "__COOKIE__":1,
        #"description":"vishnu is a blue and black shinned Hindu god with four arms.  He gazes off into the unknown while levitating in the lotus position.",
        "description":"vishnu is a python based robot that runs on iorek.  if you have any questions or concerns regarding it, please talk to gib.",
    }
        
    def start(self):
        regex = re.compile(self.regex)
        self.morpheus.regex.create_and_chain(
            "LoginPostEvent", self.name, regex, self.priority)

    def react(self, event):
        event.socket.send(LAMBDA_PLAYER)
        for prop in self.properties:
            VISHNU.set_property(prop, self.properties[prop])
#        cmd = "@move me to #1179"
        cmd = "@join jeffm"
#        cmd = "@move me to #115"
        event.socket.command(cmd)

        return REACT_UNCHAIN_AND_BREAK

#class LogReader(MorpheusPlugin):
class LogReader:
    log_command = ";#212:read()"
    log_return_re = re.compile("=> 0")
    accept = ('http', 'ftp:')

    def _start(self):
        self.log = self.morpheus.registry['Log']
        self.morpheus.timer.add("LogTimerEvent", self.name, 2, repeat=True)
        self.logreturn_event = self.morpheus.regex.create(
                        "LogReturn", self.log_return_re, self.name)

    def process_urls(self, urllist):
        for url in urllist:
            if not url:
                continue
            nws = False
            if url[0] == '!':
                nws = True
                url = url[1:]
            proto = str.lower(url[:4])
            if proto in self.accept:
                print url
    
    def _react(self, event):
        if event.name == "LogTimerEvent":
            VISHNU.send_command(self.log_command)
            self.log.push_session()
            self.map("LogReturn")
        elif event.name == "LogReturn":
            log = self.log.pop_session()
            self.process_urls(log)
            return REACT_UNCHAIN_AND_BREAK
        
class Conversation(WaitOn):
    def start(self):
        regex = re.compile(".*vic.*")
        self.morpheus.regex.create_and_chain(
            "ConversationEvent", self.name, regex, self.priority)

#    def react_generator(self):
#        self.event.socket.command("say hi")
#        yield self.waiton(".*talk.*")
#        self.event.socket.command("say hello")
#        yield self.waiton(".*tylk.*")
#        self.event.socket.command("say hyllo")

class MooDbInstance:
    def __init__(self, name, user, passwd, host):
        self.name = name
        self.user = user
        self.passwd = passwd
        self.host = host
        try:
            self.reconnect()
        except ImportError:
            raise callbacks.Error, "You need python-mysql installed"
        except Exception, e:
            print e
            raise

    def reconnect(self):
            self.db = MySQLdb.connect(db=self.name, user=self.user,
                                      passwd=self.passwd, host=self.host)

    def execute(self, query, values):
        for i in [1, 1]:
            try:
                cursor = self.db.cursor()
                cursor.execute(query, values)
            except MySQLdb.OperationalError, e:
                self.reconnect()
            else:
                break

        return cursor

if __name__ == '__main__':
    db = MooDbInstance(name=db_name, user=db_user, passwd=db_pass, host=db_host)
    morpheus = get_morpheus()
    for arg in sys.argv[1:]:
	    morpheus.plugin( arg )
    morpheus.go()


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
