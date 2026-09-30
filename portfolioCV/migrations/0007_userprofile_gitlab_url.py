from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolioCV', '0006_rename_gemini_api_key_userprofile_nvidia_api_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='gitlab_url',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
