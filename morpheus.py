import socket
import select
import re
import pickle
import time
import sched
import os
import sys
import imp
import new
import types
import random
import asyncore
import traceback
import threading
import codecs

## Possible return values durection react() call
##
# Continue processing the event
REACT_NONE                      = None
REACT_CONTINUE                  = 0
REACT_BREAK                     = 1
REACT_UNCHAIN_AND_CONTINUE      = 2 
REACT_UNCHAIN_AND_BREAK         = 3
REACT_YIELD                     = 4

# Priority
PRIORITY_MORPHEUS = -(2 ** 30)

## Globals
##
__MORPHEUS__ = None

## Base class for ALL objects
##
class __baseobject__(object):
    version = None
    name = None

## The Morpheus Robot
##
class Morpheus(__baseobject__):
    version = "0.1"
    name = "Event Reactor"

    class ControlSocket(asyncore.dispatcher):
        name = "ControlSocket"
        path = "socket"

        def __init__(self, morpheus):
            asyncore.dispatcher.__init__(self)
            self.morpheus = morpheus

        def create_server_socket(self):
            self.bufsize = 4096
            self.create_socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            try:
                os.unlink(self.path)
            except:
                pass
            self.bind(self.path)

        def create_client_socket(self):
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.connect(self.path)
            return sock

        def handle_read(self):
            buffer = self.recv(self.bufsize)
            while ('\r' in buffer):
                idx = buffer.index('\r')
                buffer = buffer[:idx] + buffer[idx+1:]
            commands = buffer.split('\n')
            for command in commands:
                print "Control command:", command
                if command == "reload":
                    self.morpheus.reload()
                elif command == "shutdown":
                    self.morpheus.shutdown()
                elif command.startswith('dispatch '):
                    eventname = command[9:]
                    event = self.morpheus.registry[eventname]
                    ev = event()
                    ev.dispatch()

        def handle_connect(self):
            print "Control Socket Connect"

        def readable(self): return True
        def writable(self): return False

    def __init__(self):
        self.running = False
        self.registry = MorpheusRegistry(self)
        self.reactor = MorpheusReactor(self)

    def control_socket(self, server=True, client=True):
        self.control_socket = self.ControlSocket(self)
        self.control_remote = None
        if server:
            self.control_socket.create_server_socket()
        if client:
            self.control_remote = self.control_socket.create_client_socket()

    def control_command(self, command):
        assert self.control_remote, "Server connection not configured."
        self.control_remote.send(command)

    def go(self):
        self.running = True
        self.network = MorpheusNetwork(self)
        self.control_socket()
        self.timer = MorpheusTimer(self)
        self.registry.plugins_initialize()
        self.registry.plugins_start()
        asyncore.loop(use_poll=True)

    def plugin(self, fn):
        self.registry.module_import(fn)

    def reload(self, threshold=None):
        self.registry.plugins_reload(threshold)

    def shutdown(self):
        self.running = False
        self.timer.shutdown()
        self.control_socket.close()
        self.registry.plugins_shutdown()

    def register(self, entity):
        self.registry.register(entity)

    def get_morpheus(cls):
        global __MORPHEUS__
        try:
            __MORPHEUS__ = sys.modules['morpheus'].__MORPHEUS__
        except:
            pass
        if __MORPHEUS__ == None:
            __MORPHEUS__ = Morpheus()
            print "Morpheus: ", __MORPHEUS__
        return __MORPHEUS__
    get_morpheus = classmethod(get_morpheus)
get_morpheus = Morpheus.get_morpheus

## Base class for extrernal objects
##
class MorpheusObject(__baseobject__):
    version = "0.1"
    name = "MorpheusObject"
    Morpheus = None
    priority = 0

    class __metaclass__(type):
        def __init__(cls, name, bases, ns):
            if name != "MorpheusObject":
                if 'name' not in ns:
                    cls.name = name
            if not name in (
                'MorpheusObject', 
                'MorpheusEvent', 
                'MorpheusPlugin'): 
                    cls.morpheus = get_morpheus()
                    cls.morpheus.registry.register(cls)

## Utility function to compare priorties
##
def pricmp(this, that):
    if this.priority < that.priority:
        return -1
    if this.priority > that.priority:
        return 1
    return 0

## Base class for Events
##
class MorpheusEvent(MorpheusObject):
    version = "0.1"
    name = "Morpheus Base Event"

    def __init__(self, event=None):
        super(MorpheusEvent, self).__init__()
        self.precursor = event
        self._event_id = self.morpheus.reactor.next_event_id()

    def event_id(self):
        return self._event_id

    def dispatch(self):
        self.morpheus.reactor.react(self)

    def react(self):
        return self.morpheus.reactor.react(self)

## Base class for Plugins
##
class MorpheusPlugin(MorpheusObject):
    version = "0.1"
    name = "Morpheus Base Plugin"
    eventmap = {}

    def initialize(self): 
        pass

    def start(self): 
        pass
    
    def react(self, event):
        name =  event.name
        if name in self.eventmap:
            callback = self.eventmap[name]
            ret = callback(event)
            if ret == None:
                return REACT_CONTINUE
            return ret
        return REACT_CONTINUE

    def stop(self):
        pass

    def map(self, eventname):
        self.morpheus.reactor.chain(eventname, self.__class__.__name__)

    def unmap(self, eventname):
        self.morpheus.reactor.chain(eventname, self.__class__.__name__)

## Core Componentry
##
class MorpheusReactor(__baseobject__):
    version = "0.1"
    name = "Event Reactor"

    def __init__(self, morpheus):
        self.morpheus = morpheus
        self.eventmap = {}
        self._next_event_id = 0

    def next_event_id(self):
        self._next_event_id += 1
        return self._next_event_id

    def react(self, event):
        idstr = "0x%s" % str.upper(hex(abs(id(event)))[2:])
        print "react (%s): %s" % (idstr, event)
        eventname = event.name
        if not eventname in self.eventmap:
            #print "react warning: unknown event: %s" % eventname
            return
        targets = self.eventmap[eventname]
        ret = REACT_NONE
        for targetname in targets[:]:
            if not self.morpheus.running:
                print "Warning: aborting chain reaction due to shutdown."
                break
            try:
                target = self.morpheus.registry[targetname]
            except KeyError:
                print "Warning: unknown target: %s" % targetname
                continue
            try:
                ret = target.react(event)
            except:
                print "react (%s): %s" % (idstr, event)
                traceback.print_exc()
                break
            if ret in (REACT_CONTINUE, REACT_NONE):
                continue
            elif ret == REACT_BREAK:
                break
            elif ret == REACT_UNCHAIN_AND_CONTINUE:
                self.unchain(eventname, targetname)
                continue
            elif ret == REACT_UNCHAIN_AND_BREAK:
                self.unchain(eventname, targetname)
                break
            else:
                raise ValueError, "unexpected return value: %s" % ret
        return ret
    
    def chain(self, eventname, targetname):
        assert type(eventname) == str and type(targetname) == str
        if eventname not in self.eventmap:
            self.eventmap[eventname] = []
        self.eventmap[eventname].append(targetname)
        self.eventmap[eventname].sort()

    def unchain(self, eventname, targetname=None):
        assert type(eventname) == str and \
                (targetname == None or type(targetname) == str)
        if eventname in self.eventmap:
            if targetname != None:
                del self.eventmap[eventname]
            else:
                kill = []
                for idx in range(len(self.eventmap[eventname])):
                    _tar = self.eventmap[eventname][idx]
                    if targetname == _tar:
                        kill.append(idx)
                    for idx in kill:
                        del self.eventmap[eventname][idx]
                if not len(self.eventmap[eventname]):
                    del self.eventmap[eventname]

class MorpheusRegistry(__baseobject__):
    def __init__(self, morpheus):
        self.morpheus = morpheus
        self.modules = []
        self.plugged = {}
        self.registry = {}

    def register(self, entity):
        assert isinstance(entity, MorpheusObject) or \
                issubclass(entity, MorpheusObject)
        idstr = "0x%s" % str.upper(hex(abs(id(entity)))[2:])
        print "register (%s): %s" % (idstr, entity.name)
        self.registry[entity.name] = entity

    def __getitem__(self, key):
        try:
            return self.plugged[key]
        except KeyError:
            return self.registry[key]

    def __contains__(self, key):
        return (key in self.plugged) or (key in self.registry)

    def module_import(self, name):
        try:
            module = sys.modules[name]
        except KeyError:
            module = self.module_load(name)
        if module and module not in self.modules:
            self.modules.append(name)

    def module_load(self, name):
        fp, pathname, description = imp.find_module(name)
        fp.close()
        if pathname.endswith('pyc'):
            pathname = pathname[:-1]
        module = imp.load_source(name, pathname)
        return module

    def plugins_get(self):
        ret = []
        for entity in self.registry.values():
            try:
                if issubclass(entity, MorpheusPlugin):
                    ret.append(entity)
            except:
                continue
        ret.sort(pricmp)
        return ret

    def plugins_initialize(self, threshold=None):
        plugins = self.plugins_get()
        for plug in plugins:
            if threshold != None and plug.priority < threshold:
                continue
            plug = plug()
            self.plugged[plug.name] = plug
            plug.initialize()

    def plugins_start(self, threshold=None):
        for plugname in self.plugged:
            plug = self.plugged[plugname]
            if threshold != None and plug.priority < threshold:
                continue
            plug.start()

    def plugins_shutdown(self, threshold=None):
        for plugname in self.plugged.keys():
            plug = self.plugged[plugname]
            if threshold != None and plug.priority < threshold:
                continue
            plug.stop()
            del self.plugged[plugname]

    def plugins_reload(self, threshold=None):
        self.plugins_shutdown(threshold)
        for module in self.modules:
            print "Reloading \"%s\" module." % module
            self.module_load(module)
        self.plugins_initialize(threshold)
        self.plugins_start(threshold)

class MorpheusNetwork(__baseobject__):
    name = "Morpheus Network"
    priority = PRIORITY_MORPHEUS

    class Socket(MorpheusObject, asyncore.dispatcher):
        def __init__(self, name, eventclass, bufsize=1024):
            asyncore.dispatcher.__init__(self)
            self.name = name
            self.bufsize = 1024
            self.write_buffer = u''
            self.event = eventclass
            self.event.socket = self

        def connect(self, host, port):
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            asyncore.dispatcher.connect(self, (host, port))

        def handle_connect(self):
            pass

        def handle_close(self):
            self.close()

        def handle_read(self):
            buffer = self.recv(self.bufsize)
            while ('\r' in buffer):
                if '\r' in buffer:
                    idx = buffer.index('\r')
                    buffer = buffer[:idx] + buffer[idx+1:]
            #while ('\n' in buffer):
                #if '\n' in buffer:
                #    idx = buffer.index('\n')
                #    buffer = buffer[:idx] + buffer[idx+1:]
            ev = self.event()
            ev.buffer = buffer
            ev.dispatch()
        
        def readable(self):
            return True

        def writable(self):
            return bool(self.write_buffer)

        def handle_write(self):
	    sent = asyncore.dispatcher.send(self, self.write_buffer)
            self.write_buffer = self.write_buffer[sent:]

	def handle_error(self):
	    n = len(self.write_buffer)
	    b = codecs.encode(self.write_buffer, 'ascii', 'replace')
	    sent = asyncore.dispatcher.send(self, b)
            self.write_buffer = self.write_buffer[n:]
	    pass

        def send(self, data):
            self.write_buffer += data

        def command(self, command):
            self.write_buffer += "%s\n\r" % command

    class SocketEvent(MorpheusEvent):
        name = "Socket Event"
        socket = None
        buffer = ''

        def new(cls, name, ns={}):
            return new.classobj(name, (cls,), ns)
        new = classmethod(new)

    def socket(self, name, bufsize=1024):
        # make new SocketEvent class
        if name in self.morpheus.registry:
            return self.morpheus.registry[name]
        eventname = "%sEvent" % name
        ev = self.SocketEvent.new(eventname)
        socket = self.Socket(name, ev, bufsize=bufsize)
        self.morpheus.register(socket)
        return socket

    def __init__(self, morpheus):
        self.morpheus = morpheus

class MorpheusTimer(__baseobject__, threading.Thread):
    version = "0.1"
    name = "Morpheus Timer"

    class TimerEvent(MorpheusEvent):
        name = "Timer Event"
        absolute = False
        repeat = False
        offset = 0
        priority = 0
        schedule_id = None

        def new(cls, name, timer, offset=0, absolute=False, repeat=False, priority=0, ns={}):
            ns['offset'] = float(offset)
            ns['absolute'] = bool(absolute)
            ns['priority'] = int(priority)
            ns['repeat'] = bool(repeat)
            ns['timer'] =  timer
            return new.classobj(name, (cls,), ns)
        new = classmethod(new)
        
        def schedule(cls):
            # re-schedule check
            if cls.schedule_id != None:
                if not cls.repeat:
                    return False
            schedule = cls.timer.schedule
            # XXX: NOT THREAD SAFE (what if schedule is running?)
            if cls.absolute:
                cls.schedule_id = schedule.enterabs(
                        cls.offset, cls.priority, cls.timer.dispatch, (cls,))
            else:
                cls.schedule_id = schedule.enter(
                        cls.offset, cls.priority, cls.timer.dispatch, (cls,))
            return True
        schedule = classmethod(schedule)

    def __init__(self, morpheus):
        super(MorpheusTimer, self).__init__()
        self.morpheus = morpheus
        self.running = True
        self.cv_work = threading.Condition()
        self.schedule = sched.scheduler(time.time, time.sleep)
        self.start()

    def add(self, name, targetname, time=0, absolute=False, repeat=False, priority=0):
        ev = self.TimerEvent.new(name, self, time, absolute, repeat, priority)
        self.morpheus.reactor.chain(name, targetname)
        ev.schedule()
        self.notify()

    def notify(self):
        self.cv_work.acquire()
        self.cv_work.notify()
        self.cv_work.release()

    def dispatch(self, cls):
        dispatch = "dispatch %s" % cls.name
        self.morpheus.control_command(dispatch)
        cls.schedule()
        
    def run(self):
        print "MorpheusTimer: Starting timer thread"
        while True:
            self.cv_work.acquire()
            # shutdown the thread loop?
            if not self.running:
                self.cv_work.release()
                break
            # are there timer events?
            if self.empty():
                self.cv_work.wait()
                # we just woke up -- let's retest everything
                continue
            # if we get here, we have work to do
            self.cv_work.release()
            self.schedule.run()
            
    def empty(self):
        return self.schedule.empty()

    def shutdown(self):
        self.running = False
        self.notify()

## Core Plugins
##
class MorpheusRegex(MorpheusPlugin):
    name = "Morpheus Regular Expression Engine"
    priority = PRIORITY_MORPHEUS

    def initialize(self):
        self.morpheus.regex = self

    class RegexEvent(MorpheusEvent):
        name = "Regex Event"
        regex = None
        match = None
        socket = None
        priority = 0

        def new(cls, name, regex, priority=0, ns={}):
            ns['regex'] = regex
            ns['priority'] = priority
            return new.classobj(name, (cls,), ns)
        new = classmethod(new)

        def __init__(self, event=None):
            super(MorpheusEvent, self).__init__(event)
            if isinstance(event, MorpheusNetwork.SocketEvent):
                self.socket = event.socket

    def __init__(self):
        self.regex_events = []
        self.regex_map = {}

    def bind(self, eventname):
        self.morpheus.reactor.chain(eventname, self.name)

    def unbind(self, eventname):
        self.morpheus.reactor.unchain(eventname, self.name)

    def react(self, event):
        buffer = ''
        if isinstance(event, MorpheusNetwork.SocketEvent):
            buffer = event.buffer
        for regex_event in self.regex_events[:]:
            m = regex_event.regex.search(buffer)
            if m:
                event = regex_event(event)
                event.match = m
                event.buffer = buffer
                ret = event.react()
                if ret in (REACT_CONTINUE, REACT_NONE):
                    continue
                elif ret == REACT_BREAK:
                    break
                elif ret == REACT_UNCHAIN_AND_CONTINUE:
                    self.unchain(regex_event.name)
                    continue
                elif ret == REACT_UNCHAIN_AND_BREAK:
                    self.unchain(regex_event.name)
                    break
                else:
                    raise ValueError, "unexpected return value: %s" % ret
        return REACT_CONTINUE
            
    def _sync(self):
        self.regex_events = self.regex_map.values()
        self.regex_events.sort()

    def _map_regex_event(self, regex_event):
        self.regex_map[regex_event.name] = regex_event
        self._sync()

    def _unmap_regex_event(self, event_name):
        del self.regex_map[event_name]
        self._sync()

    def create(self, name, regex, priority=0):
        return self.RegexEvent.new(name, regex, priority)

    def chain(self, name, targetname, priority=0):
        regex_event = self.morpheus.registry[name]
        self._map_regex_event(regex_event)
        self.morpheus.reactor.chain(name, targetname)

    def create_and_chain(self, name, targetname, regex, priority=0):
        regex_event = self.create(name, regex, priority)
        self.chain(name, targetname, priority)

    def unchain(self, name, targetname=None):
        self._unmap_regex_event(name)
        self.morpheus.reactor.unchain(name, targetname)

class RegEx(MorpheusPlugin):
    regex = ''
    morpheus = None
    priority = 500

    class __metaclass__(MorpheusPlugin.__metaclass__):
        def __init__(cls, name, bases, ns):
            if cls.regex:
                cls.regex_string = cls.regex
                cls.regex = re.compile(cls.regex)
            super(cls.__metaclass__, cls).__init__(name, bases, ns)

    def bind(cls, name):
        cls.morpheus.regex.add(cls.name, name, cls, cls.priority)
    bind = classmethod(bind)


class WaitOn(MorpheusPlugin):
    priority = 500
    generators = {}
    waitcount = 0

    def react(self, event):
        self.event = event
        if event.name not in self.generators:
            generator = self.react_generator()
            ret = REACT_BREAK
        else:
            generator = self.generators[event.name]
            del self.generators[event.name]
            ret = REACT_UNCHAIN_AND_BREAK
        try:
            next_eventname = generator.next()
            self.generators[next_eventname] = generator
        except StopIteration:
            pass
        return ret

    def waiton(self, regex):
        name = self.name + 'WaitOnEvent-%d' % self.waitcount
        regex = re.compile(regex)
        regexev = self.morpheus.regex.create(name, regex, self.priority)
        self.morpheus.regex.chain(regexev, self.name, self.priority)
        self.waitcount += 1
        return name

    def react_generator(self):
        pass

