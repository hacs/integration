from astpath import search

checks = set()


def add(f):
    checks.add(f)
    return f


def find(string):
    return search(".", string, print_matches=False)


def log(severity, filename, line, message):
    print(f"::{severity} file={filename[2:]}, line={line}:: {message}")


@add
def findForLoopsContainingAwait():
    message = "Do not await in a for loop, use asyncio.gather"
    for line in find("//AsyncFunctionDef[body//For/body//Await]"):
        log("error", line[0], line[1], message)


for check in checks:
    check()
