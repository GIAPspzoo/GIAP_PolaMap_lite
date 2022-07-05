# -*- coding: utf-8 -*-

import qgis
from PyQt5.QtCore import Qt
from qgis.core import QgsProject, QgsMapLayer, QgsLayerTreeGroup, \
    QgsLayerTreeLayer, QgsLayerTreeModel, QgsLayerTree


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@singleton
class LayersPanel(object):
    def __init__(self):
        self.iface = qgis.utils.iface
        self.ltv = self.iface.layerTreeView()
        self.model = self.ltv.layerTreeModel()
        self.root = QgsProject.instance().layerTreeRoot()

    def runHide(self):
        selectedNodes = self.ltv.selectedNodes(True)
        for node in selectedNodes:
            self.hideNode(node)

    def runShow(self):
        self.showHiddenNodes(self.root)

    def hideNode(self, node, bHide=True):
        if type(node) in (QgsLayerTreeLayer, QgsLayerTreeGroup):
            try:
                index = self.ltv.node2index(node)
            except:
                index = self.model.node2index(node)
            self.ltv.setRowHidden(index.row(), index.parent(), bHide)
            node.setCustomProperty('nodeHidden', 'true' if bHide else 'false')
            self.ltv.setCurrentIndex(self.model.node2index(self.root))

    def showHiddenNodes(self, group):
        for child in group.children():
            if child.customProperty(
                    "nodeHidden") == 'true':  # Node is currently hidden
                self.hideNode(child, False)
            if isinstance(child, QgsLayerTreeGroup):  # Continue iterating
                self.showHiddenNodes(child)

    def hideNodesByProperty(self, group):
        for child in group.children():
            if child.customProperty(
                    "nodeHidden") == 'true':  # Node should be hidden
                self.hideNode(child)
            if isinstance(child, QgsLayerTreeGroup):  # Continue iterating
                self.hideNodesByProperty(child)

    def readHiddenNodes(self):
        """ SLOT """
        self.hideNodesByProperty(self.root)

    def hideLayer(self, mapLayer):
        if isinstance(mapLayer, QgsMapLayer):
            self.hideNode(self.root.findLayer(mapLayer.id()))

    def hideLayerById(self, mapLayerId):
        self.hideNode(self.root.findLayer(mapLayerId))

    def hideGroup(self, group):
        if isinstance(group, QgsLayerTreeGroup):
            self.hideNode(group)
        elif isinstance(group, str):
            self.hideGroup(self.root.findGroup(group))

    def hideUncheckedGroups(self, group):
        for g in group.children():
            if not g.isVisible():
                self.hideGroup(g)
            else:
                self.hideUncheckedGroups(g)

    def hideUncheckedLayers(self, group):
        for layer in group.findLayers():
            if not layer.isVisible():
                self.hideNode(layer)

    def hideUncheckedNodes(self):
        root = QgsProject.instance().layerTreeRoot()
        self.hideUncheckedLayers(root)
        self.hideUncheckedGroups(root)

    def uncheckAll(self):
        root = QgsProject.instance().layerTreeRoot()
        for layer in root.findLayers():
            layer.setItemVisibilityChecked(False)

    def uncheckAllGroup(self):
        for group in self.root.children():
            group.setItemVisibilityChecked(False)

    def checkAll(self):
        root = QgsProject.instance().layerTreeRoot()
        for layer in root.findLayers():
            layer.setItemVisibilityChecked(True)

    def getVisibleLayersList(self):
        """zwraca liste wlaczonych warstw w panelu warstw
        do jednego dziecka (grupa:warswa albo grupa:podgrupa)"""
        l = []
        for group in self.root.children():
            if group.isVisible() in (Qt.Checked, Qt.PartiallyChecked):
                for layer in group.children():
                    if layer.isVisible() in (Qt.Checked, Qt.PartiallyChecked):
                        l.append(get_qgs_layer_tree_node_name(
                            group) + ":" + get_qgs_layer_tree_node_name(layer))
        return l

    def start_getting_visible_layers(self):
        root = QgsProject.instance().layerTreeRoot()
        tmp_list = []
        self.get_visible_layer_list_from_all_groups(tmp_list, root)
        return tmp_list

    def get_visible_layer_list_from_all_groups(self, lista, group):
        """
        Funkcja dodaje do listy zaznaczone warstwy w projekcie
        szukając po grupach dla wszystich grup
        (nawet podrzednych a nie tylko dla jednego dziecka)
        """
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                if child.isVisible() in (Qt.Checked, Qt.PartiallyChecked):
                    self.get_visible_layer_list_from_all_groups(lista, child)
            else:
                if child.isVisible() in (Qt.Checked, Qt.PartiallyChecked):
                    lista.append(child.layerId())

    def checkLayersByIds(self, layers_ids):
        layers = QgsProject.instance().mapLayers()

        def change_layers_visibility(layer):
            if layer in layers_ids:
                self.root.findLayer(layer).setItemVisibilityChecked(Qt.Checked)

        list(map(change_layers_visibility, layers))

    def checkGroupsByName(self, groups):
        root = self.root
        e_groups = {}
        for group_names in groups:
            group_list = group_names.split(':')
            external_group_name = group_list[0]
            if external_group_name in list(e_groups.keys()):
                if len(group_list) > 1:
                    e_groups[external_group_name].append(group_list[1])
            else:
                if len(group_list) > 1:
                    e_groups[external_group_name] = group_list
                else:
                    e_groups[external_group_name] = []
        for group in root.children():
            name = get_qgs_layer_tree_node_name(group)
            if name in list(e_groups.keys()):
                group.setItemVisibilityChecked(Qt.Checked)
                this_group_layers = e_groups[name]
                if len(this_group_layers) > 1:
                    subgroups = group.children()
                    for subgroup in subgroups:
                        subgroup_name = get_qgs_layer_tree_node_name(subgroup)
                        if subgroup_name in this_group_layers:
                            subgroup.setItemVisibilityChecked(Qt.Checked)
                        else:
                            subgroup.setItemVisibilityChecked(Qt.Unchecked)

    def uncheckGroupsByName(self, groups):
        root = self.root
        e_groups = {}
        for group_names in groups:
            group_list = group_names.split(':')
            external_group_name = group_list[0]
            if external_group_name in list(e_groups.keys()):
                if len(group_list) > 1:
                    e_groups[external_group_name].append(group_list[1])
            else:
                if len(group_list) > 1:
                    e_groups[external_group_name] = group_list
                else:
                    e_groups[external_group_name] = []
        for group in root.children():
            name = get_qgs_layer_tree_node_name(group)
            if name in list(e_groups.keys()):
                group.setItemVisibilityChecked(Qt.Unchecked)
                this_group_layers = e_groups[name]
                if len(this_group_layers) > 1:
                    subgroups = group.children()
                    for subgroup in subgroups:
                        subgroup_name = get_qgs_layer_tree_node_name(subgroup)
                        if subgroup_name in this_group_layers:
                            subgroup.setItemVisibilityChecked(Qt.Unchecked)
                        else:
                            subgroup.setItemVisibilityChecked(Qt.Checked)


def get_qgs_layer_tree_node_name(node):
    return node.name()


def get_qgs_layer_tree_node_id(node):
    if isinstance(node, QgsLayerTreeGroup):
        return node.layerId()
    else:
        return node.name()


def get_groups_from_composition(composition):
    groups = []
    for c in composition:
        group = c[0]
        if group not in groups:
            groups.append(group)
    return groups


def get_layers_ids_from_composition(composition):
    layer_ids = []
    groups_check = []
    for c in composition:
        group = c[0]
        layer = c[1]
        groups = group.split(':')
        map_layer = identify_layer_in_groups(layer, groups)
        if map_layer:
            layer_ids.append(map_layer.id())
            groups_check.append(group)
    return layer_ids, list(set(groups_check))


def get_checked_layers_ids_from_composition(composition):
    layer_ids = []
    groups_check = []
    for c in composition:
        group = c[0]
        layer = c[1]
        checked = True
        if len(c) > 3:
            checked = c[3]
        if checked:
            groups = group.split(':')
            map_layer = identify_layer_in_groups(layer, groups)
            if map_layer:
                layer_ids.append(map_layer.id())
                groups_check.append(group)
    return layer_ids, list(set(groups_check))


def get_layers_from_group(lista, group, group_name):
    for child in group.children():
        if isinstance(child, QgsLayerTreeGroup):
            if group_name:
                s = group_name + ':'
            else:
                s = ''
            get_layers_from_group(lista, child,
                                  s + get_qgs_layer_tree_node_name(child))
        else:
            if group_name:
                s = group_name + ':'
            else:
                s = ''
            lista.append(s + get_qgs_layer_tree_node_name(child))


def get_all_groups_layers():
    root = QgsProject.instance().layerTreeRoot()
    tmp_list = []
    get_layers_from_group(tmp_list, root, '')
    return tmp_list


def get_map_layer(layer_group, layer_name):
    if layer_group:
        groups = layer_group.split(':')
        map_layer = identify_layer_in_groups(layer_name, groups)
    else:
        map_layer = identify_layer_out_of_groups(layer_name)
    if not map_layer and layer_group:
        layer_name_part = layer_group.split(':')[-1]
        layer_name = '{}:{}'.format(layer_name_part, layer_name)
        if layer_name_part == layer_group:
            map_layer = identify_layer_out_of_groups(layer_name)
        else:
            groups = layer_group.split(':')[:-1]
            map_layer = identify_layer_in_groups(layer_name, groups)
            layer_group = layer_group[:layer_group.rindex(':')]
    return map_layer, layer_group, layer_name


def layer_tree_layer_in_groups(layer, groups):
    """
    :type layer: QgsLayerTreelayer
    :type groups: String list with group and subgroups
    """
    node = layer
    for group in reversed(groups):
        parent_name = node.parent().name()
        if parent_name != group:
            return False
        node = node.parent()
    return True


def identify_layer_in_groups(layer_to_find, groups):
    root = QgsProject.instance().layerTreeRoot()
    for lr in root.findLayers():
        if lr.layer().name() == layer_to_find and layer_tree_layer_in_groups(
                lr, groups):
            return lr.layer()
    return


def identify_layer_out_of_groups(layer_to_find):
    root = QgsProject.instance().layerTreeRoot()
    for lr in root.findLayers():
        if lr.layer().name() == layer_to_find and not lr.parent().name():
            return lr.layer()
    return


def get_groups(layerid):
    node = None
    root = QgsProject.instance().layerTreeRoot()
    for lr in root.findLayers():
        if lr.layer().id() == layerid:
            node = lr
            break
    groups_list = []
    if isinstance(node, QgsLayerTreeLayer):
        while node.parent().name():
            groups_list.append(node.parent().name())
            node = node.parent()
    return ':'.join(reversed(groups_list))


def change_visibility(ch):
    if isinstance(ch, QgsLayerTreeLayer) and ch.customProperty(
            "nodeHidden") == 'true':
        ch.setItemVisibilityChecked(Qt.Unchecked)


def connect_nodes(group):
    for ch in group.children():
        if isinstance(ch, QgsLayerTreeGroup):
            ch.visibilityChanged.connect(change_visibility)
            connect_nodes(ch)


def disconnect_nodes(group):
    for ch in group.children():
        if isinstance(ch, QgsLayerTreeGroup):
            try:
                ch.visibilityChanged.disconnect(change_visibility)
            except:
                pass
            disconnect_nodes(ch)
