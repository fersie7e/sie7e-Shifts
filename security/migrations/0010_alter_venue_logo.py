# Generated by Django 4.2.7 on 2023-12-13 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0009_alter_venue_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='venue',
            name='logo',
            field=models.ImageField(blank=True, default='sie7e.png', null=True, upload_to=''),
        ),
    ]
