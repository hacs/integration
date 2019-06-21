# Installation using the terminal

To download via terminal, make sure you have `git` installed.

Next, Navigate to your custom_components directory:

`cd /config/custom_components` # This location is different from installation to installation (see step 5).

Then run the following commands:

```bash
git clone https://github.com/custom-components/hacs.git hacs_temp
cd hacs_temp
git checkout $(git describe --tags $(git rev-list --tags --max-count=1))
cd ../
cp -r hacs_temp/custom_components/hacs hacs
rm -R hacs_temp
```

[You should now be done, next part will be to add it to your configuration.](../configuration)
