# Generated by Django 5.0.6 on 2024-05-31 18:59

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("conversion", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="conversion",
            old_name="user_id",
            new_name="user",
        ),
    ]
