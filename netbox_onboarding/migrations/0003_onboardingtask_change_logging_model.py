from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_onboarding", "0002_onboardingdevice"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingtask", name="created", field=models.DateField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="onboardingtask", name="last_updated", field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterModelOptions(name="onboardingtask", options={},),
        migrations.RemoveField(model_name="onboardingtask", name="created_on",),
    ]
