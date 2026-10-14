# Easy Cheats Menu — меню, собранные из игровых окон выбора.
from easy_cheats import cheats
from easy_cheats.dialogs import Option, ask_number, notify, show_menu


def main_menu(sim_info=None):
    """sim_info — персонаж, на котором открыто меню (по умолчанию активный)."""
    sim_info = sim_info or cheats.active_sim_info()
    show_menu('Easy Cheats', [
        Option('Деньги', money_menu, '§{}'.format(cheats.get_money())),
        Option('Потребности', lambda: needs_menu(sim_info)),
        Option('Навыки', lambda: skills_menu(sim_info)),
        Option('Мудлеты', lambda: buffs_menu(sim_info)),
        Option('Отношения', lambda: relationships_menu(sim_info)),
        Option('Карьера', lambda: career_menu(sim_info)),
        Option('Жизненные цели', lambda: aspiration_menu(sim_info)),
        Option('Сезоны', season_menu, 'Нужно дополнение «Времена года»'),
        Option('Изменить в CAS', cheats.edit_in_cas, 'Полное редактирование активного персонажа')
        if sim_info is cheats.active_sim_info() else None,
    ], text='Персонаж: {}'.format(cheats.full_name(sim_info)))


# --- Деньги ---------------------------------------------------------------

def money_menu():
    def add(amount):
        return lambda: notify('Бюджет: §{}'.format(cheats.add_money(amount)))

    def set_exact():
        ask_number('Бюджет семьи', 'Введите точную сумму:', cheats.get_money(),
                   lambda v: notify('Бюджет: §{}'.format(cheats.set_money(v))),
                   fallback_command='uic.setmoney <сумма>')

    show_menu('Деньги', [
        Option('+ §1 000', add(1000)),
        Option('+ §50 000', add(50000)),
        Option('+ §1 000 000', add(1000000)),
        Option('− §1 000', add(-1000)),
        Option('Ввести точную сумму…', set_exact),
        Option('Обнулить бюджет', lambda: notify('Бюджет: §{}'.format(cheats.set_money(0)))),
    ], text='Сейчас: §{}'.format(cheats.get_money()))


# --- Потребности ----------------------------------------------------------

def needs_menu(sim_info):
    options = [
        Option('Заполнить все', lambda: (cheats.fill_motives(sim_info), notify('Потребности заполнены.'))),
        Option('Заполнить всей семье', lambda: (
            [cheats.fill_motives(s) for s in cheats.household_sim_infos()], notify('Потребности семьи заполнены.'))),
    ]
    for stat in cheats.get_motives(sim_info):
        options.append(Option(cheats._stat_label(stat.stat_type), _motive_editor(sim_info, stat.stat_type),
                              'Сейчас: {}'.format(int(stat.get_value()))))
    show_menu('Потребности', options)


def _motive_editor(sim_info, stat_type):
    def set_to(value):
        return lambda: cheats.set_motive(sim_info, stat_type, value)

    def custom():
        ask_number('Потребность', 'Значение от -100 до 100:', 100,
                   lambda v: cheats.set_motive(sim_info, stat_type, v))

    return lambda: show_menu('Потребность', [
        Option('100 (максимум)', set_to(stat_type.max_value)),
        Option('75', set_to(75)),
        Option('50', set_to(50)),
        Option('0', set_to(0)),
        Option('-100 (минимум)', set_to(stat_type.min_value)),
        Option('Ввести значение…', custom),
    ])


# --- Навыки ---------------------------------------------------------------

def skills_menu(sim_info):
    options = [
        Option('+ Добавить навык…', lambda: _all_skills_menu(sim_info)),
        Option('Все навыки персонажа на максимум', lambda: (cheats.max_all_skills(sim_info), notify('Готово.'))),
    ]
    for stat in cheats.get_sim_skills(sim_info):
        options.append(Option(cheats.skill_label(stat.stat_type), _skill_editor(sim_info, stat.stat_type),
                              'Уровень: {}'.format(stat.get_user_value())))
    show_menu('Навыки', options)


def _all_skills_menu(sim_info):
    show_menu('Все навыки', [
        Option(cheats.skill_label(t), _skill_editor(sim_info, t), 'Уровень: {}'.format(cheats.skill_level(sim_info, t)))
        for t in cheats.get_all_skill_types(sim_info)
    ])


def _skill_editor(sim_info, skill_type):
    max_level = getattr(skill_type, 'max_level', 10)

    def set_level(level):
        return lambda: (cheats.set_skill_level(sim_info, skill_type, level),
                        notify('Уровень навыка: {}'.format(cheats.skill_level(sim_info, skill_type))))

    return lambda: show_menu('Уровень навыка', [Option('Уровень {}'.format(i), set_level(i))
                                                for i in range(1, max_level + 1)])


# --- Мудлеты --------------------------------------------------------------

def buffs_menu(sim_info):
    options = [Option('Удалить все негативные', lambda: notify(
        'Удалено мудлетов: {}'.format(cheats.remove_negative_buffs(sim_info))))]
    for buff in cheats.get_buffs(sim_info):
        options.append(Option(cheats.buff_label(sim_info, buff), _remover(sim_info, buff),
                              'Нажмите, чтобы удалить' + (' (негативный)' if cheats.buff_is_negative(buff) else '')))
    show_menu('Мудлеты', options)


def _remover(sim_info, buff):
    return lambda: (cheats.remove_buff(sim_info, buff), buffs_menu(sim_info))


# --- Отношения ------------------------------------------------------------

def relationships_menu(sim_info):
    friendship, romance = cheats.relationship_tracks()
    options = []
    for target in cheats.get_relationship_targets(sim_info):
        desc = 'Дружба: {} / Романтика: {}'.format(
            int(cheats.get_relationship_score(sim_info, target, friendship)),
            int(cheats.get_relationship_score(sim_info, target, romance)))
        options.append(Option(cheats.full_name(target), _relationship_editor(sim_info, target), desc))
    show_menu('Отношения', options, text='Выберите персонажа')


def _relationship_editor(sim_info, target):
    friendship, romance = cheats.relationship_tracks()

    def set_score(track, value):
        return lambda: cheats.set_relationship_score(sim_info, target, track, value)

    def custom(track):
        return lambda: ask_number('Отношения', 'Значение от -100 до 100:', 100,
                                  lambda v: cheats.set_relationship_score(sim_info, target, track, v))

    def build():
        options = [
            Option('Дружба: 100', set_score(friendship, 100)),
            Option('Дружба: 50', set_score(friendship, 50)),
            Option('Дружба: 0', set_score(friendship, 0)),
            Option('Дружба: -100', set_score(friendship, -100)),
            Option('Дружба: ввести…', custom(friendship)),
        ]
        if cheats.romance_allowed(sim_info, target):  # не для детей/подростков и родственников
            options += [
                Option('Романтика: 100', set_score(romance, 100)),
                Option('Романтика: 50', set_score(romance, 50)),
                Option('Романтика: 0', set_score(romance, 0)),
                Option('Романтика: ввести…', custom(romance)),
            ]
        show_menu(cheats.full_name(target), options)

    return build


# --- Карьера --------------------------------------------------------------

def career_menu(sim_info):
    options = []
    for career in cheats.get_careers(sim_info):
        options.append(Option(cheats.career_label(career, sim_info), _career_editor(sim_info, career),
                              'Уровень: {}'.format(getattr(career, 'user_level', '?'))))
    show_menu('Карьера', options, text='Нет карьеры — нечего менять.' if not options else '')


def _career_editor(sim_info, career):
    return lambda: show_menu(cheats.career_label(career, sim_info), [
        Option('Повысить', lambda: (career.promote(), notify('Повышение!'))),
        Option('Понизить', lambda: (career.demote(), notify('Понижение.'))),
        Option('Продуктивность на максимум', lambda: (cheats.max_performance(sim_info, career), notify('Готово.'))),
    ])


# --- Жизненные цели, сезоны ----------------------------------------------

def aspiration_menu(sim_info):
    show_menu('Жизненные цели', [
        Option('Завершить текущий этап', lambda: (cheats.complete_milestone(sim_info), notify('Этап завершён.'))),
        Option('+1 000 очков удовлетворения', lambda: cheats.give_satisfaction(sim_info, 1000)),
        Option('+10 000 очков удовлетворения', lambda: cheats.give_satisfaction(sim_info, 10000)),
    ])


def season_menu():
    show_menu('Сезоны', [Option(label, (lambda n: lambda: cheats.set_season(n))(name))
                         for name, label in cheats.SEASONS])
