{%- if version_installed == "master" %}
## You are running master!

This is **only** intended for development!

{%- elif (version_installed.split(".")[1] | int) < 17 %}
## DO NOT UPGRADE TO THE LATEST VERSION!

First upgrade to version [0.16.3](https://github.com/hacs/integration/releases/tag/0.16.3), then upgrade to the latest version.
{% endif %}
## Useful links

- [General documentation](https://hacs.xyz/)
- [Configuration](https://hacs.xyz/docs/configuration/start)
- [FAQ](https://hacs.xyz/docs/faq/what)
- [GitHub](https://github.com/hacs)
- [Forum post](https://community.home-assistant.io/t/custom-component-hacs/121727)
- [Discord](https://discord.gg/apgchf8)
- [Become a GitHub sponsor? ❤️](https://github.com/sponsors/ludeeus)
