# Easy Cheats Menu — игровая логика читов (без интерфейса).
# Всё вызывается напрямую через Python-API игры (сверено с декомпилированным кодом EA),
# поэтому testingcheats не нужен и встроенные Cheat/Automation-команды не используются.
import re

import services
import sims4.commands
import sims4.resources

try:
    from protocolbuffers import Consts_pb2
    MONEY_REASON = getattr(Consts_pb2, 'TELEMETRY_MONEY_CHEAT', 0)
except ImportError:
    MONEY_REASON = 0

ADULT_AGE_MIN = 16  # sims.sim_info_types.Age.YOUNGADULT


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


def is_adult(sim_info):
    return int(sim_info.age) >= ADULT_AGE_MIN


def run_live_command(command):
    """Только для Live-команд игры: Cheat-команды через execute() без testingcheats молча не выполняются."""
    client = services.client_manager().get_first_client()
    sims4.commands.execute(command, client.id if client is not None else None)


# --- Деньги ---------------------------------------------------------------

def get_money():
    return active_household().funds.money


def add_money(amount):
    funds = active_household().funds
    sim = services.get_active_sim()
    if amount >= 0:
        # count_as_earnings=False: читерские деньги не засчитываются в цели «заработать N»
        funds.add(amount, MONEY_REASON, sim, count_as_earnings=False)
    else:
        funds.try_remove(min(-amount, funds.money), MONEY_REASON, sim)
    return funds.money


def set_money(amount):
    return add_money(max(0, amount) - get_money())


# --- Потребности ----------------------------------------------------------

def _stat_label(stat_type):
    name = getattr(stat_type, 'stat_name', None)
    return name if name is not None else pretty_name(stat_type)


def get_motives(sim_info):
    """Видимые потребности (голод, бодрость, ... жажда вампира и т.п.)."""
    result = []
    for stat in list(sim_info.commodity_tracker):
        if not getattr(stat, 'is_visible', False) or getattr(stat, 'is_ranked', False):
            continue
        name = tuning_name(stat.stat_type).lower()
        if 'motive' in name and 'hidden' not in name:
            result.append(stat)
    return result


def set_motive(sim_info, stat_type, value):
    value = max(stat_type.min_value, min(stat_type.max_value, value))
    sim_info.commodity_tracker.set_value(stat_type, value)


def fill_motives(sim_info):
    # То же, что делает встроенный чит stats.fill_commodities.
    sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=True)


def set_all_motives(sim_info, value):
    for stat in get_motives(sim_info):
        set_motive(sim_info, stat.stat_type, value)


# --- Навыки ---------------------------------------------------------------

def get_sim_skills(sim_info):
    return list(sim_info.all_skills())


def get_all_skill_types(sim_info):
    manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
    result = []
    for skill_type in manager.all_skills_gen():
        if getattr(skill_type, 'hidden', False) or getattr(skill_type, 'stat_name', None) is None:
            continue
        if skill_type.can_add(sim_info):  # возраст, вид, наличие дополнения
            result.append(skill_type)
    return result


def skill_label(skill_type):
    return _stat_label(skill_type)


def skill_level(sim_info, skill_type):
    return sim_info.commodity_tracker.get_user_value(skill_type)


def set_skill_level(sim_info, skill_type, level):
    tracker = sim_info.commodity_tracker
    level = max(0, min(skill_type.max_level, level))
    if tracker.get_statistic(skill_type) is None and tracker.add_statistic(skill_type) is None:
        raise CheatError('Этот навык нельзя добавить персонажу.')
    current = tracker.get_user_value(skill_type)
    if level <= current:
        tracker.set_user_value(skill_type, level)
        return
    # Как stats.set_skill_level: по одному уровню, чтобы сработали награды за каждый уровень.
    for n in range(current + 1, level + 1):
        tracker.set_user_value(skill_type, n)


def max_all_skills(sim_info):
    for stat in get_sim_skills(sim_info):
        set_skill_level(sim_info, stat.stat_type, stat.stat_type.max_level)


# --- Мудлеты --------------------------------------------------------------

def get_buffs(sim_info):
    return [b for b in list(sim_info.Buffs) if b.visible and b.buff_type.buff_name is not None]


def buff_label(sim_info, buff):
    return buff.buff_type.buff_name(sim_info)


def buff_is_negative(buff):
    from buffs import BuffPolarity
    return buff.polarity == BuffPolarity.NEGATIVE


def remove_buff(sim_info, buff):
    # Мудлеты от основных потребностей игра сама не даст удалить (это безопасно).
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


def romance_allowed(sim_info, target):
    if not (is_adult(sim_info) and is_adult(target)):
        return False
    try:
        return not sim_info.genealogy.get_family_relationship_bit(target.sim_id)
    except Exception:
        return True


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


def max_performance(sim_info, career):
    # Как careers.set_performance в коде EA.
    stat = sim_info.statistic_tracker.get_statistic(career.current_level_tuning.performance_stat, add=True)
    stat.set_value(stat.max_value)
    sim_info.career_tracker.resend_career_data()


# --- Жизненные цели -------------------------------------------------------

def complete_milestone(sim_info):
    """Копия логики aspirations.complete_current_milestone из кода EA."""
    aspiration = sim_info.primary_aspiration
    if aspiration is None:
        raise CheatError('У персонажа нет жизненной цели.')
    track = services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK).get(aspiration.guid64)
    if track is None:
        raise CheatError('Жизненная цель не найдена.')
    tracker = sim_info.aspiration_tracker
    for _, milestone in track.get_aspirations():
        if tracker.milestone_completed(milestone):
            continue
        just_completed = []
        for objective in milestone.objectives:
            if not tracker.objective_completed(objective):
                tracker.complete_objective(objective, milestone)
                just_completed.append(objective)
        tracker.complete_milestone(milestone, sim_info)
        tracker.send_if_dirty()
        tracker.update_objectives_after_ui_change(just_completed)
        return True
    raise CheatError('Все этапы этой цели уже выполнены.')


def give_satisfaction(sim_info, points):
    from protocolbuffers.DistributorOps_pb2 import SetWhimBucks
    sim_info.apply_satisfaction_points_delta(points, SetWhimBucks.COMMAND)


# --- Сезоны ---------------------------------------------------------------

SEASONS = (('SPRING', 'Весна'), ('SUMMER', 'Лето'), ('FALL', 'Осень'), ('WINTER', 'Зима'))


def set_season(season_name):
    service = services.season_service()
    if service is None:
        raise CheatError('Нужно дополнение «Времена года».')
    from seasons.seasons_enums import SeasonSetSource, SeasonType
    service.set_season(getattr(SeasonType, season_name), SeasonSetSource.CHEAT, None)


def edit_in_cas():
    run_live_command('sims.modify_in_cas')  # Live-команда игры, работает без testingcheats
