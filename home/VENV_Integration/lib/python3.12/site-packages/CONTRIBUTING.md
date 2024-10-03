<!---

This file serves as an entry point for GitHub's Contributing
Guidelines [1] only.

GitHub doesn't render rST very well, especially in respect to internal
hyperlink targets and cross-references [2]. People also tend to
confuse rST and Markdown syntax. Therefore, instead of keeping the
contents here (and including from rST documentation under doc/), link
to the Sphinx generated docs is provided below.


[1] https://github.com/blog/1184-contributing-guidelines
[2] http://docutils.sourceforge.net/docs/user/rst/quickref.html#hyperlink-targets

-->

# Certbot Contributing Guide

Hi! Welcome to the Certbot project. We look forward to collaborating with you.

If you're reporting a bug in Certbot, please make sure to include:
 - The version of Certbot you're running.
 - The operating system you're running it on.
 - The commands you ran.
 - What you expected to happen, and
 - What actually happened.

If you're a developer, we have some helpful information in our
[Developer's Guide](https://certbot.eff.org/docs/contributing.html) to get you
started. In particular, we recommend you read these sections 

 - [Finding issues to work on](https://certbot.eff.org/docs/contributing.html#find-issues-to-work-on)
 - [Coding style](https://certbot.eff.org/docs/contributing.html#coding-style)
 - [Submitting a pull request](https://certbot.eff.org/docs/contributing.html#submitting-a-pull-request)

# Specific instructions for Josepy

## Configure a development environment

1) Install Poetry: https://python-poetry.org/docs/#installation
2) Setup a Python virtual environment
```bash
$ poetry install -E docs
```
3) Activate the Python virtual environment
```bash
# (On Linux)
$ source .venv/bin/activate
# (On Windows Powershell)
$ .\.venv\Script\activate
```
4) Optionally set up [pre-commit](https://pre-commit.com/) which will cause
simple tests to be automatically run on your changes when you commit them
```bash
$ pre-commit install
```

## Run the tests and quality checks

1) Configure a development environment ([see above](#configure-a-development-environment))
2) Run the tests
```bash
$ tox
```
3) You can also run specific tests
```bash
$ tox -e py
```
You can get a listing of the available tests by running
```bash
$ tox -l
```
