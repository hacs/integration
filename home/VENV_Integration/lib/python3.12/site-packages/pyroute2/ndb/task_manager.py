import inspect
import logging
import queue
import threading
import time
import traceback
from functools import partial

from pyroute2 import config

from . import schema
from .events import (
    DBMExitException,
    InvalidateHandlerException,
    RescheduleException,
    ShutdownException,
)
from .messages import cmsg, cmsg_event, cmsg_failed, cmsg_sstart

log = logging.getLogger(__name__)


def Events(*argv):
    for sequence in argv:
        if sequence is not None:
            for item in sequence:
                yield item


class NDBConfig(dict):
    def __init__(self, task_manager):
        self.task_manager = task_manager

    def __getitem__(self, key):
        return self.task_manager.config_get(key)

    def __setitem__(self, key, value):
        return self.task_manager.config_set(key, value)

    def __delitem__(self, key):
        return self.task_manager.config_del(key)

    def keys(self):
        return self.task_manager.config_keys()

    def items(self):
        return self.task_manager.config_items()

    def values(self):
        return self.task_manager.config_values()


class TaskManager:
    def __init__(self, ndb):
        self.ndb = ndb
        self.log = ndb.log
        self.event_map = {}
        self.event_queue = ndb._event_queue
        self.thread = None
        self.ctime = self.gctime = time.time()

    def register_handler(self, event, handler):
        if event not in self.event_map:
            self.event_map[event] = []
        self.event_map[event].append(handler)

    def unregister_handler(self, event, handler):
        self.event_map[event].remove(handler)

    def default_handler(self, target, event):
        if isinstance(getattr(event, 'payload', None), Exception):
            raise event.payload
        log.debug('unsupported event ignored: %s' % type(event))

    def check_sources_started(self, _locals, target, event):
        _locals['countdown'] -= 1
        if _locals['countdown'] == 0:
            self.ndb._dbm_ready.set()

    def wrap_method(self, method):
        #
        # this wrapper will be published in the DBM thread
        #
        def _do_local_generator(target, request):
            try:
                for item in method(*request.argv, **request.kwarg):
                    request.response.put(item)
                request.response.put(StopIteration())
            except Exception as e:
                request.response.put(e)

        def _do_local_single(target, request):
            try:
                (request.response.put(method(*request.argv, **request.kwarg)))
            except Exception as e:
                (request.response.put(e))

        #
        # this class will be used to map the requests
        #
        class cmsg_req(cmsg):
            def __init__(self, response, *argv, **kwarg):
                self['header'] = {'target': None}
                self.response = response
                self.argv = argv
                self.kwarg = kwarg

        #
        # this method will proxy the original one
        #
        def _do_dispatch_generator(self, *argv, **kwarg):
            if self.thread == id(threading.current_thread()):
                # same thread, run method locally
                for item in method(*argv, **kwarg):
                    yield item
            else:
                # another thread, run via message bus
                response = queue.Queue()
                request = cmsg_req(response, *argv, **kwarg)
                self.event_queue.put((request,))
                while True:
                    item = response.get()
                    if isinstance(item, StopIteration):
                        return
                    elif isinstance(item, Exception):
                        raise item
                    else:
                        yield item

        def _do_dispatch_single(self, *argv, **kwarg):
            if self.thread == id(threading.current_thread()):
                # same thread, run method locally
                return method(*argv, **kwarg)
            else:
                # another thread, run via message bus
                response = queue.Queue(maxsize=1)
                request = cmsg_req(response, *argv, **kwarg)
                self.event_queue.put((request,))
                ret = response.get()
                if isinstance(ret, Exception):
                    raise ret
                else:
                    return ret

        #
        # return the method spec to be announced
        #
        handler = _do_local_single
        proxy = _do_dispatch_single
        if inspect.isgeneratorfunction(method):
            handler = _do_local_generator
            proxy = _do_dispatch_generator
        return (cmsg_req, handler, proxy)

    def register_api(self, api_obj, prefix=''):
        for name in dir(api_obj):
            method = getattr(api_obj, name, None)
            if hasattr(method, 'publish'):
                if isinstance(method.publish, str):
                    name = method.publish
                name = f'{prefix}{name}'
                event, handler, proxy = self.wrap_method(method)
                setattr(self, name, partial(proxy, self))
                self.event_map[event] = [handler]

    def run(self):
        _locals = {'countdown': len(self.ndb._nl)}
        self.thread = id(threading.current_thread())

        # init the events map
        event_map = {
            cmsg_event: [lambda t, x: x.payload.set()],
            cmsg_failed: [lambda t, x: (self.ndb.schema.mark(t, 1))],
            cmsg_sstart: [partial(self.check_sources_started, _locals)],
        }
        self.event_map = event_map

        try:
            self.ndb.schema = schema.DBSchema(
                self.ndb.config,
                self.ndb.sources,
                self.event_map,
                self.log.channel('schema'),
            )
            self.register_api(self.ndb.schema, 'db_')
            self.register_api(self.ndb.schema.config, 'config_')
            self.ndb.bonfig = NDBConfig(self)

        except Exception as e:
            self.ndb._dbm_error = e
            self.ndb._dbm_ready.set()
            return

        for spec in self.ndb._nl:
            spec['event'] = None
            self.ndb.sources.add(**spec)

        for event, handlers in self.ndb.schema.event_map.items():
            for handler in handlers:
                self.register_handler(event, handler)

        stop = False
        source = None
        reschedule = []
        while not stop:
            source, events = self.event_queue.get()
            events = Events(events, reschedule)
            reschedule = []
            try:
                for event in events:
                    handlers = event_map.get(
                        event.__class__, [self.default_handler]
                    )

                    for handler in tuple(handlers):
                        try:
                            target = event['header']['target']
                            handler(target, event)
                        except RescheduleException:
                            if 'rcounter' not in event['header']:
                                event['header']['rcounter'] = 0
                            if event['header']['rcounter'] < 3:
                                event['header']['rcounter'] += 1
                                self.log.debug('reschedule %s' % (event,))
                                reschedule.append(event)
                            else:
                                self.log.error('drop %s' % (event,))
                        except InvalidateHandlerException:
                            try:
                                handlers.remove(handler)
                            except Exception:
                                self.log.error(
                                    'could not invalidate '
                                    'event handler:\n%s'
                                    % traceback.format_exc()
                                )
                        except ShutdownException:
                            stop = True
                            break
                        except DBMExitException:
                            return
                        except Exception:
                            self.log.error(
                                'could not load event:\n%s\n%s'
                                % (event, traceback.format_exc())
                            )
                    if time.time() - self.gctime > config.gc_timeout:
                        self.gctime = time.time()
            except Exception as e:
                self.log.error(f'exception <{e}> in source {source}')
                # restart the target
                try:
                    self.log.debug(f'requesting source {source} restart')
                    self.ndb.sources[source].state.set('restart')
                except KeyError:
                    self.log.debug(f'key error for {source}')
                    pass

        # release all the sources
        for target in tuple(self.ndb.sources.cache):
            source = self.ndb.sources.remove(target, sync=False)
            if source is not None and source.th is not None:
                self.log.debug(f'closing source {source}')
                source.close()
                if self.ndb.schema.config['db_cleanup']:
                    self.log.debug('flush DB for the target %s' % target)
                    self.ndb.schema.flush(target)
                else:
                    self.log.debug('leave DB for debug')

        # close the database
        self.ndb.schema.commit()
        self.ndb.schema.close()

        # close the logging
        for handler in self.log.logger.handlers:
            handler.close()
