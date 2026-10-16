from django import forms

from .models import ConnectorConfig, System


class WelcomeForm(forms.Form):
    """Шаг 1: название коннектора + sink/source."""

    name = forms.CharField(
        label='Название коннектора',
        max_length=255,
        help_text='Латиница, без пробелов: буквы, цифры, точка, дефис, '
                  'подчёркивание.',
    )
    direction = forms.ChoiceField(
        label='Формат коннектора',
        choices=ConnectorConfig.DIRECTION_CHOICES,
        widget=forms.RadioSelect,
    )

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name.replace('.', '').replace('-', '').replace('_', '').isascii():
            raise forms.ValidationError('Название должно быть на латинице.')
        if ' ' in name:
            raise forms.ValidationError('Без пробелов.')
        return name


class SystemForm(forms.Form):
    """Шаг 2: система-продюсер или система-приёмник."""

    system = forms.ModelChoiceField(
        label='',
        queryset=System.objects.none(),
        empty_label=None,
        widget=forms.Select,
    )

    def __init__(self, *args, direction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.direction = direction
        if direction:
            self.fields['system'].queryset = System.objects.filter(
                usage=direction)
            if direction == ConnectorConfig.SOURCE:
                self.fields['system'].label = (
                    'Укажите систему-продюсер, которая будет писать в топик')
            else:
                self.fields['system'].label = (
                    'Укажите систему, куда пишем из топика')

    def clean(self):
        data = super().clean()
        system = data.get('system')
        if system and self.direction and system.usage != self.direction:
            raise forms.ValidationError(
                'Система выбрана не по формату коннектора.')
        return data

DATA_FORMAT_CHOICES = [
    ('json', 'JSON'),
    ('avro+json', 'Avro + JSON'),
    ('xml', 'XML'),
]

RECORD_GENERATION_CHOICES = [
    ('incrementing', 'incrementing'),
    ('timestamp', 'timestamp'),
]


class KeyFormSetForm(forms.Form):
    """Один ключ. Вводится вручную, список растёт по кнопке «Добавить»."""

    value = forms.CharField(label='Значение ключа', max_length=128,
                            required=False,
                            widget=forms.TextInput(
                                attrs={'placeholder': 'например: order_id'}))

    def clean_value(self):
        return self.cleaned_data.get('value', '').strip()