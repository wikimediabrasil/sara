# Generated by Django 4.1.5 on 2023-03-10 18:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gender', models.CharField(blank=True, choices=[('M', 'Male'), ('F', 'Female'), ('NB', 'Non Binary'), ('?', 'Other')], default='X', max_length=2, null=True)),
                ('wiki_handle', models.CharField(blank=True, max_length=50, null=True)),
                ('twitter', models.CharField(blank=True, max_length=100, null=True)),
                ('facebook', models.CharField(blank=True, max_length=100, null=True)),
                ('instagram', models.CharField(blank=True, max_length=100, null=True)),
                ('linkedin', models.CharField(blank=True, max_length=100, null=True)),
                ('lattes', models.CharField(blank=True, max_length=100, null=True)),
                ('orcid', models.CharField(blank=True, max_length=100, null=True)),
                ('google_scholar', models.CharField(blank=True, max_length=100, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User profile',
                'verbose_name_plural': 'User profiles',
            },
        ),
        migrations.CreateModel(
            name='TeamArea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=420)),
                ('code', models.CharField(max_length=105)),
                ('manager', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manager', to='users.userprofile')),
            ],
            options={
                'verbose_name': 'Team area',
                'verbose_name_plural': 'Team areas',
            },
        ),
    ]
