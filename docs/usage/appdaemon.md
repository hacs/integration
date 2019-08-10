# AppDaemon

_AppDaemon setup varies depending on your Home Assistant setup._

## With Hass.io

Setup with the Hass.io AppDaemon add-on is straightforward. By default, your apps directory should be `/config/appdaemon/apps`. Apps from HACS will be placed in subfolders
under there. Just update `/config/appdaemon/apps/apps.yaml` with the information from the app's README to set up an app from HACS in AppDaemon.

## AppDaemon in Docker

Install AppDaemon using [this tutorial.](https://appdaemon.readthedocs.io/en/stable/DOCKER_TUTORIAL.html)

To allow AppDaemon to run HACS installed files in HA you need to bind the correct folder to the `conf` folder for AD. You will modify the -v binding to “<your_HA_config_directory>/appdaemon:/conf”

Here is an example docker run command, but you need to make sure you rename your path to the correct HA config directory:

`sudo docker run -d --name="appdaemon" --restart=unless-stopped -p 5050:5050 -e HA_URL="http://<your_HA_IP:PORT>" -v <your_HA_config_directory>/appdaemon:/conf -v /etc/localtime:/etc/localtime:ro -e TOKEN="<your_HA_AD_Token>" -e DASH_URL="http://$HOSTNAME:5050" acockburn/appdaemon:latest`

Make sure you change the permissions on the appdaemon conf directory in the HA config directory to allow HACS to write that folder.

## Other Setups

If you have AppDaemon set up in a different way (for example, on a different machine), it is still likely possible but not yet documented on how to set
it up with HACS. If you have set up AppDaemon and HACS with a different setup than the above, pull requests to this documentation are welcomed.
