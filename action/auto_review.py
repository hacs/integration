import os
from astpath import search

checks = set()
exitinformation = {"code": 0}

GITHUB_ACTION = os.getenv("GITHUB_ACTION")


def add(f):
    checks.add(f)
    return f


def find(string):
    return search(".", string, print_matches=False)


def formatOutput(filename, line, message, error=True):
    if error:
        exitinformation["code"] = 1
    print(f"{filename}:{line}")
    if GITHUB_ACTION:
        print(
            f"::{'error' if error else 'warning'} file={filename[2:]},line={line}:: {message}"
        )
    else:
        print(f"{message}\n")


@add
def findForLoopsContainingAwait():
    message = "Do not await in a for loop, use asyncio.gather"
    for line in find("//AsyncFunctionDef[body//For/body//Await]"):
        formatOutput(line[0], line[1], message)


for check in checks:
    check()

exit(exitinformation["code"])
