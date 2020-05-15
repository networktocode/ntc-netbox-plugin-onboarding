# NetBox Onboarding plugin

<!-- Build status with linky to the builds for ease of access. -->
[![Build Status](https://travis-ci.com/networktocode/ntc-netbox-plugin-onboarding.svg?token=29s5AiDXdkDPwzSmDpxg&branch=master)](https://travis-ci.com/networktocode/ntc-netbox-plugin-onboarding)

A plugin for [NetBox](https://github.com/netbox-community/netbox) to easily onboard new devices.

`ntc-netbox-plugin-onboarding` is leverating Netmiko, NAPALM & Django-RQ to simplify the onboarding process of a new device into NetBox down to an IP Address and a site.
The goal of this plugin is not to import everything about a device into NetBox but rather to help build quickly an inventory in NetBox that is often the first step into an automation journey.

## Installation

The plugin is available as a Python package in pypi and can be installed with pip
```shell
pip install ntc-netbox-plugin-onboarding
```

Once installed, the plugin need to be enabled in your `configuration.py`
```python
# In your configuration.py
PLUGINS = ["netbox_onboarding"]

# If need you can override the default settings of the plugin too
# PLUGINS_CONFIG = {
#   "netbox_onboarding": {
#         "create_platform_if_missing": True,
#         "create_manufacturer_if_missing": True,
#         "create_device_type_if_missing": True,
#         "create_device_role_if_missing": True,
#         "default_device_role": "network",
#   }
# }
```

## Usage
### Preparation

The work properly the plugin need to know the Site, Platform, Device Type, Device Role of each device as well as its IP primary IP address.
It's recommended to create these objects in NetBox ahead of time and to provide them when you want to start the onboarding process.

If `Platform`, `Device Type` and/or `Device Role` are not provided, the plugin will try to identify these information automatically and, based on the settings, it can create them in NetBox as needed.
> If the Platform is provided, it must contains a valid Napalm driver available to the worker in Python

### Onboard a new device

A new device can be onboarded via :
- A web form
- A CSV form to import multiple devices in bulk. `/plugins/onboarding/import/`
- An API, `POST /plugins​/onboarding​/onboarding​/`

### Consult the status of onboarding tasks

The status of the onboarding process for each device is maintain is a dedicated table in NetBox and can be retrive :
- Via the UI `/plugins/onboarding/`
- Via the API `GET /plugins​/onboarding​/onboarding​/`

<ADD SCREEN SHOT HERE>

### API

The plugin comes with 4 new API endpoints to manage devices onbarding tasks

```shell
GET        /plugins​/onboarding​/onboarding​/       Check status of all onboarding tasks.
POST    ​   /plugins​/onboarding​/onboarding​/       Onboard a new device
GET     ​   /plugins​/onboarding​/onboarding​/{id}​/  Check the status of a specific onboarding task
DELETE    ​ /plugins​/onboarding​/onboarding​/{id}​/  Delete a specific onboarding task
```

## Contributing

Pull requests are welcomed and automatically built and tested against multiple version of Python and multiple version of NetBox through TravisCI.

The project is packaged with a light development environment based on docker-compose to help with the local development of the project and to run the tests within TravisCI.

The project is following Network to Code software development guideline and is leveraging:
- Black, Pylint, Bandit and pydocstyle for Python format
- Django unit test to ensure the plugin is working properly.

### CLI Helper Commands

The project is coming with a CLI helper based on `invoke` to help setup the development environment. The commands are listed below in 3 categories `dev environment`, `utility` and `testing`. 

Each command can be executed with `invoke <command>`
All commands support the arguments `--netbox-ver` and `--python-ver` if you want to manually the version of Python and NetBox to use. Each command also has its own help `invoke <command> --help`

#### Local dev environment
```
  build            Build all docker images.
  debug            Start NetBox and its dependencies in debug mode.
  destroy          Destroy all containers and volumes.
  start            Start NetBox and its dependencies in detached mode.
  stop             Stop NetBox and its dependencies.
```

#### Utility 
```
  cli              Launch a bash shell inside the running NetBox container.
  create-user      Create a new user in django (default: admin), will prompt for password.
  makemigrations   Run Make Migration in Django.
  nbshell          Launch a nbshell session.
```
#### Testing 

```
  tests            Run all tests for this plugin.
  pylint           Run pylint code analysis.
  pydocstyle       Run pydocstyle to validate docstring formatting adheres to NTC defined standards.
  bandit           Run bandit to validate basic static code security analysis.
  black            Run black to check that Python files adhere to its style standards.
  unittest         Run Django unit tests for the plugin.
```

## Questions

For any questions or comments, please check the [FAQ](FAQ.md) first and feel free to swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode).
Sign up [here](http://slack.networktocode.com/)
