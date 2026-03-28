from django.db import migrations


def create_initial_categories(apps, schema_editor):
    Category = apps.get_model('product', 'Category')
    initial_categories = [
        '衣物',
        '零食',
        '生活用品',
        '娱乐用品',
        '饲料',
        '数码产品',
        '学习用品',
        '其他',
    ]
    for name in initial_categories:
        Category.objects.get_or_create(name=name, parent=None)


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0003_product_keywords'),
    ]

    operations = [
        migrations.RunPython(create_initial_categories, migrations.RunPython.noop),
    ]
