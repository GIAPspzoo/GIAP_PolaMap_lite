# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os
import qgis
from qgis.core import QgsProject
from .CompositionsLib import get_all_groups_layers, LayersPanel, get_checked_layers_ids_from_composition, \
    get_layers_ids_from_composition
from GIAP_funkcje import (identify_layer_in_group, get_project_config)

default_compositions = {}

# 	'Adresat': [('ADRESAT', 'AD_PunktAdresowy', True),
# 	            ('GRANICE', 'DZIAŁKI EWIDENCYJNE', True)],
# 	'PRZEZNACZENIE MPZP STANDARD': [],
# 	'PRZEZNACZENIE MPZP ORYGINAŁ': [],
# 	'PLIKI RASTROWE': [('DOKUMENTY PLANISTYCZNE', 'PLIKI RASTROWE', True)],
# 	'PLIKI RASTROWE PRZYCIĘTE': [('', 'PLIKI RASTROWE PRZYCIĘTE', True)],
# }

def update_wszystkie_default_compositions():
    wszystkie_layer_list = [
        'DZIAŁKI EWIDENCYJNE',
        'PRZEZNACZENIE MPZP',
    ]
    all_layers = get_all_groups_layers()
    n = []
    for layer_path in all_layers:
        splitted_layer = layer_path.rsplit(':')
        group = ':'.join(splitted_layer[:-1]) if len(
            splitted_layer) > 1 else ''
        layer = splitted_layer[-1]
        if layer in wszystkie_layer_list:
            n.append((group, layer, True))
        else:
            n.append((group, layer, False))
    default_compositions['Wszystkie warstwy'] = n


def update_mpzp_default_compositions():
    mpzp_groups = [
        'DOKUMENTY PLANISTYCZNE',
        'PLIKI RASTROWE PRZYCIĘTE',
    ]
    mpzp_layers = [
        'PRZEZNACZENIE MPZP'
    ]
    all_layers = get_all_groups_layers()
    n = []
    for layer_path in all_layers:
        splitted_layer = layer_path.rsplit(':')
        group = ':'.join(splitted_layer[:-1]) if len(
            splitted_layer) > 1 else ''
        for mg in mpzp_groups:
            if mg in group:
                layer = splitted_layer[-1]
                if layer in mpzp_layers:
                    n.append((group, layer, True))
                else:
                    n.append((group, layer, False))
    default_compositions['PRZEZNACZENIE MPZP ORYGINAŁ'] = n
    default_compositions['PRZEZNACZENIE MPZP STANDARD'] = n


def update_pliki_rastrowe_compositions():
    all_layers = get_all_groups_layers()
    n = []
    for layer_path in all_layers:
        splitted_layer = layer_path.rsplit(':')
        group = ':'.join(splitted_layer[:-1]) if len(
            splitted_layer) > 1 else ''
        if 'DOKUMENTY PLANISTYCZNE:PLIKI RASTROWE' in group:
            layer = splitted_layer[-1]
            n.append((group, layer, True))
    default_compositions['PLIKI RASTROWE'] = n


def update_pliki_rastrowe_przyciete_compositions():
    all_layers = get_all_groups_layers()
    n = []
    for layer_path in all_layers:
        splitted_layer = layer_path.rsplit(':')
        group = ':'.join(splitted_layer[:-1]) if len(
            splitted_layer) > 1 else ''
        if 'PLIKI RASTROWE PRZYCIĘTE' in group:
            layer = splitted_layer[-1]
            n.append((group, layer, True))
    default_compositions['PLIKI RASTROWE PRZYCIĘTE'] = n


def update_default_compositions():
    update_wszystkie_default_compositions()


def __show_specified_groups(groups=['DOKUMENTY PLANISTYCZNE',
                                    'PLIKI RASTROWE PRZYCIĘTE']):
    # dokumenty planistyczne i rastry przyciete do widoku
    panel = LayersPanel()
    panel.uncheckAll()
    panel.hideUncheckedNodes()
    for group_name in groups:
        group = panel.root.findGroup(group_name)
        panel.hideNode(group, False)
        panel.showHiddenNodes(group)


def load_qml_to_layer(layer, qml_name):
    qml_path = ''
    prjpath = QgsProject.instance().fileName()
    proj_dir = os.path.dirname(os.path.abspath(prjpath))
    up_dir = os.path.dirname(proj_dir)
    for file in os.listdir(os.path.join(up_dir, 'PLIKI_WEKTOROWE', "MPZP")):
        if file.endswith(qml_name):
            qml_path = os.path.join(up_dir, 'PLIKI_WEKTOROWE', "MPZP", file)
    if os.path.exists(qml_path):
        layer.loadNamedStyle(qml_path)
        layer.triggerRepaint()


def set_mpzp_strefy_linie():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP', 'STREFY LINIE')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])

def set_mpzp_wymiarowanie():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP', 'WYMIAROWANIE')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])

def set_punktowe_standard():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP',
                                        'DODATKOWE INFORMACJE PUNKTOWE')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])
        load_qml_to_layer(
            map_layer,
            'mpzp_dodatkowe_punktowe_S_STANDARD.qml'
        )


def set_punktowe_oryginal():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP',
                                        'DODATKOWE INFORMACJE PUNKTOWE')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])
        load_qml_to_layer(
            map_layer,
            'mpzp_dodatkowe_punktowe_S_ORYGINAL.qml'
        )


def set_liniowe_standard():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP',
                                        'DODATKOWE INFORMACJE LINIOWE')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])
        load_qml_to_layer(
            map_layer,
            'mpzp_dodatkowe_liniowe_S_STANDARD.qml'
        )


def set_liniowe_oryginal():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP',
                                        'DODATKOWE INFORMACJE LINIOWE')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])
        load_qml_to_layer(
            map_layer,
            'mpzp_dodatkowe_liniowe_S_ORYGINAL.qml'
        )


def set_mpzp_standard():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP',
                                        'PRZEZNACZENIE MPZP')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])
        load_qml_to_layer(
            map_layer,
            'mpzp_przeznaczenie_S_STANDARD.qml'
        )


def set_mpzp_oryginal():
    __show_specified_groups()
    map_layer = identify_layer_in_group('MPZP',
                                        'PRZEZNACZENIE MPZP')
    if map_layer:
        LayersPanel().checkLayersByIds([map_layer.id()])
        load_qml_to_layer(
            map_layer,
            'mpzp_przeznaczenie_S_ORYGINAL.qml'
        )


def set_pliki_rastrowe():
    update_default_compositions()
    comp = get_compositions()
    rastry = ['DOKUMENTY PLANISTYCZNE:PLIKI RASTROWE']
    LayersPanel().checkGroupsByName(rastry)
    LayersPanel().hideUncheckedNodes()
    if not comp['PLIKI RASTROWE'][0][2]:
        LayersPanel().uncheckGroupsByName(rastry)
    set_default_styles()


def set_pliki_rastrowe_przyciete():
    comp = get_compositions()
    rastry_przyciete = ['PLIKI RASTROWE PRZYCIĘTE']
    LayersPanel().checkGroupsByName(rastry_przyciete)
    LayersPanel().hideUncheckedNodes()
    if not comp['PLIKI RASTROWE PRZYCIĘTE'][0][2]:
        LayersPanel().uncheckGroupsByName(rastry_przyciete)
    set_default_styles()


def set_wszystkie_warstwy():
    comp = get_compositions()
    checked_layers_ids, groups = get_checked_layers_ids_from_composition(comp['Wszystkie warstwy']['layers']
    )
    LayersPanel().checkLayersByIds(checked_layers_ids)
    LayersPanel().checkGroupsByName(groups)


compositons_special = {
    # 'MPZP STREFY LINIE': set_mpzp_strefy_linie,
    # 'DODATKOWE PUNKTOWE STANDARD': set_punktowe_standard,
    # 'DODATKOWE PUNKTOWE ORYGINAŁ': set_punktowe_oryginal,
    # 'DODATKOWE LINIOWE STANDARD': set_liniowe_standard,
    # 'DODATKOWE LINIOWE ORYGINAŁ': set_liniowe_oryginal,
    'PRZEZNACZENIE MPZP STANDARD': set_mpzp_standard,
    'PRZEZNACZENIE MPZP ORYGINAŁ': set_mpzp_oryginal,
    # 'PLIKI RASTROWE': set_pliki_rastrowe,
    # 'PLIKI RASTROWE PRZYCIĘTE': set_pliki_rastrowe_przyciete,
    'Wszystkie warstwy': set_wszystkie_warstwy,
}


def get_compositions():
    update_default_compositions()
    comp = eval(
        get_project_config('Kompozycje',
                           'domyslne_kompozycje',
                           str(default_compositions)
                           )
    )
    for name in default_compositions:
        if name not in comp:
            comp[name] = default_compositions[name]
    return comp


def compositions_names():
    compositions_dict = get_compositions()
    sorted_comps = sorted(list(compositions_dict.items()), key=lambda x: x[1]['order'])
    sorted_comps_names = [y[0] for y in sorted_comps]
    return sorted_comps_names


def set_simple_composition(name):
    compositions = get_compositions()
    layers_ids = get_layers_ids_from_composition(
        compositions[name]['layers'])
    checked_layers_ids = get_checked_layers_ids_from_composition(
        compositions[name]['layers'])
    LayersPanel().checkLayersByIds(layers_ids)
    # ukryj wszystkie warstwy i grupy ktore nie sa zaznaczone
    LayersPanel().hideUncheckedNodes()
    LayersPanel().uncheckAll()
    LayersPanel().checkLayersByIds(checked_layers_ids)
    set_default_styles()


def set_composition(name):
    if name in compositons_special:
        compositons_special[name]()
    else:
        set_simple_composition(name)


def set_default_styles_decorator(func):
    def set_default_styles_wrapper():
        giap_layout = 'giap_layout'
        if giap_layout in qgis.utils.plugins:
            spdp = qgis.utils.plugins[giap_layout]
            combo = giap_layout.main_widget.styleComboBox
            text = u'MPZP ORYGINAŁ'
            text_id = combo.findText(text)
            if text_id == -1:
                func()
        else:
            func()
    return set_default_styles_wrapper


@set_default_styles_decorator
def set_default_styles():
    layers_qml = {
        'DODATKOWE INFORMACJE PUNKTOWE': 'mpzp_dodatkowe_punktowe_S_ORYGINAL.qml',
        'DODATKOWE INFORMACJE LINIOWE': "mpzp_dodatkowe_liniowe_S_ORYGINAL.qml",
        'PRZEZNACZENIE MPZP': 'mpzp_przeznaczenie_S_ORYGINAL.qml',
    }
    for layer, qml in list(layers_qml.items()):
        map_layer = identify_layer_in_group('MPZP', layer)
        if map_layer:
            load_qml_to_layer(map_layer, qml)
