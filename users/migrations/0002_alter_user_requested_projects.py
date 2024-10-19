# Generated by Django 4.2.16 on 2024-10-19 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_project_requested'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='requested_projects',
            field=models.ManyToManyField(blank=True, related_name='users_requested_projects', to='projects.project'),
        ),
    ]
