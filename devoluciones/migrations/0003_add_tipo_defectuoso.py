from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devoluciones', '0002_devolucion_metodo_pago_reembolso'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devolucion',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('NORMAL', 'Normal'),
                    ('DEFECTUOSO', 'Defectuoso'),
                    ('GARANTIA', 'Garantía'),
                    ('EXTRAORDINARIA', 'Extraordinaria'),
                ],
                default='NORMAL',
                max_length=20,
            ),
        ),
    ]
