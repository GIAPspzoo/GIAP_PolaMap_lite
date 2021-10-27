# -*- coding: utf-8 -*-

from __future__ import absolute_import

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QToolButton, QMenu, QAction
from qgis.core import QgsProject, QgsRasterLayer, QgsMessageLog

from .utils import WMS_SERVERS, WMS_SERVERS_GROUPS
from .utils import tr, CustomMessageBox


class OrtoAddingTool(object):
    def __init__(self,
                 parent, button,
                 group_names=("WMS/WMTS")):
        self.parent = parent
        self.button = button
        self.group_names = group_names
        self.layer_actions_dict = {}

        self.button.setToolTip(tr("Add WMS/WMTS services"))
        self.button.setPopupMode(QToolButton.InstantPopup)
        self.name_service = WMS_SERVERS
        self.groups_for_names = WMS_SERVERS_GROUPS
        self.services = []
        self.create_menu()
        self.connect_ortofotomapa_group()

    def connect_ortofotomapa_group(self):
        """
        Łączy sygnał wywoływany podczas zmiany widoczności w grupie o nazwie
         self.group_name z funkcją self.create_menu.
        """
        for group_name in self.group_names:
            root = QgsProject.instance().layerTreeRoot()
            group = root.findGroup(group_name)
            if group:
                group.visibilityChanged.connect(self.create_menu)
                group.addedChildren.connect(self.create_menu)
                group.removedChildren.connect(self.create_menu)

    def disconnect_ortofotomapa_group(self):
        """
        Odłącza sygnał wywoływany podczas zmiany widoczności w grupie o nazwie
         self.group_name z funkcją self.create_menu.
        """
        for group_name in self.group_names:
            group = QgsProject.instance().layerTreeRoot().findGroup(
                group_name)
            if group:
                try:
                    group.visibilityChanged.disconnect(self.create_menu)
                    group.addedChildren.disconnect(self.create_menu)
                    group.removedChildren.disconnect(self.create_menu)
                except Exception:
                    QgsMessageLog.logMessage(
                        tr("Error, detaching signals from "
                           "groups in layers tree."
                           ),
                        tag="GIAP-PolaMap(lite)"
                    )

    def action_clicked(self, item):
        """
        Uaktualnia widoczność warstw na podstawie akcji z menu przycisku.
        """
        layer_name = self.layer_name_dict[item]
        if QgsProject.instance().mapLayersByName(layer_name):
            try:
                for layer, action in self.layer_actions_dict.items():
                    if QgsProject.instance().layerTreeRoot().findLayer(layer):
                        QgsProject.instance().layerTreeRoot().findLayer(
                            layer).parent().setItemVisibilityChecked(True)

                        checked = action.isChecked()
                        QgsProject.instance().layerTreeRoot().findLayer(
                            layer).setItemVisibilityChecked(checked)
            except RuntimeError:
                item.setChecked(True)
        self.add_to_map(layer_name)

    def add_to_map(self, name):
        url = self.name_service[name]
        rlayer = QgsRasterLayer(url, name, 'wms')
        if not QgsProject.instance().mapLayersByName(name):
            root = QgsProject.instance().layerTreeRoot()
            group_name = self.groups_for_names[name]
            if rlayer.isValid():
                group = root.findGroup(group_name)
                if not group:
                    root.addGroup(group_name)
                    group = root.findGroup(group_name)
                QgsProject.instance().addMapLayer(rlayer)
                node_layer = root.findLayer(rlayer.id())
                node_parent = node_layer.parent()
                clone_node_layer = node_layer.clone()
                group.insertChildNode(0, clone_node_layer)
                clone_node_layer.setItemVisibilityCheckedParentRecursive(True)
                node_parent.removeChildNode(node_layer)
            else:
                CustomMessageBox(
                    None, tr('Can\'t add layer') + name).button_ok()
        else:
            lyr = QgsProject.instance().mapLayersByName(name)[0]
            lyrontree = QgsProject.instance().layerTreeRoot().findLayer(
                lyr.id())
            lyrontree.setItemVisibilityChecked(
                not lyrontree.isItemVisibilityCheckedRecursive())

    def create_menu(self):
        layers_names = []
        self.layer_name_dict = {}
        self.layer_actions_dict = {}
        menu = QMenu(self.parent)
        for group_name in self.group_names:
            group = QgsProject.instance().layerTreeRoot().findGroup(group_name)
            if group:
                for lr in group.findLayers():
                    layer = lr.layer()
                    layers_names.append(layer.name())
                    action = QAction(layer.name(), self.parent)
                    action.setCheckable(True)
                    action.triggered.connect(
                        lambda checked, item=action: self.action_clicked(item))
                    self.layer_name_dict[action] = layer.name()
                    self.layer_actions_dict[layer] = action
        values = list(self.layer_actions_dict.values())
        values.sort(key=lambda x: x.text())
        list(map(menu.addAction, values))

        self.services = []
        for name, service in self.name_service.items():
            if name not in layers_names:
                action = QAction(name, self.parent)
                action.setCheckable(True)
                group_name = self.groups_for_names[name]
                self.layer_name_dict[action] = name
                self.services.append(
                    OrtoActionService(
                        action,
                        service,
                        name,
                        group_name,
                        parent=self
                    )
                )
                menu.addAction(action)
                menu.aboutToShow.connect(self.ortocheck)
        self.button.setMenu(menu)
        self.ortomenu = menu

    def ortocheck(self):
        checked = [layer.name() for layer in
                   QgsProject.instance().layerTreeRoot().checkedLayers()]
        for orto in self.ortomenu.actions():
            orto.setChecked(orto.text() in checked)


class OrtoActionService(QObject):
    orto_added = pyqtSignal()
    orto_group_added = pyqtSignal()

    def __init__(self, action, url, name,
                 default_group="WMS/WMTS", parent=None):
        QObject.__init__(self)
        self.parent = parent
        self.button = action
        self.url = url
        self.name = name
        self.group_name = default_group
        self.button.triggered.connect(
            lambda checked, item=self.button: self.parent.action_clicked(item))
