{%- if version_installed == "master" %}

## You are running master!

This is **only** intended for development!

{%- elif (version_installed.split(".")[1] | int) < 17 and version_installed != "0.16.3" %}

## DO NOT UPGRADE TO THE LATEST VERSION!

First upgrade to version [0.16.3](https://github.com/hacs/integration/releases/tag/0.16.3), then upgrade to the latest version.
{%- elif (version_installed.split(".")[0] | int) < 1 %}

# Breaking changes!

Read the release notes!
{% endif %}

## Useful links

- [General documentation](https://hacs.xyz/)
- [Configuration](https://hacs.xyz/docs/configuration/start)
- [FAQ](https://hacs.xyz/docs/faq/what)
- [GitHub](https://github.com/hacs)
- [Discord](https://discord.gg/apgchf8)
- [Become a GitHub sponsor? ❤️](https://github.com/sponsors/ludeeus)
- [BuyMe~~Coffee~~Beer? 🍺🙈](https://buymeacoffee.com/ludeeus)
