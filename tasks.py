"""
(c) 2020 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from invoke import task

PYTHON_VER = os.getenv("PYTHON_VER", "3.7")
NETBOX_VER = os.getenv("NETBOX_VER", "master")

# Name of the docker image/container
NAME = os.getenv("IMAGE_NAME", "ntc-netbox-plugin-onboarding")
PWD = os.getcwd()

COMPOSE_FILE = "development/docker-compose.yml"
BUILD_NAME = "netbox_onboarding"


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task
def build(context, netbox_ver=NETBOX_VER, python_ver=PYTHON_VER):
    """Build all docker images.

    Args:
        context (obj): Used to run specific commands
        netbox_ver (str): NetBox version to use to build the container
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} build --build-arg netbox_ver={netbox_ver} --build-arg python_ver={python_ver}",
        env={"NETBOX_VER": netbox_ver, "PYTHON_VER": python_ver},
    )


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context):
    """Start NetBox and its dependencies in debug mode."""

    print("Starting Netbox .. ")
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} up",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )


@task
def start(context):
    """Start NetBox and its dependencies in detached mode."""

    print("Starting Netbox in detached mode.. ")
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} up -d",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )


@task
def stop(context):
    """Stop NetBox and its dependencies."""

    print("Stopping Netbox .. ")
    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} down",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )


@task
def destroy(context):
    """Destroy all containers and volumes."""

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} down",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )
    context.run(
        f"docker volume rm -f {BUILD_NAME}_pgdata_netbox_onboarding",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context):
    """Launch a nbshell session."""

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox python manage.py nbshell",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
        pty=True,
    )


@task
def cli(context):
    """Launch a bash shell inside the running NetBox container."""

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox bash",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
        pty=True,
    )


@task
def create_user(context, user="admin"):
    """Create a new user in django (default: admin), will prompt for password"""

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox python manage.py createsuperuser --username {user}",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
        pty=True,
    )


@task
def makemigrations(context):
    """Run Make Migration in Django"""

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} up -d postgres",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox python manage.py makemigrations",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )

    context.run(
        f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} down",
        env={"NETBOX_VER": NETBOX_VER, "PYTHON_VER": PYTHON_VER},
    )


# ------------------------------------------------------------------------------
# TESTS / LINTING
# ------------------------------------------------------------------------------
@task
def unittest(context):
    """Run Django unit tests for the plugin.

    Args:
        context (obj): Used to run specific commands
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox"
    context.run(f'{docker} sh -c "python manage.py test netbox_onboarding"', pty=True)


@task
def pylint(context):
    """Run pylint code analysis.

    Args:
        context (obj): Used to run specific commands
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox"
    # We exclude the /migrations/ directory since it is autogenerated code
    context.run(
        f"{docker} sh -c \"cd /source && find . -name '*.py' -not -path '*/migrations/*' | "
        'PYTHONPATH=/opt/netbox/netbox xargs pylint"',
        pty=True,
    )


@task
def black(context):
    """Run black to check that Python files adhere to its style standards.

    Args:
        context (obj): Used to run specific commands
    """
    docker = f"docker-compose -f {COMPOSE_FILE} -p {BUILD_NAME} run netbox"
    context.run(f'{docker} sh -c "cd /source && black --check --diff ."', pty=True)


# @task
# def pylama(context, name=NAME, python_ver=PYTHON_VER):
#     """This will run pylama for the specified name and Python version.

#     Args:
#         context (obj): Used to run specific commands
#         name (str): Used to name the docker image
#         python_ver (str): Will use the Python version docker image to build from
#     """
#     # pty is set to true to properly run the docker commands due to the invocation process of docker
#     # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
#     DOCKER = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
#     context.run(f"{DOCKER} pylama .", pty=True)


# @task
# def pydocstyle(context, name=NAME, python_ver=PYTHON_VER):
#     """This will run pydocstyle to validate docstring formatting adheres to NTC defined standards.

#     Args:
#         context (obj): Used to run specific commands
#         name (str): Used to name the docker image
#         python_ver (str): Will use the Python version docker image to build from
#     """
#     # pty is set to true to properly run the docker commands due to the invocation process of docker
#     # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
#     DOCKER = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
#     context.run(f"{DOCKER} pydocstyle .", pty=True)


# @task
# def bandit(context, name=NAME, python_ver=PYTHON_VER):
#     """This will run bandit to validate basic static code security analysis.

#     Args:
#         context (obj): Used to run specific commands
#         name (str): Used to name the docker image
#         python_ver (str): Will use the Python version docker image to build from
#     """
#     # pty is set to true to properly run the docker commands due to the invocation process of docker
#     # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
#     DOCKER = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
#     context.run(f"{DOCKER} bandit --recursive ./ --configfile .bandit.yml", pty=True)


@task
def tests(context):
    """Run all tests for this plugin.

    Args:
         context (obj): Used to run specific commands
    """
    # Sorted loosely from fastest to slowest
    print("Running black...")
    black(context)
    print("Running pylint...")
    pylint(context)
    print("Running unit tests...")
    unittest(context)
    # print("Running pylama...")
    # pylama(context, NAME, python_ver)
    # print("Running yamllint...")
    # yamllint(context, NAME, python_ver)
    # print("Running pydocstyle...")
    # pydocstyle(context, NAME, python_ver)
    # print("Running bandit...")
    # bandit(context, NAME, python_ver)

    print("All tests have passed!")
