# Easy Cheats Menu — консольные команды (Ctrl+Shift+C). testingcheats для них не нужен.
import sims4.commands

from easy_cheats import cheats, menus
from easy_cheats.dialogs import logger

LIVE = sims4.commands.CommandType.Live


def _run(_connection, action, *args):
    output = sims4.commands.CheatOutput(_connection)
    try:
        result = action(*args)
        if result is not None:
            output(str(result))
        return True
    except cheats.CheatError as exc:
        output(str(exc))
    except Exception as exc:
        logger.exception('Easy Cheats command failed', exc=exc)
        output('Easy Cheats error: {}'.format(exc))
    return False


@sims4.commands.Command('uic', 'easycheats', command_type=LIVE)
def open_menu(_connection=None):
    return _run(_connection, menus.main_menu)


@sims4.commands.Command('uic.money', command_type=LIVE)
def add_money(amount: int = 1000, _connection=None):
    return _run(_connection, lambda: 'Funds: {}'.format(cheats.add_money(amount)))


@sims4.commands.Command('uic.setmoney', command_type=LIVE)
def set_money(amount: int = 0, _connection=None):
    return _run(_connection, lambda: 'Funds: {}'.format(cheats.set_money(amount)))


@sims4.commands.Command('uic.needs', command_type=LIVE)
def fill_needs(value: int = None, _connection=None):
    def apply():
        sim_info = cheats.active_sim_info()
        if value is None:
            cheats.fill_motives(sim_info)
        else:
            cheats.set_all_motives(sim_info, value)
    return _run(_connection, apply)


@sims4.commands.Command('uic.needs_household', command_type=LIVE)
def fill_needs_household(_connection=None):
    def fill_all():
        for sim_info in cheats.household_sim_infos():
            cheats.fill_motives(sim_info)
    return _run(_connection, fill_all)


@sims4.commands.Command('uic.maxskills', command_type=LIVE)
def max_skills(_connection=None):
    return _run(_connection, lambda: cheats.max_all_skills(cheats.active_sim_info()))


@sims4.commands.Command('uic.cleanbuffs', command_type=LIVE)
def clean_buffs(_connection=None):
    return _run(_connection, lambda: 'Removed: {}'.format(cheats.remove_negative_buffs(cheats.active_sim_info())))


@sims4.commands.Command('uic.help', command_type=LIVE)
def show_help(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    for line in ('uic  - open Easy Cheats menu',
                 'uic.money [amount]  - add money (default 1000, negative removes)',
                 'uic.setmoney <amount>  - set exact household funds',
                 'uic.needs [value]  - fill (or set) all needs of active sim',
                 'uic.needs_household  - fill needs of whole household',
                 'uic.maxskills  - max out every skill the active sim has',
                 'uic.cleanbuffs  - remove negative moodlets'):
        output(line)
    return True
