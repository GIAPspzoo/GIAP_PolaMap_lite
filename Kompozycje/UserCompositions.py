# coding=utf-8

from .CompositionsLib import (
    LayersPanel,
    get_layers_ids_from_composition,
    get_checked_layers_ids_from_composition,
)
from GIAP_funkcje import get_project_config

"""
Kompozycje użytkownika.

Kompozycje użytkownika zapisane są w projekcie QGisa w postaci napisu
reprezentującego następującą strukturę:

{
    nazwa_kompozycji: [
                       (nazwa_grupy, nazwa_warstwy, czy_zaznaczona),
                       (nazwa_grupy/nazwa_podgrupy, nazwa_warstwy, czy_zaznaczona),
                       ...
                      ]
    nazwa_kompozycji2: [
                       (nazwa_grupy, nazwa_warstwy, czy_zaznaczona),
                       (nazwa_grupy/nazwa_podgrupy, nazwa_warstwy, czy_zaznaczona),
                       ...
                      ]
    ...

}
"""


def get_compositions():
    return eval(get_project_config('Kompozycje', 'stworzone_kompozycje', '{}'))


def compositions_names():
    compositions_dict = get_compositions()
    sorted_comps = sorted(list(compositions_dict.items()), key=lambda x: x[1]['order'])
    sorted_comps_names = [y[0] for y in sorted_comps]
    return sorted_comps_names


def set_composition(name):
    compositions = get_compositions()
    layers_ids, groups = get_layers_ids_from_composition(compositions[name]['layers'])
    checked_layers_ids, g = get_checked_layers_ids_from_composition(compositions[name]['layers'])
    LayersPanel().uncheckAll()
    LayersPanel().uncheckAllGroup()
    LayersPanel().checkGroupsByName(groups)
    LayersPanel().checkLayersByIds(layers_ids)
    LayersPanel().hideUncheckedNodes()
    LayersPanel().uncheckAll()
    LayersPanel().uncheckAllGroup()
    LayersPanel().checkGroupsByName(groups)
    LayersPanel().checkLayersByIds(checked_layers_ids)


