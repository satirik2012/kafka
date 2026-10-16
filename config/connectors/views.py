import json

from django.shortcuts import redirect, render

from .forms import (DATA_FORMAT_CHOICES, KeyFormSetForm,
                    RECORD_GENERATION_CHOICES, SystemForm, WelcomeForm)
from .models import ConnectorConfig, System, Transform


def welcome(request):
    """Шаг 1: название и формат коннектора.

    При первом заходе поля пустые. Заполняем их только если пользователь
    вернулся сюда со второго шага по ссылке «Назад» (?back=1).
    """
    survey = request.session.get('survey', {})
    back = request.GET.get('back') == '1'

    if request.method == 'POST':
        form = WelcomeForm(request.POST)
        if form.is_valid():
            request.session['survey'] = {
                'name': form.cleaned_data['name'],
                'direction': form.cleaned_data['direction'],
                'keys': [],
                'data_format': '',
                'record_generation': '',
                'incrementing_column': '',
                'system': None,
                'transforms': [],
            }
            return redirect('connectors:system')
    elif back and survey.get('name'):
        form = WelcomeForm(initial={
            'name': survey['name'],
            'direction': survey.get('direction', ''),
        })
    else:
        form = WelcomeForm()

    return render(request, 'connectors/welcome.html', {'form': form})


def system_step(request):
    """Шаг 2: система, формат данных, формат счётчика, список ключей."""
    survey = request.session.get('survey')
    if not survey:
        return redirect('connectors:welcome')

    direction = survey['direction']
    keys = survey.get('keys', [])
    data_format = survey.get('data_format', '')
    record_generation = survey.get('record_generation', '')
    incrementing_column = survey.get('incrementing_column', '')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # --- нажали «Добавить» у ключа ---
        if action == 'add_key':
            data_format = request.POST.get('data_format', '') or data_format
            record_generation = (request.POST.get('record_generation', '')
                                 or record_generation)
            incrementing_column = (request.POST.get('incrementing_column', '')
                                   or incrementing_column)
            kf = KeyFormSetForm(request.POST)
            if kf.is_valid():
                value = kf.cleaned_data['value']
                if value and value not in keys:
                    keys.append(value)
            survey['keys'] = keys
            survey['data_format'] = data_format
            survey['record_generation'] = record_generation
            survey['incrementing_column'] = incrementing_column
            request.session['survey'] = survey
            return redirect('connectors:system')

        # --- нажали «Удалить» у ключа ---
        if action == 'del_key':
            target = request.POST.get('del_value', '').strip()
            survey['keys'] = [k for k in keys if k != target]
            request.session['survey'] = survey
            return redirect('connectors:system')

        # --- нажали «Продолжить»: проверяем и идём дальше ---
        form = SystemForm(request.POST, direction=direction)
        data_format = request.POST.get('data_format', '')
        record_generation = request.POST.get('record_generation', '')
        incrementing_column = request.POST.get('incrementing_column', '').strip()

        if form.is_valid():
            if data_format not in dict(DATA_FORMAT_CHOICES):
                form.add_error(None, 'Выберите формат данных.')
            elif record_generation not in dict(RECORD_GENERATION_CHOICES):
                form.add_error(None, 'Выберите формат счётчика.')
            elif record_generation == 'incrementing' and not incrementing_column:
                form.add_error(None, 'Укажите имя поля incrementing.')
            else:
                survey['system'] = form.cleaned_data['system'].pk
                survey['data_format'] = data_format
                survey['record_generation'] = record_generation
                survey['incrementing_column'] = incrementing_column
                request.session['survey'] = survey
                return redirect('connectors:summary')
    else:
        form = SystemForm(direction=direction)

    return render(request, 'connectors/system.html', {
        'form': form,
        'survey': survey,
        'keys': survey.get('keys', []),
        'data_formats': DATA_FORMAT_CHOICES,
        'selected_format': data_format,
        'record_generations': RECORD_GENERATION_CHOICES,
        'selected_generation': record_generation,
        'selected_incrementing': incrementing_column,
        'key_form': KeyFormSetForm(),
        'direction_label': dict(ConnectorConfig.DIRECTION_CHOICES)[direction],
        'no_systems': not form.fields['system'].queryset.exists(),
    })


def build_preview(survey, system, transforms):
    """Собирает предварительный конфиг, чтобы показать JSON до сохранения.

    NOTE: connector.class и key.converter — заглушки. Настоящий маппинг
    (формат -> key/value.converter, система -> класс коннектора) пока не
    определён ни в модели, ни в реестре.
    """
    config = {
        'name': survey['name'],
        'connector.class': '',
        'tasks.max': '1',
        'key.converter': survey.get('data_format', ''),
        'record.generation': survey.get('record_generation', ''),
    }
    if system:
        config['source.system'] = system.slug_code
    if survey.get('keys'):
        config['key.fields'] = ','.join(survey['keys'])
    if survey.get('record_generation') == 'incrementing':
        config['incrementing.column.name'] = survey.get('incrementing_column', '')

    for entry in transforms:
        t = Transform.objects.filter(pk=entry['id']).first()
        if t:
            try:
                config.update(t.render_config(entry['field']))
            except (json.JSONDecodeError, AttributeError):
                pass

    return json.dumps(config, indent=2, ensure_ascii=False)


def summary(request):
    """Шаг 3: настройки коннектора — выбор трансформаций и предпросмотр."""
    survey = request.session.get('survey')
    if not survey:
        return redirect('connectors:welcome')

    system = None
    if survey.get('system'):
        system = System.objects.filter(pk=survey['system']).first()

    transforms = list(survey.get('transforms', []))
    all_transforms = Transform.objects.all()
    errors = []
    editing_index = None

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add_transform':
            pk = request.POST.get('transform', '')
            field = request.POST.get('field_value', '').strip()
            t = Transform.objects.filter(pk=pk).first()
            if not t:
                errors.append('Трансформация не найдена.')
            elif not field:
                errors.append('Заполните значение поля.')
            elif not t.multiple and any(x['id'] == t.pk for x in transforms):
                errors.append(
                    f'«{t.name}» можно добавить только один раз — '
                    f'отредактируйте существующую.')
            else:
                transforms.append({'id': t.pk, 'name': t.name, 'field': field})
                survey['transforms'] = transforms
                request.session['survey'] = survey
                return redirect('connectors:summary')

        elif action == 'del_transform':
            idx = request.POST.get('edit_index', '')
            try:
                transforms.pop(int(idx))
                survey['transforms'] = transforms
                request.session['survey'] = survey
                return redirect('connectors:summary')
            except (ValueError, IndexError):
                errors.append('Не удалось удалить трансформацию.')

        elif action == 'start_edit':
            try:
                editing_index = int(request.POST.get('edit_index', ''))
            except ValueError:
                editing_index = None

        elif action == 'cancel_edit':
            return redirect('connectors:summary')

        elif action == 'edit_transform':
            idx = request.POST.get('edit_index', '')
            field = request.POST.get('field_value', '').strip()
            try:
                pos = int(idx)
                if field:
                    transforms[pos]['field'] = field
                    survey['transforms'] = transforms
                    request.session['survey'] = survey
                    return redirect('connectors:summary')
                errors.append('Значение поля не может быть пустым.')
                editing_index = pos
            except (ValueError, IndexError):
                errors.append('Не удалось изменить трансформацию.')

    used_ids = [x['id'] for x in transforms]

    return render(request, 'connectors/summary.html', {
        'survey': survey,
        'system': system,
        'transforms': transforms,
        'all_transforms': all_transforms,
        'used_ids': used_ids,
        'errors': errors,
        'editing_index': editing_index,
        'preview': build_preview(survey, system, transforms),
    })


def settings_page(request):
    """Раздел настроек: ссылки на справочники."""
    return render(request, 'connectors/settings.html')


def transforms_admin(request):
    """Справочник трансформаций: список + создание/редактирование."""
    if request.method == 'POST':
        pk = request.POST.get('pk')
        t = Transform.objects.filter(pk=pk).first() if pk else Transform()
        t.name = request.POST.get('name', '').strip()
        t.description = request.POST.get('description', '').strip()
        t.transform_class = request.POST.get('transform_class', '').strip()
        t.config_template = request.POST.get('config_template', '').strip()
        t.field_label = request.POST.get(
            'field_label', 'Поля через запятую').strip() or 'Поля через запятую'
        t.multiple = request.POST.get('multiple') == '1'
        try:
            t.order = int(request.POST.get('order') or 0)
        except ValueError:
            t.order = 0
        if t.name:
            t.save()
        return redirect('connectors:transforms')

    if request.GET.get('edit'):
        editing = Transform.objects.filter(pk=request.GET['edit']).first()
    else:
        editing = None

    return render(request, 'connectors/transforms.html', {
        'items': Transform.objects.all(),
        'editing': editing,
    })