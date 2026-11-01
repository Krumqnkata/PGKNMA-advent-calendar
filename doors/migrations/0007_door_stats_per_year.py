# Статистиката по вратички става по години. Таблицата се пресъздава: дотук в нея
# имаше само тестови данни, а смяната на първичния ключ (OneToOne → id) е
# по-надеждна така, отколкото чрез AlterField, особено при MySQL.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doors", "0006_login_attempt_proxy"),
    ]

    operations = [
        migrations.DeleteModel(name="DoorStats"),
        migrations.CreateModel(
            name="DoorStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(verbose_name="година")),
                ("opens", models.PositiveIntegerField(default=0, verbose_name="отваряния")),
                ("hearts", models.PositiveIntegerField(default=0, verbose_name="сърца")),
                ("completions", models.PositiveIntegerField(default=0, verbose_name="изпълнени предизвикателства")),
                (
                    "door",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stats",
                        to="doors.door",
                        verbose_name="вратичка",
                    ),
                ),
            ],
            options={
                "verbose_name": "статистика на вратичка",
                "verbose_name_plural": "статистика по вратички",
                "ordering": ["-year", "door__day"],
                "constraints": [
                    models.UniqueConstraint(fields=("door", "year"), name="unique_door_stats_per_year"),
                ],
            },
        ),
    ]
