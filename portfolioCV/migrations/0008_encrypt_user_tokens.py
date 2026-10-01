from django.db import migrations

import portfolioCV.fields

FIELDS = ['github_token', 'gitlab_token', 'openalex_token', 'nvidia_api_key']


def encrypt_existing(apps, schema_editor):
    UserProfile = apps.get_model('portfolioCV', 'UserProfile')
    for profile in UserProfile.objects.all():
        # Al leer, el valor llega en claro (o descifrado); al guardar se cifra
        profile.save(update_fields=FIELDS)


class Migration(migrations.Migration):

    dependencies = [
        ('portfolioCV', '0007_userprofile_gitlab_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name=name,
            field=portfolioCV.fields.EncryptedCharField(blank=True, default=''),
        ) for name in FIELDS
    ] + [
        migrations.RunPython(encrypt_existing, migrations.RunPython.noop),
    ]
