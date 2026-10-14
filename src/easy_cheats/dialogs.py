# Easy Cheats Menu — обёртки над игровыми диалогами (уведомления, списки выбора, ввод числа).
import services
import sims4.log
from sims4.localization import LocalizationHelperTuning
from ui.ui_dialog_notification import UiDialogNotification
from ui.ui_dialog_picker import UiObjectPicker, ObjectPickerRow

logger = sims4.log.Logger('EasyCheats', default_owner='easy_cheats')

MOD_TITLE = 'Easy Cheats'


def raw(text):
    return LocalizationHelperTuning.get_raw_text(str(text))


def loc(value):
    """Принимает str или LocalizedString, возвращает LocalizedString."""
    if value is None:
        return raw('')
    if isinstance(value, (str, int, float)):
        return raw(value)
    return value


def _factory(value):
    return lambda *_, **__: loc(value)


def owner():
    return services.active_sim_info()


def notify(text, title=MOD_TITLE):
    try:
        dialog = UiDialogNotification.TunableFactory().default(owner(), text=_factory(text), title=_factory(title))
        dialog.show_dialog()
    except Exception as exc:
        logger.exception('notify failed', exc=exc)


class Option:
    __slots__ = ('label', 'callback', 'description')

    def __init__(self, label, callback, description=None):
        self.label = label
        self.callback = callback
        self.description = description


def _picker_type():
    enum = getattr(UiObjectPicker, 'UiObjectPickerObjectPickerType', None)
    if enum is None:
        try:
            from ui.ui_dialog_picker import ObjectPickerType as enum
        except ImportError:
            return None
    return getattr(enum, 'OBJECT', None)


def run_safely(callback, *args):
    try:
        callback(*args)
    except Exception as exc:
        logger.exception('Easy Cheats action failed', exc=exc)
        notify('Ошибка: {}'.format(exc))


def show_menu(title, options, text=''):
    """Показывает список, по клику на строку вызывает option.callback()."""
    options = [o for o in options if o is not None]
    if not options:
        notify('Здесь пока ничего нет.')
        return
    kwargs = {'text': _factory(text), 'title': _factory(title)}
    picker_type = _picker_type()
    if picker_type is not None:
        kwargs['picker_type'] = picker_type
    dialog = UiObjectPicker.TunableFactory().default(owner(), **kwargs)
    for index, option in enumerate(options):
        row_kwargs = {'option_id': index, 'name': loc(option.label), 'tag': index}
        if option.description is not None:
            row_kwargs['row_description'] = loc(option.description)
        dialog.add_row(ObjectPickerRow(**row_kwargs))

    def on_response(dlg):
        if not dlg.accepted:
            return
        tag = None
        if hasattr(dlg, 'get_single_result_tag'):
            tag = dlg.get_single_result_tag()
        else:
            tags = dlg.get_result_tags()
            tag = tags[0] if tags else None
        if tag is None or not 0 <= tag < len(options):
            return
        run_safely(options[tag].callback)

    dialog.add_listener(on_response)
    dialog.show_dialog()


def ask_number(title, text, initial, callback, fallback_command=None):
    """Окно ввода числа. Если игра не позволит его построить — подсказывает консольную команду."""
    input_name = 'easy_cheats_input'
    try:
        from sims4.collections import AttributeDict
        from ui.ui_dialog_generic import UiDialogTextInputOkCancel
        from ui.ui_text_input import UiTextInput, _TextInputLengthFixed

        text_input = UiTextInput(sort_order=0, restricted_characters=None)
        text_input.default_text = None
        text_input.title = None
        text_input.initial_value = _factory(initial)
        text_input.check_profanity = False
        text_input.length_restriction = _TextInputLengthFixed(min_length=None, max_length=16)
        text_input.height = None
        inputs = AttributeDict({input_name: text_input})
        dialog = UiDialogTextInputOkCancel.TunableFactory(text_inputs=(input_name,)).default(
            owner(), text_inputs=inputs, text=_factory(text), title=_factory(title))

        def on_response(dlg):
            if not dlg.accepted:
                return
            value = dlg.text_input_responses.get(input_name, '')
            try:
                number = int(float(str(value).strip().replace(',', '.').replace(' ', '')))
            except ValueError:
                notify('«{}» — это не число.'.format(value))
                return
            run_safely(callback, number)

        dialog.add_listener(on_response)
        dialog.show_dialog()
    except Exception as exc:
        logger.exception('text input dialog failed', exc=exc)
        hint = 'Окно ввода недоступно в этой версии игры.'
        if fallback_command:
            hint += ' Используйте консоль (Ctrl+Shift+C): {}'.format(fallback_command)
        notify(hint)
