import json

from django.db import models


class System(models.Model):
    """Система-продюсер или приёмник. Заводится вручную через админку."""

    SOURCE = 'source'
    SINK = 'sink'
    USAGE_CHOICES = [
        (SOURCE, 'Продюсер (пишет в топик)'),
        (SINK, 'Приёмник (куда пишем из Kafka)'),
    ]

    name = models.CharField('Название системы', max_length=128, unique=True)
    usage = models.CharField('Назначение', max_length=8, choices=USAGE_CHOICES)
    code = models.CharField('Код для конфига', max_length=64, blank=True,
                            help_text='Латиница, попадёт в конфиг коннектора. '
                                      'Если пусто — возьмём из названия.')
    order = models.IntegerField('Порядок в списке', default=0)

    class Meta:
        verbose_name = 'Система'
        verbose_name_plural = 'Системы'
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_usage_display()})'

    @property
    def slug_code(self):
        return (self.code or self.name).strip().lower().replace(' ', '-')

class ConnectorKey(models.Model):
    """Ключ, который вводит коннектор. Живёт внутри одной конфигурации."""

    connector = models.ForeignKey('ConnectorConfig', verbose_name='Коннектор',
                                  on_delete=models.CASCADE,
                                  related_name='keys')
    value = models.CharField('Значение ключа', max_length=128)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Ключ коннектора'
        verbose_name_plural = 'Ключи коннекторов'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['connector', 'value'],
                                    name='uniq_key_per_connector'),
        ]

    def __str__(self):
        return self.value

class Transform(models.Model):
    """Шаблон трансформации. Заполняется через страницу настроек.

    config_template — JSON-строка с плейсхолдером {field}, куда подставится
    значение из опросника. Ключи вида transforms.<имя>.<опция>.
    """

    name = models.CharField('Название', max_length=128, unique=True)
    description = models.TextField('Что делает', blank=True)
    transform_class = models.CharField(
        'Класс трансформации', max_length=255,
        help_text='Например: org.apache.kafka.connect.transforms.ReplaceField$Value')
    config_template = models.TextField(
        'Шаблон конфига (JSON)',
        help_text='JSON с плейсхолдером {field}. Пример: '
                  '{"transforms.ReplaceField.type": '
                  '"org.apache.kafka.connect.transforms.ReplaceField$Value", '
                  '"transforms.ReplaceField.blacklist": "{field}"}')
    field_label = models.CharField('Подпись поля значения', max_length=128,
                                   default='Поля через запятую')
    order = models.IntegerField('Порядок в списке', default=0)

    multiple = models.BooleanField(
        'Можно добавлять несколько раз', default=False,
        help_text='Снимите галку, если трансформация может быть только одна.')

    class Meta:
        verbose_name = 'Трансформация'
        verbose_name_plural = 'Трансформации'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def render_config(self, field_value):
        """Подставляет значение поля в шаблон и возвращает dict."""
        import json
        template = json.loads(self.config_template)
        return {k: v.replace('{field}', field_value) if isinstance(v, str) else v
                for k, v in template.items()}

class ConnectorConfig(models.Model):
    """Один коннектор = одна запись. Конфиг целиком в JSON-поле."""

    SOURCE = 'source'
    SINK = 'sink'
    DIRECTION_CHOICES = [
        (SOURCE, 'Source (из источника в Kafka)'),
        (SINK, 'Sink (из Kafka в приёмник)'),
    ]

    name = models.CharField('Название коннектора', max_length=255, unique=True)
    direction = models.CharField('Направление', max_length=8,
                                 choices=DIRECTION_CHOICES)
    connector_type = models.CharField('Тип коннектора', max_length=64,
                                      help_text='slug из реестра, '
                                                'например jdbc-source')
    connector_class = models.CharField('Класс коннектора', max_length=255)
    config = models.JSONField('Конфиг Kafka Connect')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Изменён', auto_now=True)

    class Meta:
        verbose_name = 'Конфигурация коннектора'
        verbose_name_plural = 'Конфигурации коннекторов'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def config_json(self):
        return json.dumps(self.config, indent=2, ensure_ascii=False)

    def as_connect_payload(self):
        """Тело для POST <connect-rest>/connectors."""
        return {'name': self.name, 'config': self.config}