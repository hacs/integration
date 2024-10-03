import code
import getpass
import socket
import sys

from pyroute2.cli.session import Session
from pyroute2.ndb.main import NDB


class Console(code.InteractiveConsole):
    def __init__(self, stdout=None, log=None, sources=None):
        self.db = NDB(log=log, sources=sources)
        self.db.config.update(
            {'show_format': 'json', 'recordset_pipe': 'true'}
        )
        self.stdout = stdout or sys.stdout
        self.session = Session(self.db, self.stdout, self.set_prompt)
        self.matches = []
        self.isatty = sys.stdin.isatty()
        self.prompt = ''
        self.set_prompt()
        code.InteractiveConsole.__init__(self)

    def close(self):
        self.db.close()

    def help(self):
        self.session.lprint(
            "Built-in commands: \n"
            "exit\t-- exit cli\n"
            "ls\t-- list current namespace\n"
            ".\t-- print the current object\n"
            ".. or Ctrl-D\t-- one level up\n"
        )

    def set_prompt(self, prompt=None):
        if self.isatty:
            if prompt is not None:
                self.prompt = '%s > ' % (prompt)
            else:
                self.prompt = '%s > ' % (self.session.ptr.__class__.__name__)
            self.prompt = '%s@%s : %s' % (
                getpass.getuser(),
                (socket.gethostname().split('.')[0]),
                self.prompt,
            )

    def loadrc(self, fname):
        with open(fname, 'r') as f:
            self.session.handle(f.read())

    def interact(self, readfunc=None):
        if self.isatty and readfunc is None:
            self.session.lprint("pyroute2 cli prototype")

        if readfunc is None:
            readfunc = self.raw_input

        indent = 0
        while True:
            try:
                text = readfunc(self.prompt)
            except EOFError:
                if self.session.stack:
                    self.session.stack_pop()
                    continue
                else:
                    self.close()
                    break
            except Exception:
                self.close()
                break

            try:
                indent = self.session.handle(text, indent)
            except SystemExit:
                self.close()
                return
            except:
                self.showtraceback()
                continue

    def set_completer(self, readline):
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.completer)
        readline.set_completion_display_matches_hook(self.display)

    def completer(self, text, state):
        if state == 0:
            d = [x for x in dir(self.session.ptr) if x.startswith(text)]
            if isinstance(self.session.ptr, dict):
                keys = [str(y) for y in self.session.ptr.keys()]
                d.extend([x for x in keys if x.startswith(text)])
            self.matches = d
        try:
            return self.matches[state]
        except:
            pass

    def display(self, line, matches, length):
        self.session.lprint()
        self.session.lprint(matches)
        self.session.lprint('%s%s' % (self.prompt, line), end='')


if __name__ == '__main__':
    Console().interact()
