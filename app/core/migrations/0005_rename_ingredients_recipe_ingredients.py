# Generated by Django 3.2.25 on 2024-06-26 12:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20240625_1218'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recipe',
            old_name='Ingredients',
            new_name='ingredients',
        ),
    ]