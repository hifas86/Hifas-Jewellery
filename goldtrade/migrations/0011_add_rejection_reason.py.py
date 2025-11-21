from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('goldtrade', '0010_alter_bankdeposit_user_alter_goldrate_buy_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kyc',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
    ]
