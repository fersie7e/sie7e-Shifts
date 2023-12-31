# Generated by Django 5.0 on 2023-12-18 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('subtitle', models.CharField(max_length=200)),
                ('link', models.CharField(max_length=200)),
                ('bg_image', models.ImageField(blank=True, default='sie7e.png', null=True, upload_to='images/')),
            ],
        ),
    ]
