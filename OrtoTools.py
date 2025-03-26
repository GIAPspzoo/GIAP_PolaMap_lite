# -*- coding: utf-8 -*-
from typing import Union

from qgis.PyQt.QtCore import QVariant, NULL
from qgis.core import QgsLayerTreeLayer, QgsLayerTreeGroup
from qgis.PyQt.QtWidgets import QToolButton, QMenu, QAction

from .Wms_wmts import WMS_WMTS
from .Wms_wmts import orto_action_service
from .utils import tr

def check_if_value_empty(value: Union[str, None, QVariant]) -> bool:
    return value in [None, NULL, 'NULL', 'None', '']

class OrtoAddingTool(object):
    def __init__(self, parent, button, iface, group_names=None):
        self.parent = parent
        self.button = button
        self.iface = iface
        self.button.setToolTip(tr("Add defined WMS/WMTS addresses"))
        self.button.setPopupMode(QToolButton.InstantPopup)
        self.group_names = group_names
        self.layer_actions_dict = {}
        self.services = []
        self.data = orto_action_service.get_wms_config()
        self.create_menu()
        self.connect_ortofotomapa_group()
        orto_action_service.project.projectSaved.connect(self.remove_wms_wmts_temp_group)

    def get_group_names(self) -> set:
        return set([value[1] for value in self.data.values() if value])

    def connect_ortofotomapa_group(self) -> None:
        for group_name in self.get_group_names():
            group = orto_action_service.root.findGroup(group_name)
            if group:
                group.visibilityChanged.connect(self.my_refresh_menu)
                group.addedChildren.connect(self.my_refresh_menu)
                group.removedChildren.connect(self.my_refresh_menu)

    def disconnect_ortofotomapa_group(self) -> None:
        for group_name in self.get_group_names():
            group = orto_action_service.root.findGroup(group_name)
            if group:
                try:
                    group.visibilityChanged.disconnect(self.my_refresh_menu)
                    group.addedChildren.disconnect(self.my_refresh_menu)
                    group.removedChildren.disconnect(self.my_refresh_menu)
                except:
                    pass

    def action_clicked(self, item: QAction) -> None:
        self.layer_name = item.text()
        source, group_name = self.return_orto_data(item)
        identified_layers_list = orto_action_service.project.mapLayersByName(self.layer_name)
        group = orto_action_service.root.findGroup(self.layer_name)
        if identified_layers_list:
            try:
                for map_layer in identified_layers_list:
                    if orto_action_service.root.findLayer(map_layer).parent().name() == group_name and map_layer.source() == source:
                        self.set_visibility(map_layer, item)
                for layer, action in self.layer_actions_dict.items():
                    self.set_visibility(layer, action)
            except RuntimeError:
                item.setChecked(True)

    def set_visibility(self, layer, action):
        item = orto_action_service.root.findLayer(layer)
        if item:
            item.parent().setItemVisibilityChecked(True)
            item.setItemVisibilityCheckedRecursive(action.isChecked())

    def my_refresh_menu(self):
        self.data = orto_action_service.get_wms_config()
        try:
            self.create_menu(self.parent.runOrtoTool)
        except:
            self.create_menu(self.parent.main_widgets.runOrtoTool)
        tab_lay = []
        try:
            tabs = self.parent.tabs
        except:
            tabs = self.parent.main_widgets.tabs

        for tab in tabs:
            for index in range(tab.lay.count()):
                if tab.lay.itemAt(index).widget():
                    if tab.lay.itemAt(index).widget().objectName() == 'giapSection':
                        for ch in tab.lay.itemAt(index).widget().children():
                            if ch.objectName() == 'giapWMS':
                                tab_lay.append(ch)

        for button in tab_lay:
            button.setMenu(self.ortomenu)

    def create_menu(self, but=None) -> None:
        layers_names = []
        self.layer_name_dict = {}
        self.layer_actions_dict = {}
        menu = QMenu(self.iface.mainWindow())

        self.services = []
        for name, service_list in self.data.items():
            action = QAction(name, self.iface.mainWindow())
            action.setCheckable(True)
            action.triggered.connect(lambda checked, item=action: self.action_clicked(item))
            service, group_name = service_list
            self.layer_name_dict[action] = name
            self.services.append(orto_action_service.OrtoActionService(action, service, name))
            menu.addAction(action)
            menu.aboutToShow.connect(self.ortocheck)

        for group_name in self.get_group_names():
            group = orto_action_service.root.findGroup(group_name)
            if group:
                for lr in group.findLayers():
                    layer = lr.layer()
                    if not layer:
                        continue
                    layers_names.append(layer.name())
                    action = QAction(layer.name(), self.iface.mainWindow())
                    action.setCheckable(True)
                    action.triggered.connect(lambda checked, item=action: self.action_clicked(item))
                    if layer.name() not in self.layer_name_dict.values():
                        if layer.name() in self.data.keys():
                            self.layer_name_dict[action] = layer.name()
                            self.layer_actions_dict[layer] = action
        values = list(self.layer_actions_dict.values())
        values.sort(key=lambda x: x.text())
        list(map(menu.addAction, values))

        menu.addSeparator()

        setts = QAction(tr('LIST SETTINGS'), self.iface.mainWindow())
        setts.triggered.connect(self.setts)
        menu.addAction(setts)
        if but not in [None, NULL]:
            but.setMenu(menu)
        else:
            self.button.setMenu(menu)
        self.ortomenu = menu

    def setts(self):
        self.configure_wms = WMS_WMTS.WMS_WMTS(self)
        self.configure_wms.run()

    def ortocheck(self) -> None:
        for orto in self.ortomenu.actions():
            if orto.text() not in ['', 'USTAWIENIA LISTY', 'LIST SETTINGS']:
                source, group_name = self.return_orto_data(orto)
                orto_layers = orto_action_service.project.mapLayersByName(orto.text())
                group = orto_action_service.root.findGroup(orto.text())
                orto.setChecked(False)
                if orto_layers:
                    for layer in orto_layers:
                        if orto_action_service.root.findLayer(layer).isVisible() and orto_action_service.root.findLayer(layer).parent().name() == group_name \
                                and layer.source() == source:
                            orto.setChecked(True)
                            break
                if group and group.parent().name() == group_name:
                    orto.setChecked(True)

    def return_orto_data(self, orto):
        source = self.data[orto.text()][0]
        group_name = self.data[orto.text()][1]
        if check_if_value_empty(group_name):
            group_name = orto_action_service.temp_group_name
        return source, group_name

    def remove_wms_wmts_temp_group(self):
        group_names = list(self.get_group_names())
        group_names.append(orto_action_service.temp_group_name)
        groups = []
        for group_name in group_names:
            if orto_action_service.root.findGroup(group_name):
                groups.append(orto_action_service.root.findGroup(group_name))
        if not groups:
            return
        self.layers_list = []
        for group in groups:
            self.get_recursive_layer(group)
        for ll in self.layers_list:
            if ll.layer().dataProvider().name() in ['WFS', 'wms']:
                orto_action_service.project.removeMapLayer(ll.layer())

    def get_recursive_layer(self, group):
            for child in group.children():
                if isinstance(child, QgsLayerTreeGroup):
                    self.get_recursive_layer(child)
                if isinstance(child, QgsLayerTreeLayer):
                    self.layers_list.append(child)


