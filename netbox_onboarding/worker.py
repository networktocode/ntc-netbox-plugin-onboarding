"""Worker code for processing inbound OnboardingTasks.

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
import logging
import time

from django_rq import job

from .models import OnboardingTask
from .onboard import NetboxKeeper, NetdevKeeper, OnboardException
from .choices import OnboardingStatusChoices, OnboardingFailChoices

logger = logging.getLogger("rq.worker")
logger.setLevel(logging.DEBUG)


@job("default")
def onboard_device(task_id, credentials):
    """Process a single OnboardingTask instance."""
    username = credentials.username
    password = credentials.password

    try:
        ot = OnboardingTask.objects.get(id=task_id)
    except OnboardingTask.DoesNotExist:
        # TODO: maybe we started before the DB was done writing it, or maybe it was deleted out from under us?
        time.sleep(1)
        ot = OnboardingTask.objects.get(id=task_id)

    logging.info("START: onboard device")

    try:
        ot.status = OnboardingStatusChoices.STATUS_RUNNING
        ot.save()

        netdev = NetdevKeeper(ot, username, password)
        nbk = NetboxKeeper(netdev=netdev)

        netdev.get_required_info()
        nbk.ensure_device()

    except OnboardException as exc:
        ot.status = OnboardingStatusChoices.STATUS_FAILED
        ot.failed_reason = exc.reason
        ot.message = exc.message
        ot.save()
        # return dict(ok=False)
        raise

    except Exception as exc:
        ot.status = OnboardingStatusChoices.STATUS_FAILED
        ot.failed_reason = OnboardingFailChoices.FAIL_GENERAL
        ot.message = str(exc)
        ot.save()
        raise

    logging.info("FINISH: onboard device")
    ot.status = OnboardingStatusChoices.STATUS_SUCCEEDED
    ot.save()

    return dict(ok=True)
