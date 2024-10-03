from __future__ import print_function

import sys
import traceback
from collections import namedtuple

from pyroute2 import config
from pyroute2.cli import t_comma, t_dict, t_pipe, t_stmt
from pyroute2.cli.parser import Parser
from pyroute2.common import basestring


class Session(object):
    def __init__(self, ndb, stdout=None, ptrname_callback=None, builtins=None):
        self.db = ndb
        self.ptr = self.db
        self._ptrname = None
        self._ptrname_callback = ptrname_callback
        self.stack = []
        self.errors = 0
        self.indent_stack = set()
        self.prompt = ''
        self.stdout = stdout or sys.stdout
        self.builtins = builtins or (
            'ls',
            '.',
            '..',
            'version',
            'exit',
            ':stack',
        )

    @property
    def ptrname(self):
        return self._ptrname

    @ptrname.setter
    def ptrname(self, name):
        self._ptrname = name
        if self._ptrname_callback is not None:
            self._ptrname_callback(name)

    def stack_pop(self):
        self.ptr, self.ptrname = self.stack.pop()
        return (self.ptr, self.ptrname)

    def lprint(self, text='', end='\n'):
        if not isinstance(text, basestring):
            text = str(text)
        self.stdout.write(text)
        if end:
            self.stdout.write(end)
        self.stdout.flush()

    def handle_statement(self, stmt, token):
        obj = None
        if stmt.kind == t_dict:
            obj = self.ptr[stmt.kwarg]
        elif stmt.kind == t_stmt:
            obj = getattr(self.ptr, stmt.name, None)
            if obj is None and isinstance(self.ptr, dict):
                try:
                    obj = self.ptr.get(stmt.name, None)
                except KeyError:
                    pass

        if hasattr(obj, '__call__'):
            try:
                nt = next(token)
            except StopIteration:
                nt = namedtuple('Token', ('kind', 'argv', 'kwarg'))(
                    t_dict, [], {}
                )

            if nt.kind == t_dict:
                args = nt
                try:
                    pipe = next(token)
                    if pipe.kind != t_pipe:
                        raise TypeError('pipe expected')
                except StopIteration:
                    pipe = None
            elif nt.kind == t_stmt:
                argv = []
                kwarg = {}
                arg_name = nt.name
                pipe = None
                for nt in token:
                    if arg_name is None:
                        if nt.kind == t_stmt:
                            arg_name = nt.name
                        elif nt.kind == t_comma:
                            continue
                        elif nt.kind == t_pipe:
                            pipe = nt
                            break
                        else:
                            raise TypeError('stmt expected')
                    else:
                        if nt.kind == t_comma:
                            argv.append(arg_name)
                        elif nt.kind == t_stmt:
                            kwarg[arg_name] = nt.name
                        elif nt.kind == t_pipe:
                            pipe = nt
                            break
                        else:
                            raise TypeError('stmt or comma expected')
                        arg_name = None
                if arg_name is not None:
                    argv.append(arg_name)
                args = namedtuple('Token', ('kind', 'argv', 'kwarg'))(
                    t_dict, argv, kwarg
                )
            elif nt.kind == t_pipe:
                args = namedtuple('Token', ('kind', 'argv', 'kwarg'))(
                    t_dict, [], {}
                )
                pipe = nt
            else:
                raise TypeError('dict, stmt or comma expected')

            # at this step we have
            # args -- arguments
            # pipe -- pipe or None

            try:
                ret = obj(*args.argv, **args.kwarg)
                #
                if pipe is not None:
                    ptr = self.ptr
                    self.ptr = ret
                    try:
                        stmt = next(token)
                    except StopIteration:
                        raise TypeError('statement expected')
                    if stmt.kind != t_stmt:
                        raise TypeError('statement expected')
                    try:
                        self.handle_statement(stmt, token)
                    except Exception:
                        pass
                    self.ptr = ptr
                    return
                if hasattr(obj, '__cli_cptr__'):
                    obj = ret
                elif hasattr(obj, '__cli_publish__'):
                    if hasattr(ret, 'generator') or hasattr(ret, 'next'):
                        for line in ret:
                            if isinstance(line, basestring):
                                self.lprint(line)
                            else:
                                self.lprint(repr(line))
                    else:
                        self.lprint(ret)
                    return
                elif isinstance(ret, (bool, basestring, int, float)):
                    self.lprint(ret)
                    return
                else:
                    return
            except Exception:
                self.errors += 1
                traceback.print_exc()
                return
        else:
            if isinstance(self.ptr, dict) and not isinstance(obj, dict):
                try:
                    nt = next(token)
                    if nt.kind == t_stmt:
                        self.ptr[stmt.name] = nt.name
                    elif nt.kind == t_dict and nt.argv:
                        self.ptr[stmt.name] = nt.argv
                    elif nt.kind == t_dict and nt.kwarg:
                        self.ptr[stmt.name] = nt.kwarg
                    else:
                        raise TypeError('failed setting a key/value pair')
                    return
                except NotImplementedError:
                    raise KeyError()
                except StopIteration:
                    pass

        if obj is None:
            raise KeyError()
        elif isinstance(obj, (basestring, int, float)):
            self.lprint(obj)
        else:
            return obj

    def handle_sentence(self, sentence, indent):
        if sentence.indent < indent:
            while max(self.indent_stack) > sentence.indent:
                self.indent_stack.remove(max(self.indent_stack))
                if self.stack:
                    self.ptr, self.ptrname = self.stack.pop()
        else:
            self.indent_stack.add(sentence.indent)
        indent = sentence.indent
        iterator = iter(sentence)
        obj = None
        save_ptr = self.ptr
        save_ptrname = self.ptrname
        try:
            for stmt in iterator:
                if stmt.name in self.builtins:
                    if stmt.name == 'exit':
                        raise SystemExit()
                    elif stmt.name == 'ls':
                        self.lprint(dir(self.ptr))
                    elif stmt.name == ':stack':
                        self.lprint('stack:')
                        for item in self.stack:
                            self.lprint(item)
                        self.lprint('end')
                    elif stmt.name == '.':
                        self.lprint(repr(self.ptr))
                    elif stmt.name == '..':
                        if self.stack:
                            save_ptr, save_ptrname = self.stack.pop()
                    elif stmt.name == 'version':
                        try:
                            self.lprint(config.version.__version__)
                        except:
                            self.lprint('unknown')
                    break
                else:
                    try:
                        obj = self.handle_statement(stmt, iterator)
                        if obj is not None:
                            self.ptr = obj
                            if hasattr(obj, 'key_repr'):
                                self.ptrname = obj.key_repr()
                            else:
                                self.ptrname = stmt.name
                    except KeyError:
                        self.lprint('object not found')
                        self.errors += 1
                        return indent
                    except:
                        self.errors += 1
                        traceback.print_exc()
        except SystemExit:
            raise
        finally:
            if obj is not None:
                self.stack.append((save_ptr, save_ptrname))
            else:
                self.ptr, self.ptrname = save_ptr, save_ptrname
        return indent

    def handle(self, text, indent=0):
        parser = Parser(text)
        for sentence in parser.sentences:
            indent = self.handle_sentence(sentence, indent)
        return indent
