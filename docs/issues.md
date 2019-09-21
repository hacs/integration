# Issues

[First lets start out by stating that **ALL** issues should be reported here.](https://github.com/custom-components/hacs/issues)

# What should be in the issue?

When you create an issue in the repository for HACS, you start by selecting a template.

All templates have a defined structure and it is **expected** that you folow it.

_Issues that are missing required information can (will) be closed._

![template](images/select_issue_template.png)

## Feature request

You select this when you have an idea on how HACS could be better.

To be able to handle a feature request you need to write a good description, it should show that this is something that you have invested time in.

You can see examples of good/bad feature requests further down on this page.

## Flag

This should **only** be used, when there is grounds for removing (blacklisting) a repository in HACS.

When you are flagging a repository you need to supply at least these:

- A good description for why.
- The name of the repository.
- Proof that you have tried to contact the owner of that repository (link to issue)

_If you are flagging it because you don't like it, have issues with it, or it's not working, you should report that to the repository and not here._

## Issues

You use this when you have issues with HACS.

[To enable debug logs for HACS (required when adding an issue) have a look here](https://hacs.netlify.com/#logs).

Logs are **more** then _just_ errors, with debug logging it gives the person investigating the issue a full picture of what happened.

**A issue should contain at least:**

- The version of HACS you are using.
- A GOOD description of the issue.
- Debug logs.
- Steps to reproduce the issue.
- If the issue is in the UI, add screenshots.

You can see examples of good/bad issues further down on this page.

_Issues that are missing required information can (will) be closed._

oh... and almost forgot... `latest` is **NOT** a version.

# Examples

This is a collection of good/bad feature requests/issues.

## Examples of bad feature requests

```text
Is it possible to get a persistent notification if there is a component or card has a upgrade?
```

***

```text
# Describe the solution you'd like
Could be possible to add support for python_scripts?

# Describe alternatives you've considered
custom_updater support them.
```

## Examples of good feature requests

```text
# Is your feature request related to a problem? Please describe.
I'm always frustrated when the different plugins and Lovelace cards don't have a decent description.

For me, HACS is also a way to find new components of which I didn't know they even existed. But, a lot of the integration and components don't provide decent info. This requires me to navigate to the repository and sometimes even the source code to find out what the component is about.

# Describe the solution you'd like
Require a minimum amount of info (good description, info.md) before inclusion in HACS and perhaps a tagging system of what the integration/plugin is about.

Examples of tags would be: Denkovi (manufacturer), Ethernet relay (product type), ...
```

***

```text
# Describe the solution you'd like
One benefit of AppDaemon that I think is underutilized is how reusable and shareable apps are. I think a lot of Home Assistant users are put off by the learning curve of learning Python to use AppDaemon. However, it's very possible for people to create apps that anyone can use without modifying the underlying Python code, that just take some YAML configuration to set up. It would be great to be able to have a section in HACS, in addition to custom components and Lovelace plugins, for custom AppDaemon apps that could auto update.

# Describe alternatives you've considered
If this isn't something you're interested in implementing with HACS, I've looked at some other options for having apps auto update, but I think this would be the cleanest route and would put everything custom in one interface.

# Additional context
Apps would land in the appdaemon/apps/<app_name> folder. And I think it would be possible to pull the suggested YAML configuration out and include it in HACS like Lovelace plugins do.

Also, I would be happy to take this on myself and put in a PR. But I wanted to run the idea by you before I start any work on it to see if it's something you'd be willing to merge or implement.
```

## Examples of bad issues

```text

```
_Yes the issue was blank it only had a header 'CCH Settings'_


***

```text
Version of HACS
Describe the bug
A clear and concise description of what the bug is.

Debug log

Add your logs here.
```
_The description of the issue only contained the template but it had a header 'Blows up on update.'_

***

```text
Version of HACS
Describe the bug
A clear and concise description of what the bug is.

Debug log

Add your logs here.
```
_The description of the issue only contained the template but it had a header 'zod'_

***

```text
[Expecting value: line 1 column 1 (char 0)] Restore Failed!
11:51 AM custom_components/hacs/hacsbase/data.py (CRITICAL)
I checked and it exactly how its supposed to be
even replaced the whole hacs folder with a fresh download
```

## Examples of good issues

_Good issues have to much text to extract it (some also have screenshots) but here is a few links:_

- [https://github.com/custom-components/hacs/issues/452](https://github.com/custom-components/hacs/issues/452)
- [https://github.com/custom-components/hacs/issues/470](https://github.com/custom-components/hacs/issues/470)
- [https://github.com/custom-components/hacs/issues/356](https://github.com/custom-components/hacs/issues/356)

# Last words

The more time/words/examples you put in your issue, the faster someone can see/understand what you mean.

[**ALL** issues with HACS should be reported here.](https://github.com/custom-components/hacs/issues)