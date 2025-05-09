# -*- coding: utf-8 -*-
# flake8: noqa
# Generated by Django 1.9 on 2016-01-27 16:29
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="A",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="B",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "a",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="b",
                        to="tests.A",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="C",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "b",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cs",
                        to="tests.B",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Cat",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="D",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="Dog",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("fur_color", models.TextField()),
                ("origin", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("status", models.TextField(default=b"current")),
            ],
        ),
        migrations.CreateModel(
            name="Group",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="Horse",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("origin", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("blob", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="Permission",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("code", models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("display_name", models.TextField()),
                ("thumbnail_url", models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("last_name", models.TextField()),
                (
                    "groups",
                    models.ManyToManyField(related_name="users", to="tests.Group"),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tests.Location",
                    ),
                ),
                (
                    "permissions",
                    models.ManyToManyField(related_name="users", to="tests.Permission"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Zebra",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField()),
                ("origin", models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name="profile",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, to="tests.User"
            ),
        ),
        migrations.AddField(
            model_name="group",
            name="permissions",
            field=models.ManyToManyField(related_name="groups", to="tests.Permission"),
        ),
        migrations.AddField(
            model_name="event",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="tests.Location",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="users",
            field=models.ManyToManyField(to="tests.User"),
        ),
        migrations.AddField(
            model_name="cat",
            name="backup_home",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="friendly_cats",
                to="tests.Location",
            ),
        ),
        migrations.AddField(
            model_name="cat",
            name="home",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="tests.Location"
            ),
        ),
        migrations.AddField(
            model_name="cat",
            name="hunting_grounds",
            field=models.ManyToManyField(
                related_name="annoying_cats",
                related_query_name=b"getoffmylawn",
                to="tests.Location",
            ),
        ),
        migrations.AddField(
            model_name="cat",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="kittens",
                to="tests.Cat",
            ),
        ),
        migrations.AddField(
            model_name="c",
            name="d",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="tests.D"
            ),
        ),
    ]
