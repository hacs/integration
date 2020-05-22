{%- if version_installed == "master" %}

## You are running master!

This is **only** intended for development!

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
