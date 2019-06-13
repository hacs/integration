***

[HOME](/hacs/) | [INSTALLATION](/hacs/install) | [**CONFIGURATION**](/hacs/configure) | [TOKEN](/hacs/token)

***
# Configuration

Configuration for this is quite simple.

Only two lines are needed/supported.

```yaml
hacs:
  token: !secret my_github_access_token
```

**NB! This needs to be in `configuration.yaml`, _not_ in a "package".**

[To generate a GitHub Personal Access Token that you can use have a look here.](https://custom-components.github.io/hacs/token)