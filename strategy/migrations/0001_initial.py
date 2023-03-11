# Generated by Django 4.1.5 on 2023-03-10 18:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StrategicAxis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=420)),
            ],
            options={
                'verbose_name': 'Strategic axis',
                'verbose_name_plural': 'Strategic axes',
            },
        ),
        migrations.CreateModel(
            name='Direction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=420)),
                ('strategic_axis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='directions', to='strategy.strategicaxis')),
            ],
            options={
                'verbose_name': 'Direction',
                'verbose_name_plural': 'Directions',
            },
        ),
    ]
