# Easy Cheats Menu — точка входа: регистрирует команды и показывает подсказку после загрузки участка.
from easy_cheats import commands  # noqa: F401  (регистрация консольных команд)
from easy_cheats.dialogs import logger, notify

_greeted = False


def _inject_zone_hook():
    try:
        from zone import Zone
    except ImportError:
        return
    original = Zone.on_loading_screen_animation_finished

    def on_loading_screen_animation_finished(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        global _greeted
        if not _greeted:
            _greeted = True
            try:
                notify('Мод загружен. Откройте консоль (Ctrl+Shift+C) и введите: uic')
            except Exception as exc:
                logger.exception('greeting failed', exc=exc)
        return result

    Zone.on_loading_screen_animation_finished = on_loading_screen_animation_finished


_inject_zone_hook()
