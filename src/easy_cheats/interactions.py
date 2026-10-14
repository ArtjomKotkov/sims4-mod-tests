# Easy Cheats Menu — пункт «Easy Cheats» в круглом меню сима (тюнинг лежит в EasyCheats.package).
import services
import sims4.resources
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from sims4.tuning.instance_manager import InstanceManager

from easy_cheats import menus
from easy_cheats.dialogs import logger, run_safely

# Должно совпадать с build-package.js (fnv64('EasyCheats:Interaction_OpenMenu') со старшим битом).
OPEN_MENU_INTERACTION_ID = 16701209688680602853
OBJECT_SIM_ID = 14965  # тюнинг object_sim — общий для всех людей


class EasyCheatsOpenMenuInteraction(ImmediateSuperInteraction):

    def _run_interaction_gen(self, timeline):
        target = getattr(self.target, 'sim_info', None) or self.sim.sim_info
        run_safely(menus.main_menu, target)
        return True
        yield  # генератор, как требует движок взаимодействий


def _add_to_sim_pie_menu(object_manager):
    affordance = services.get_instance_manager(sims4.resources.Types.INTERACTION).types.get(
        sims4.resources.get_resource_key(OPEN_MENU_INTERACTION_ID, sims4.resources.Types.INTERACTION))
    if affordance is None:
        logger.error('EasyCheats.package не найден: пункт в меню сима не добавлен.')
        return
    object_sim = object_manager.types.get(
        sims4.resources.get_resource_key(OBJECT_SIM_ID, sims4.resources.Types.OBJECT))
    if object_sim is None or affordance in object_sim._super_affordances:
        return
    object_sim._super_affordances += (affordance,)


_original_load = InstanceManager.load_data_into_class_instances


def _load_data_into_class_instances(self, *args, **kwargs):
    result = _original_load(self, *args, **kwargs)
    if self.TYPE == sims4.resources.Types.OBJECT:
        try:
            _add_to_sim_pie_menu(self)
        except Exception as exc:
            logger.exception('Easy Cheats: pie menu injection failed', exc=exc)
    return result


InstanceManager.load_data_into_class_instances = _load_data_into_class_instances
