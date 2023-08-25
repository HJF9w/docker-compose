https://github.com/docker-library/docs/blob/master/influxdb/README.md
https://docs.influxdata.com/influxdb/v2.7/upgrade/v1-to-v2/docker/#influxdb-2x-initialization-credentials

Set the bind mount permissions to 472: for grafana

When installing the python requirements with "pip install -r requirements" you get an error since Debian 12 bookworm.
You can override this with "pip install --break-system-packages -r requirements" or use a venv (but I had no luck with that).

Create a venv with "python -m venv venv".
Enter the venv with ". venv/bin/activate" or for use with cronjobs instead of "/usr/bin/python" "./venv/bin/python".
install the requirements in venv "pip install -r requirements.txt".
upgrade the requirements "pip install --upgrade -r requirements.txt".
To exit the venv, use "deactivate".


sources:
https://www.pegelonline.wsv.de/gast/karte/standard
fam-lange.de
