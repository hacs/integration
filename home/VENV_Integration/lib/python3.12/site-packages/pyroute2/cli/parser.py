import re
import shlex

from pyroute2.cli import (
    t_comma,
    t_dict,
    t_end_of_dict,
    t_end_of_sentence,
    t_end_of_stream,
    t_pipe,
    t_stmt,
)
from pyroute2.common import basestring


class Token(object):
    def __init__(self, lex, expect=(), prohibit=(), leaf=False):
        self.lex = lex
        self.leaf = leaf
        self.kind = 0
        self.name = None
        self.argv = []
        self.kwarg = {}
        self.parse()
        if expect and self.kind not in expect:
            raise SyntaxError('expected %s, got %s' % (expect, self.kind))
        if prohibit and self.kind in prohibit:
            raise SyntaxError('unexpected %s' % (self.name,))

    def convert(self, arg):
        if re.match('^[0-9]+$', arg):
            return int(arg)
        else:
            return arg

    def parse(self):
        # triage
        first = self.lex.get_token()
        self.name = first

        ##
        # no token
        #
        if first == '':
            self.kind = t_end_of_stream

        ##
        # dict, e.g.
        #
        # resource spec, function arguments::
        #   {arg1, arg2}
        #   {key1 value1, key2 value2}
        #   {key {skey1 value}}
        #
        elif first == '{':
            arg_name = None
            while True:
                nt = Token(
                    self.lex, expect=(t_stmt, t_dict, t_comma, t_end_of_dict)
                )
                if arg_name is None:
                    if nt.kind == t_dict:
                        self.argv.append(nt.kwarg)
                    elif nt.kind == t_comma:
                        continue
                    elif nt.kind == t_stmt:
                        arg_name = nt.name
                else:
                    if nt.kind in (t_end_of_dict, t_comma):
                        self.argv.append(arg_name)
                    elif nt.kind == t_stmt:
                        self.kwarg[arg_name] = nt.name
                    elif nt.kind == t_dict:
                        self.kwarg[arg_name] = nt.kwarg
                    arg_name = None

                if nt.kind == t_end_of_dict:
                    self.kind = t_dict
                    self.name = '%s %s' % (self.argv, self.kwarg)
                    return

        ##
        # end of dict
        #
        elif first == '}':
            self.kind = t_end_of_dict

        ##
        # end of sentence
        #
        elif first == ';':
            self.kind = t_end_of_sentence

        ##
        # end of dict entry
        #
        elif first == ',':
            self.kind = t_comma

        ##
        # pipe
        #
        elif first == '|':
            self.kind = t_pipe

        elif first == '=':
            lookahead = self.lex.get_token()
            if lookahead == '>':
                self.name = '=>'
                self.kind = t_pipe
            else:
                self.lex.push_token(lookahead)
                self.kind = t_stmt

        ##
        # simple statement
        #
        # object name::
        #   name
        #
        # function call::
        #   func
        #   func {arg1, arg2}
        #   func {key1 value1, key2 value2}
        #
        else:
            self.name = self.convert(first)
            self.kind = t_stmt


class Sentence(object):
    def __init__(self, text, indent=0, master=None):
        self.offset = 0
        self.statements = []
        self.text = text
        self.lex = shlex.shlex(text)
        self.lex.wordchars += '.:/'
        self.lex.commenters = '#!'
        self.lex.debug = False
        self.indent = indent
        if master:
            self.chain = master.chain
        else:
            self.chain = []
            self.parse()

    def __iter__(self):
        for stmt in self.statements:
            yield stmt

    def parse(self):
        sentence = self
        while True:
            nt = Token(self.lex)
            if nt.kind == t_end_of_sentence:
                sentence = Sentence(None, self.indent, master=self)
            elif nt.kind == t_end_of_stream:
                return
            else:
                sentence.statements.append(nt)
            if sentence not in self.chain:
                self.chain.append(sentence)

    def __repr__(self):
        ret = '----\n'
        for s in self.statements:
            ret += '%i [%s] %s\n' % (self.indent, s.kind, s.name)
            ret += '\targv: %s\n' % (s.argv)
            ret += '\tkwarg: %s\n' % (s.kwarg)
        return ret


class Parser(object):
    def __init__(self, stream):
        self.stream = stream
        self.indent = None
        self.sentences = []
        self.parse()

    def parse(self):
        if hasattr(self.stream, 'readlines'):
            for text in self.stream.readlines():
                self.parse_string(text)
        elif isinstance(self.stream, basestring):
            self.parse_string(self.stream)
        else:
            raise ValueError('unsupported stream')
        self.parsed = True

    def parse_string(self, text):
        # 1. get indentation
        indent = re.match(r'^([ \t]*)', text).groups(0)[0]
        spaces = []
        # 2. sort it
        if indent:
            spaces = list(set(indent))
            if len(spaces) > 1:
                raise SyntaxError('mixed indentation')
            if self.indent is None:
                self.indent = spaces[0]
            if self.indent != spaces[0]:
                raise SyntaxError('mixed indentation')
        sentence = Sentence(text, len(indent))
        self.sentences.extend(sentence.chain)
