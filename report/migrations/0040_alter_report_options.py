# Generated by Django 5.1.1 on 2025-07-04 04:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0039_report_donors_report_submissions'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='report',
            options={'permissions': [('can_edit_locked_report', 'Can edit locked report')], 'verbose_name': 'Report', 'verbose_name_plural': 'Reports'},
        ),
    ]
