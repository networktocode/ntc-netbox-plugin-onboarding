from django.db import migrations


def create_missing_onboardingdevice(apps, schema_editor):
    Device = apps.get_model("dcim", "Device")
    OnboardingDevice = apps.get_model("netbox_onboarding", "OnboardingDevice")

    for device in Device.objects.filter(onboardingdevice__isnull=True):
        OnboardingDevice.objects.create(device=device)


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_onboarding", "0003_onboardingtask_change_logging_model"),
    ]

    operations = [
        migrations.RunPython(create_missing_onboardingdevice),
    ]
