---
id: logs
title: Logs
---

Like any other integration this logs to the `home-assistant.log` file.

You can also click the "OPEN LOG" from the "SETTINGS" tab to show logs only related to this integration (useful when creating a issue)

To enable `debug` logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    hacs: debug
```