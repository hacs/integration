---
id: events
title: Events
---

When HACS operate it will fire some events that the frontend listens to.

These events can also be used in automations.

### Events:

- `hacs/update`
- `hacs/repository`


### Automation example

This will create a new `persistent_notification` every time a new repository is added to HACS.

```yaml
automation:
  trigger:
    platform: event
    event_type: hacs/repository
    event_data:
      action: registration
  action:
    service: persistent_notification.create
    data_template:
      title: New repository in HACS
      message: "{{ trigger.event.data.repository }} was just added to HACS."
```