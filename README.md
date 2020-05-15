# NetBox Onboaring plugin

<!-- Build status with linky to the builds for ease of access. -->
[![Build Status](https://travis-ci.com/networktocode/ntc-netbox-plugin-onboarding.svg?token=29s5AiDXdkDPwzSmDpxg&branch=master)](https://travis-ci.com/networktocode/ntc-netbox-plugin-onboarding)

<!-- TODO: https://github.com/networktocode/ntc-netbox-plugin-onboarding/issues/3

Improve this readme with accurate descriptions of what this does, as well as
appropriate links to rendered documentation and standard sections such as:

## Installation

## Usage

## Contributing

-->


```
invoke --list
Available tasks:

  build            Build all docker images.
  cli              Launch a bash shell inside the running NetBox container.
  create-user      Create a new user in django (default: admin), will prompt for password
  debug            Start NetBox and its dependencies in debug mode.
  destroy          Destroy all containers and volumes.
  makemigrations   Run Make Migration in Django
  nbshell          Launch a nbshell session.
  start            Start NetBox and its dependencies in detached mode.
  stop             Stop NetBox and its dependencies.
```
