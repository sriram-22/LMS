# Generated by Django 5.1.3 on 2025-01-09 12:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0027_rename_coursevideos_coursevideo"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="CourseComments",
            new_name="CourseComment",
        ),
        migrations.RenameModel(
            old_name="CourseLikes",
            new_name="CourseLike",
        ),
    ]