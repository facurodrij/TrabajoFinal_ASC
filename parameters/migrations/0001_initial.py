# Generated by Django 4.1.3 on 2023-10-24 19:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MedioPago',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Nombre')),
            ],
            options={
                'verbose_name': 'Medio de pago',
                'verbose_name_plural': 'Medios de pago',
            },
        ),
        migrations.CreateModel(
            name='Pais',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
            ],
            options={
                'verbose_name': 'País',
                'verbose_name_plural': 'Países',
            },
        ),
        migrations.CreateModel(
            name='Sexo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
            ],
            options={
                'verbose_name': 'Sexo',
                'verbose_name_plural': 'Sexos',
            },
        ),
        migrations.CreateModel(
            name='Provincia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre')),
                ('pais', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='parameters.pais', verbose_name='País')),
            ],
            options={
                'verbose_name': 'Provincia',
                'verbose_name_plural': 'Provincias',
                'unique_together': {('nombre', 'pais')},
            },
        ),
        migrations.CreateModel(
            name='Municipio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('provincia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='parameters.provincia')),
            ],
            options={
                'verbose_name': 'Municipio',
                'verbose_name_plural': 'Municipios',
            },
        ),
        migrations.CreateModel(
            name='Departamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre')),
                ('provincia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='parameters.provincia', verbose_name='Provincia')),
            ],
            options={
                'verbose_name': 'Departamento',
                'verbose_name_plural': 'Departamentos',
                'unique_together': {('nombre', 'provincia')},
            },
        ),
        migrations.CreateModel(
            name='Localidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('categoria', models.CharField(max_length=50)),
                ('departamento', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='parameters.departamento')),
                ('municipio', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='parameters.municipio')),
                ('provincia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='parameters.provincia')),
            ],
            options={
                'verbose_name_plural': 'Localidades',
                'unique_together': {('nombre', 'provincia', 'departamento', 'municipio')},
            },
        ),
    ]
