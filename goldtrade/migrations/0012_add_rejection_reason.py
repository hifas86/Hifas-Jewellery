from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('goldtrade', '0011_auto_20251121_1359'),
    ]

    operations = [
        migrations.AddField(
            model_name='kyc',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
    ]
