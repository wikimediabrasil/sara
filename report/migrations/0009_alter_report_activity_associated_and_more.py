# Generated by Django 4.1.7 on 2023-04-22 22:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_userprofile_gender_alter_userprofile_user'),
        ('metrics', '0001_initial'),
        ('report', '0008_alter_report_activity_associated_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='activity_associated',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='activity_associated', to='metrics.activity'),
        ),
        migrations.AlterField(
            model_name='report',
            name='activity_other',
            field=models.TextField(blank=True, default='', max_length=420, null=True),
        ),
        migrations.AlterField(
            model_name='report',
            name='area_activated',
            field=models.ManyToManyField(related_name='area_activated', to='report.areaactivated'),
        ),
        migrations.AlterField(
            model_name='report',
            name='commons_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='commons_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='created_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.RESTRICT, related_name='user_reporting', to='users.userprofile'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='report',
            name='editors',
            field=models.ManyToManyField(related_name='editors', to='report.editor'),
        ),
        migrations.AlterField(
            model_name='report',
            name='mediawiki_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='mediawiki_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='metawiki_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='metawiki_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='modified_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.RESTRICT, related_name='user_modifying', to='users.userprofile'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='report',
            name='organizers',
            field=models.ManyToManyField(related_name='organizers', to='report.organizer'),
        ),
        migrations.AlterField(
            model_name='report',
            name='partners_activated',
            field=models.ManyToManyField(related_name='partners', to='report.partner'),
        ),
        migrations.AlterField(
            model_name='report',
            name='public_communication',
            field=models.TextField(blank=True, max_length=10000, null=True),
        ),
        migrations.AlterField(
            model_name='report',
            name='technologies_used',
            field=models.ManyToManyField(related_name='tecnologies', to='report.technology'),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikibooks_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikibooks_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikidata_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikidata_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikinews_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikinews_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikipedia_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikipedia_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikiquote_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikiquote_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikisource_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikisource_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikispecies_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikispecies_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikiversity_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikiversity_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikivoyage_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wikivoyage_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wiktionary_created',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AlterField(
            model_name='report',
            name='wiktionary_edited',
            field=models.IntegerField(blank=True, default=0),
        ),
    ]
