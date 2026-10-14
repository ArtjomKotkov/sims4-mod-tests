# Easy Cheats Menu — семейные связи (родитель/ребёнок, братья-сёстры, брак).
#
# В игре родство хранится в двух местах:
#   1) семейное древо (genealogy): у каждого сима записаны только мать и отец (+ бабушки/дедушки);
#      дети, братья, дяди, кузены вычисляются из него;
#   2) «биты» отношений (иконки «Отец», «Сестра»…), которые игра выводит из древа.
# Чтобы ничего не рассинхронизировать, мы меняем только древо теми же функциями, что игра
# использует при рождении ребёнка, а потом пересчитываем биты для всех затронутых пар так же,
# как игра делает это при загрузке участка (SimInfo.add_family_link).
# Брак — рецепт из EA ForceMarriageInteraction (бит «супруг» с обеих сторон).
import services

from easy_cheats.cheats import CheatError, full_name, is_adult

_BIT_DEPTH = 2  # родство дальше кузенов/внуков игра битами не отмечает


def _indexes():
    from sims.genealogy_tracker import FamilyRelationshipIndex
    return FamilyRelationshipIndex


def _sim_info(sim_id):
    return services.sim_info_manager().get(sim_id) if sim_id else None


def _family_tree_service():
    getter = getattr(services, 'family_tree_service', None)
    return getter() if getter is not None else None


def _genealogy_caching():
    try:
        from sims.genealogy_tracker import genealogy_caching
        return genealogy_caching()
    except ImportError:
        import contextlib
        return contextlib.suppress()


# --- Чтение древа ---------------------------------------------------------

def parent_id(sim_info, index):
    genealogy = sim_info.genealogy
    relations = getattr(genealogy, '_family_relations', None)
    if relations is not None and index not in relations:
        return None
    if hasattr(genealogy, 'get_parent_relation'):  # новая версия древа (family_tree_service)
        return genealogy.get_parent_relation(index, allow_invalid_parent=True)
    return genealogy.get_relation(index)


def parents(sim_info):
    """{FamilyRelationshipIndex.MOTHER/FATHER: sim_id} — только заполненные."""
    idx = _indexes()
    result = {}
    for index in (idx.MOTHER, idx.FATHER):
        sim_id = parent_id(sim_info, index)
        if sim_id:
            result[index] = sim_id
    return result


_children_map = None  # parent_id -> [sim_info], строится один раз на операцию


class _ChildrenIndex:
    def __enter__(self):
        global _children_map
        self._owner = _children_map is None
        if self._owner:
            mapping = {}
            for s in services.sim_info_manager().values():
                for pid in parents(s).values():
                    mapping.setdefault(pid, []).append(s)
            _children_map = mapping

    def __exit__(self, *exc):
        global _children_map
        if self._owner:
            _children_map = None
        return False


def children(sim_info):
    if _children_map is not None:
        return list(_children_map.get(sim_info.sim_id, ()))
    return [s for s in services.sim_info_manager().values() if sim_info.sim_id in parents(s).values()]


def ancestors(sim_info, depth=None):
    found, level, current = set(), 0, [sim_info]
    while current and (depth is None or level < depth):
        level += 1
        nxt = []
        for s in current:
            for pid in parents(s).values():
                if pid not in found:
                    found.add(pid)
                    p = _sim_info(pid)
                    if p is not None:
                        nxt.append(p)
        current = nxt
    return found


def descendants(sim_info, depth=None):
    found, level, current = {}, 0, [sim_info]
    while current and (depth is None or level < depth):
        level += 1
        nxt = []
        for s in current:
            for c in children(s):
                if c.sim_id not in found and c.sim_id != sim_info.sim_id:
                    found[c.sim_id] = c
                    nxt.append(c)
        current = nxt
    return list(found.values())


def _blood_relatives(sim_info):
    """Все, с кем у сима могут быть семейные биты: предки до бабушек и их потомки до 2 колен."""
    result = {}
    roots = [sim_info] + [s for s in (_sim_info(i) for i in ancestors(sim_info, _BIT_DEPTH)) if s is not None]
    for root in roots:
        result[root.sim_id] = root
        for d in descendants(root, _BIT_DEPTH):
            result[d.sim_id] = d
    result.pop(sim_info.sim_id, None)
    return result


def are_blood_related(a, b):
    tree = _family_tree_service()
    if tree is not None and hasattr(tree, 'are_sims_blood_related'):
        return tree.are_sims_blood_related(a.sim_id, b.sim_id)
    a_family = ancestors(a) | {a.sim_id}
    b_family = ancestors(b) | {b.sim_id}
    return bool(a_family & b_family)


# --- Пересчёт битов родства ----------------------------------------------

def _family_bit(a, b):
    return a.genealogy.get_family_relationship_bit(b.sim_id)


class _BitRefresher:
    """Запоминает биты до изменения древа и после него убирает устаревшие / добавляет новые."""

    def __init__(self, changed_sim):
        self._old = {}
        with _genealogy_caching(), _ChildrenIndex():
            self._subtree = [changed_sim] + descendants(changed_sim, _BIT_DEPTH)
            for x in self._subtree:
                for y in self._partners(x):
                    self._remember(x, y)

    def _partners(self, x):
        manager = services.sim_info_manager()
        partners = dict(_blood_relatives(x))
        for target_id in x.relationship_tracker.target_sim_gen():
            if target_id not in partners:
                target = manager.get(target_id)
                if target is not None:
                    partners[target_id] = target
        partners.pop(x.sim_id, None)
        return partners.values()

    def _remember(self, x, y, known_bit=True):
        for a, b in ((x, y), (y, x)):
            if (a.sim_id, b.sim_id) not in self._old:
                self._old[(a.sim_id, b.sim_id)] = (a, b, _family_bit(a, b) if known_bit else None)

    def apply(self):
        with _genealogy_caching(), _ChildrenIndex():
            for x in self._subtree:
                for y in self._partners(x):
                    # Новые родственники: раньше общих предков не было, значит и семейного бита не было.
                    self._remember(x, y, known_bit=False)
            for a, b, old_bit in list(self._old.values()):
                new_bit = _family_bit(a, b)
                if new_bit is old_bit:
                    continue
                # SimInfo.add_family_link кладёт бит a→b в трекер b с ключом a.
                tracker = b.relationship_tracker
                if old_bit is not None and tracker.has_bit(a.sim_id, old_bit):
                    tracker.remove_relationship_bit(a.sim_id, old_bit)
                if new_bit is not None:
                    a.add_family_link(b)


# --- Изменение древа ------------------------------------------------------

def _slot_for(parent):
    idx = _indexes()
    return idx.MOTHER if parent.is_female else idx.FATHER


def _other_slot(slot):
    idx = _indexes()
    return idx.FATHER if slot == idx.MOTHER else idx.MOTHER


def _write_parent(child, slot, parent):
    if hasattr(child, 'set_parent_relation'):  # новая версия: семейное древо обновится само
        child.set_parent_relation(slot, parent, is_adopted=False)
        return
    child.set_and_propagate_family_relation(slot, parent)
    for grandchild in children(child):  # старая версия: обновляем бабушек/дедушек у внуков
        for gslot, pid in parents(grandchild).items():
            if pid == child.sim_id:
                grandchild.set_and_propagate_family_relation(gslot, child)


def _clear_parent(child, slot):
    idx = _indexes()
    tree = _family_tree_service()
    if tree is not None and hasattr(child, 'set_parent_relation'):
        # Новая версия: очищаются оба родителя, второго возвращаем (так же делает S4CL).
        other = _sim_info(parent_id(child, _other_slot(slot)))
        from family_tree.family_tree_enums import FamilyRelationBitFlags
        tree.clear_family_relation(child.sim_id, relationship_enum=FamilyRelationBitFlags.PARENT)
        if other is not None:
            child.set_parent_relation(_other_slot(slot), other, is_adopted=False)
        return
    side = (idx.MOTHERS_MOM, idx.MOTHERS_FATHER) if slot == idx.MOTHER else (idx.FATHERS_MOM, idx.FATHERS_FATHER)
    for relation in (slot,) + side:
        child.genealogy.clear_family_relation(relation)
    for grandchild in children(child):
        for gslot, pid in parents(grandchild).items():
            if pid != child.sim_id:
                continue
            if gslot == idx.MOTHER:
                grand = idx.MOTHERS_MOM if slot == idx.MOTHER else idx.MOTHERS_FATHER
            else:
                grand = idx.FATHERS_MOM if slot == idx.MOTHER else idx.FATHERS_FATHER
            grandchild.genealogy.clear_family_relation(grand)


def check_parent(parent, child):
    if parent.sim_id == child.sim_id:
        raise CheatError('Сим не может быть родителем самому себе.')
    if parent.species != child.species:
        raise CheatError('Родитель и ребёнок должны быть одного вида.')
    if not is_adult(parent):
        raise CheatError('{} слишком молод(а), чтобы быть родителем.'.format(full_name(parent)))
    if int(parent.age) < int(child.age):
        raise CheatError('Родитель не может быть младше ребёнка.')
    with _ChildrenIndex():
        is_descendant = parent.sim_id in {d.sim_id for d in descendants(child)}
    if is_descendant:
        raise CheatError('{} — потомок {}: получится петля в древе.'.format(full_name(parent), full_name(child)))
    slot = _slot_for(parent)
    current = parent_id(child, slot)
    if current == parent.sim_id:
        raise CheatError('Эта связь уже есть.')
    if current:
        raise CheatError('У {} уже есть {}. Сначала уберите его/её.'.format(
            full_name(child), 'мать' if slot == _indexes().MOTHER else 'отец'))
    return slot


def set_parent(parent, child):
    slot = check_parent(parent, child)
    refresher = _BitRefresher(child)
    _write_parent(child, slot, parent)
    refresher.apply()


def remove_parent(child, parent):
    slots = [s for s, pid in parents(child).items() if pid == parent.sim_id]
    if not slots:
        raise CheatError('{} не родитель {}.'.format(full_name(parent), full_name(child)))
    refresher = _BitRefresher(child)
    for slot in slots:
        _clear_parent(child, slot)
    refresher.apply()


def make_siblings(a, b):
    """Братья/сёстры в игре — это общие родители. B получает родителей A."""
    a_parents = parents(a)
    if not a_parents:
        raise CheatError('У {} нет родителей в древе. Сначала назначьте общего родителя.'.format(full_name(a)))
    b_parents = parents(b)
    to_set = []
    for slot, pid in a_parents.items():
        if b_parents.get(slot) == pid:
            continue
        if b_parents.get(slot):
            raise CheatError('У {} уже другой родитель. Сначала уберите его.'.format(full_name(b)))
        parent = _sim_info(pid)
        if parent is None:
            raise CheatError('Родитель {} не найден в игре.'.format(full_name(a)))
        to_set.append(parent)
    if not to_set:
        raise CheatError('Они уже братья/сёстры.')
    for parent in to_set:
        check_parent(parent, b)
    refresher = _BitRefresher(b)
    for parent in to_set:
        _write_parent(b, _slot_for(parent), parent)
    refresher.apply()


# --- Брак -----------------------------------------------------------------

def _marriage_bit():
    from relationships.global_relationship_tuning import RelationshipGlobalTuning
    return RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT


def current_spouses(sim_info):
    bit = _marriage_bit()
    manager = services.sim_info_manager()
    result = {}
    spouse = _sim_info(sim_info.relationship_tracker.spouse_sim_id)
    if spouse is not None:
        result[spouse.sim_id] = spouse
    for target_id in sim_info.relationship_tracker.target_sim_gen():
        target = manager.get(target_id)
        if target is not None and (sim_info.relationship_tracker.has_bit(target_id, bit)
                                   or target.relationship_tracker.has_bit(sim_info.sim_id, bit)):
            result[target_id] = target
    return list(result.values())


def _remove_bit_both_ways(a, b, bit):
    if bit is None:
        return
    for x, y in ((a, b), (b, a)):
        if x.relationship_tracker.has_bit(y.sim_id, bit):
            x.relationship_tracker.remove_relationship_bit(y.sim_id, bit)


def divorce(sim_info, spouse=None):
    from sims.genealogy_tracker import FamilyRelationshipTuning
    divorced_bit = getattr(FamilyRelationshipTuning, 'DIVORCED_SPOUSE_RELATIONSHIP_BIT', None)
    spouses = [spouse] if spouse is not None else current_spouses(sim_info)
    if not spouses:
        raise CheatError('{} не состоит в браке.'.format(full_name(sim_info)))
    for other in spouses:
        _remove_bit_both_ways(sim_info, other, _marriage_bit())
        if divorced_bit is not None:
            for x, y in ((sim_info, other), (other, sim_info)):
                if not x.relationship_tracker.has_bit(y.sim_id, divorced_bit):
                    x.relationship_tracker.add_relationship_bit(y.sim_id, divorced_bit)


def marry(a, b):
    if a.sim_id == b.sim_id:
        raise CheatError('Нельзя жениться на самом себе.')
    if not (is_adult(a) and is_adult(b)):
        raise CheatError('Вступать в брак могут только взрослые.')
    if a.species != b.species:
        raise CheatError('Супруги должны быть одного вида.')
    if are_blood_related(a, b):
        raise CheatError('Они родственники — игра это запрещает.')
    bit = _marriage_bit()
    for sim in (a, b):  # как ForceMarriageInteraction: сначала снимаем старые браки
        for old in current_spouses(sim):
            if old.sim_id not in (a.sim_id, b.sim_id):
                _remove_bit_both_ways(sim, old, bit)
    for x, y in ((a, b), (b, a)):
        if not x.relationship_tracker.has_bit(y.sim_id, bit):
            x.relationship_tracker.add_relationship_bit(y.sim_id, bit)


# --- Для меню -------------------------------------------------------------

def describe(sim_info):
    lines = []
    idx = _indexes()
    for slot, label in ((idx.MOTHER, 'Мать'), (idx.FATHER, 'Отец')):
        parent = _sim_info(parent_id(sim_info, slot))
        lines.append('{}: {}'.format(label, full_name(parent) if parent else '—'))
    kids = children(sim_info)
    lines.append('Дети: {}'.format(', '.join(full_name(k) for k in kids) if kids else '—'))
    spouses = current_spouses(sim_info)
    lines.append('Супруг(а): {}'.format(', '.join(full_name(s) for s in spouses) if spouses else '—'))
    return '\n'.join(lines)
