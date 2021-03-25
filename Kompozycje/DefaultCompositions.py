# -*- coding: utf-8 -*-

from __future__ import absolute_import
from .CompositionsLib import get_all_groups_layers, LayersPanel, \
    get_checked_layers_ids_from_composition, get_layers_ids_from_composition,\
    get_map_layer
from ..utils import (identify_layer_in_group, get_project_config)

default_compositions = {}


def update_all_default_compositions():
    all_layers_list = []
    sel_list = LayersPanel().start_getting_visible_layers()
    for group_layer in get_all_groups_layers():
        colon_index = group_layer.rfind(':')
        if colon_index == -1:
            layer_group = ''
        else:
            layer_group = group_layer[:colon_index]
        layer_name = group_layer[colon_index + 1:]
        map_layer, layer_group, layer_name = get_map_layer(
            layer_group, layer_name)
        active = True if map_layer.id() in sel_list else False
        all_layers_list.append(
            (layer_group, layer_name, map_layer.id(), active)
        )
    if {False} != set([x[3] for x in all_layers_list]):
        default_compositions['Wszystkie warstwy'] = all_layers_list


def set_wszystkie_warstwy():
    comp = get_compositions()
    checked_layers_ids, groups = get_checked_layers_ids_from_composition(
        comp['Wszystkie warstwy']['layers']
    )
    LayersPanel().checkLayersByIds(checked_layers_ids)
    LayersPanel().checkGroupsByName(groups)


compositons_special = {
    'Wszystkie warstwy': set_wszystkie_warstwy,
}


def get_compositions():
    update_all_default_compositions()
    comp = {
        'Wszystkie warstwy': {
            'id': '1',
            'order': 0,
            'layers': default_compositions['Wszystkie warstwy'],
        }
    }
    return comp


def set_composition(name):
    if name in compositons_special:
        compositons_special[name]()


def compositions_names():
    compositions_dict = get_compositions()
    sorted_comps = sorted(list(compositions_dict.items()),
                          key=lambda x: x[1]['order'])
    sorted_comps_names = [y[0] for y in sorted_comps]
    return sorted_comps_names
