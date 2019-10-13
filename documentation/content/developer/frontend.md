---
id: frontend
title: Frontend
---

_All changes to the documentation should go against the `master` branch._

<pre class="prism-code language-bash codeBlock_19pQ">
    <h4>Note!</h4>
    Untill the new eperimental UI are default in HACS, you need to enable that to test your changes.
</pre>

<pre class="prism-code language-bash codeBlock_19pQ">
    <h4>Note!</h4>
    Contributions to the "old" UI will not be accepted.
</pre>

First spin up the [devcontainer](/docs/developer/devcontainer)

When you have that running issue the following comands:

```bash
cd frontend
npm install
npm start
```

Now start up Home Assistant, you can run `dc start` or select the Task _"Run Home Assistant on port 9123"_.

After some time Home Assistant will be running on http://localhost:9123

Complete the onboarding, [add HACS as an integration in the UI.](/docs/configuration/basic)

All the frontend files are located under:

```
frontend/src/
```
