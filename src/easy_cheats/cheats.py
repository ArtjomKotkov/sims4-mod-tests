# Easy Cheats Menu — игровая логика читов (без интерфейса).
import re

import services
import sims4.commands
import sims4.resources

try:
    from protocolbuffers import Consts_pb2
    MONEY_REASON = getattr(Consts_pb2, 'TELEMETRY_MONEY_CHEAT', 0)
except ImportError:
    MONEY_REASON = 0


class CheatError(Exception):
    pass


def tuning_name(tuning):
    return getattr(tuning, '__name__', type(tuning).__name__)


def pretty_name(tuning):
    """career_Adult_Astronaut -> Adult Astronaut"""
    name = tuning_name(tuning)
    name = re.sub(r'^(motive|commodity|statistic|stat|skill|career|buff|trait)_', '', name, flags=re.IGNORECASE)
    return name.replace('_', ' ').strip() or tuning_name(tuning)


def active_sim_info():
    sim_info = services.active_sim_info()
    if sim_info is None:
        raise CheatError('Нет активного персонажа.')
    return sim_info


def active_household():
    household = services.active_household()
    if household is None:
        raise CheatError('Нет активной семьи.')
    return household


def household_sim_infos():
    return list(active_household().sim_info_gen())


def full_name(sim_info):
    return '{} {}'.format(sim_info.first_name, sim_info.last_name).strip() or str(sim_info.sim_id)


def run_command(command):
    """Выполняет встроенную команду игры от имени текущего клиента."""
    client = services.client_manager().get_first_client()
    connection = client.id if client is not None else None
    sims4.commands.execute(command, connection)


# --- Деньги ---------------------------------------------------------------

def get_money():
    return active_household().funds.money


def add_money(amount):
    funds = active_household().funds
    sim = services.get_active_sim()
    if amount >= 0:
        funds.add(amount, MONEY_REASON, sim)
    else:
        funds.try_remove(min(-amount, funds.money), MONEY_REASON, sim)
    return funds.money


def set_money(amount):
    return add_money(max(0, amount) - get_money())


# --- Потребности ----------------------------------------------------------

def _iter_stats(tracker):
    try:
        return list(tracker)
    except TypeError:
        return list(getattr(tracker, '_statistics', {}).values())


def _stat_label(stat_type):
    name = getattr(stat_type, 'stat_name', None)
    return name if name is not None else pretty_name(stat_type)


def get_motives(sim_info):
    """Видимые потребности (голод, бодрость, ... жажда вампира и т.п.)."""
    result = []
    for stat in _iter_stats(sim_info.commodity_tracker):
        stat_type = stat.stat_type
        name = tuning_name(stat_type).lower()
        if 'motive' not in name or 'hidden' in name:
            continue
        if not getattr(stat_type, 'visible', True):
            continue
        result.append(stat)
    return result


def set_motive(sim_info, stat_type, value):
    value = max(stat_type.min_value, min(stat_type.max_value, value))
    sim_info.commodity_tracker.set_value(stat_type, value)


def fill_motives(sim_info, value=None):
    for stat in get_motives(sim_info):
        stat_type = stat.stat_type
        set_motive(sim_info, stat_type, stat_type.max_value if value is None else value)


# --- Навыки ---------------------------------------------------------------

def _skill_class():
    from statistics.skill import Skill
    return Skill


def get_sim_skills(sim_info):
    if hasattr(sim_info, 'all_skills'):
        return list(sim_info.all_skills())
    skill_cls = _skill_class()
    return [s for s in _iter_stats(sim_info.commodity_tracker) if isinstance(s, skill_cls)]


def get_all_skill_types(sim_info):
    skill_cls = _skill_class()
    manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
    result = []
    for stat_type in manager.types.values():
        if not (isinstance(stat_type, type) and issubclass(stat_type, skill_cls)):
            continue
        if getattr(stat_type, 'hidden', False) or getattr(stat_type, 'stat_name', None) is None:
            continue
        ages = getattr(stat_type, 'ages', None)
        if ages and sim_info.age not in ages:
            continue
        result.append(stat_type)
    return result


def skill_label(skill_type):
    return _stat_label(skill_type)


def skill_level(sim_info, skill_type):
    stat = sim_info.commodity_tracker.get_statistic(skill_type)
    return stat.get_user_value() if stat is not None else 0


def set_skill_level(sim_info, skill_type, level):
    level = max(0, min(getattr(skill_type, 'max_level', 10), level))
    stat = sim_info.commodity_tracker.get_statistic(skill_type, add=True)
    if stat is None:
        raise CheatError('Этот навык нельзя добавить персонажу.')
    if hasattr(stat, 'set_user_value'):
        stat.set_user_value(level)
    else:
        sim_info.commodity_tracker.set_value(skill_type, skill_type.convert_from_user_value(level))


def max_all_skills(sim_info):
    for stat in get_sim_skills(sim_info):
        set_skill_level(sim_info, stat.stat_type, getattr(stat.stat_type, 'max_level', 10))


# --- Мудлеты --------------------------------------------------------------

NEGATIVE_MOODS = ('sad', 'angry', 'tense', 'uncomfortable', 'embarrass', 'bored', 'dazed', 'scared')


def get_buffs(sim_info):
    component = sim_info.Buffs
    try:
        buffs = list(component)
    except TypeError:
        buffs = list(getattr(component, '_active_buffs', {}).values())
    return [b for b in buffs if getattr(b, 'visible', True) and getattr(b.buff_type, 'buff_name', None) is not None]


def buff_label(buff):
    return buff.buff_type.buff_name


def buff_is_negative(buff):
    mood = getattr(buff, 'mood_type', None)
    return mood is not None and any(m in tuning_name(mood).lower() for m in NEGATIVE_MOODS)


def remove_buff(sim_info, buff):
    sim_info.Buffs.remove_buff_by_type(buff.buff_type)


def remove_negative_buffs(sim_info):
    removed = 0
    for buff in get_buffs(sim_info):
        if buff_is_negative(buff):
            remove_buff(sim_info, buff)
            removed += 1
    return removed


# --- Отношения ------------------------------------------------------------

def relationship_tracks():
    from relationships.relationship_track import RelationshipTrack
    return RelationshipTrack.FRIENDSHIP_TRACK, RelationshipTrack.ROMANCE_TRACK


def get_relationship_targets(sim_info):
    manager = services.sim_info_manager()
    result = []
    for target_id in sim_info.relationship_tracker.target_sim_gen():
        target = manager.get(target_id)
        if target is not None:
            result.append(target)
    result.sort(key=full_name)
    return result


def get_relationship_score(sim_info, target, track):
    return sim_info.relationship_tracker.get_relationship_score(target.sim_id, track)


def set_relationship_score(sim_info, target, track, value):
    value = max(-100, min(100, value))
    sim_info.relationship_tracker.set_relationship_score(target.sim_id, value, track)


# --- Карьера --------------------------------------------------------------

def get_careers(sim_info):
    return list(sim_info.career_tracker.careers.values())


def career_label(career, sim_info):
    try:
        title = career.current_level_tuning.title(sim_info)
        if title is not None:
            return title
    except Exception:
        pass
    return pretty_name(type(career))


def max_performance(career):
    stat = career.work_performance_stat
    stat.set_value(stat.max_value)


# --- Время, сезоны, прочее (через встроенные команды игры) -----------------

def current_hour():
    return services.time_service().sim_now.hour()


def set_hour(hour):
    now = services.time_service().sim_now
    minutes = ((hour - now.hour()) % 24) * 60 - now.minute()
    if minutes <= 0:
        minutes += 24 * 60
    run_command('clock.advance_game_time {} {} 0'.format(minutes // 60, minutes % 60))


SEASONS = (('SPRING', 'Весна'), ('SUMMER', 'Лето'), ('FALL', 'Осень'), ('WINTER', 'Зима'))


def set_season(season_name):
    run_command('seasons.set_season {}'.format(season_name))


def complete_milestone():
    run_command('aspirations.complete_current_milestone')


def give_satisfaction(points):
    run_command('sims.give_satisfaction_points {}'.format(points))


def edit_in_cas():
    run_command('sims.modify_in_cas')
