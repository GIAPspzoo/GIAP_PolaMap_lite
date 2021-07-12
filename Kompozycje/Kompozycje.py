# -*- coding: utf-8 -*-

import os
from collections import OrderedDict
from time import sleep

import uuid

from PyQt5.QtCore import QObject, pyqtSignal, QItemSelectionModel, \
    Qt
from PyQt5.QtWidgets import QMessageBox, QApplication, QItemDelegate, \
    QCheckBox, QFileDialog, QProgressDialog, QToolButton
from qgis.PyQt import QtCore

from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon
from qgis.core import QgsProject, QgsLayerTreeNode

from .CompositionsSaverDialog import CompositionsSaverDialog
from .dodajKompozycje import DodajKompozycjeDialog
from .nowa_kompozycja import NowaKompozycjaDialog
from ..CustomMessageBox import CustomMessageBox

from ..utils import get_project_config, SingletonModel,\
    set_project_config, identify_layer_by_id, ConfigSaveProgressDialog

from .CompositionsLib import (
    LayersPanel as lsp,
    connect_nodes,
    disconnect_nodes,
    get_all_groups_layers,
    get_groups,
    get_map_layer,
    get_qgs_layer_tree_node_name)
from . import UserCompositions
from . import DefaultCompositions

from ..utils import tr

LayersPanel = lsp

CODING_TYPE = 'utf-8'

CONFIG_SEPARATOR = '::&*&::'
CONFIG_LINES_SEPARATOR = ';;@@\n@@;;'

FILE_CONFIG_EXTENSION = '.giapconfig'
USER_COMPOSITIONS_EXTENSION = '.giapcomp'

# COMPOSITIONS_SCOPE = "Kompozycje"


def write_user_compositions(comp, filename):
    text = comp
    with open(filename, 'wb') as f:
        f.write(text.encode(CODING_TYPE))


def write_user_compositions_gui(comp_list):
    save_path = get_project_config('Sciezka', 'sciezka_do_zapisu', '')
    filename, __ = QFileDialog.getSaveFileName(
        None,
        tr("Save as"),
        save_path,
        f'*{USER_COMPOSITIONS_EXTENSION}'
    )
    if filename:
        progress = ProgressDialog(None, tr('Saving...'))
        progress.start()
        new_dirname = os.path.dirname(save_path)
        QApplication.processEvents()
        set_project_config('Sciezka', 'sciezka_do_zapisu', new_dirname)
        QApplication.processEvents()
        if not filename.endswith(USER_COMPOSITIONS_EXTENSION):
            filename += USER_COMPOSITIONS_EXTENSION
        write_user_compositions(comp_list, filename)
        QApplication.processEvents()
        progress.stop()
        CustomMessageBox(None, tr('Saved: ')+filename).button_ok()


def get_user_compositions(filename):
    with open(filename, 'rb') as f:
        text = f.read().decode(CODING_TYPE)
        comp_dict = eval(str(text))
    return comp_dict


def get_user_compositions_gui():
    save_path = get_project_config('Sciezka', 'sciezka_do_zapisu', '')
    filename, __ = QFileDialog.getOpenFileName(
        None,
        tr("Open"),
        save_path,
        f'*{USER_COMPOSITIONS_EXTENSION}'
    )
    user_comp = {}
    if filename:
        progress = ProgressDialog(None, tr("Loading"))
        progress.start()
        new_dirname = os.path.dirname(save_path)
        QApplication.processEvents()
        set_project_config('Sciezka', 'sciezka_do_zapisu', new_dirname)
        QApplication.processEvents()
        try:
            QApplication.processEvents()
            user_comp = get_user_compositions(filename)
        except Exception:
            CustomMessageBox(None, tr('Loading settings failed')).button_ok()
        progress.stop()
    return user_comp


class CompositionsTool(object):
    def __init__(self, iface, parent=None):
        self.canvas = iface.mapCanvas()
        self.dock = parent.main_widget
        self.widget = parent.kompozycje_widget
        self.modify_tool = None
        self.domyslne_kompozycje = dict()
        self.stworzone_kompozycje = dict()
        self.combo_box = None
        self.update_buttons()

    def update_buttons(self):
        # self.dock.toolButton_compositions.clicked.connect(self.config)
        ctools = self.dock.findChildren(QToolButton, 'giapCompositions')
        # we need only one signal
        for button in ctools:
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(self.config)

    def start(self):
        prjpath = QgsProject.instance().fileName()
        if self.modify_tool:
            del self.modify_tool
        self.modify_tool = CompositionsConfig(self)
        self.domyslne_kompozycje = DefaultCompositions.get_compositions()
        self.stworzone_kompozycje = UserCompositions.get_compositions()
        self.modify_tool.check_comps_schema(
            self.domyslne_kompozycje, tr('default'))
        self.modify_tool.check_comps_schema(
            self.stworzone_kompozycje, tr('custom'))

        self.combo_box = CompositionsComboBox(self)
        connect_nodes(QgsProject.instance().layerTreeRoot())

        self.modify_tool.compositionsSaved.connect(
            self.combo_box.fill_with_kompozycje)

    def config(self):
        """
        Metoda służąca do otworzenia okna ustawian kompozycji.
        """
        self.start()
        self.modify_tool.run()

    def unload(self):
        disconnect_nodes(QgsProject.instance().layerTreeRoot())
        if hasattr(self, 'combo_box') and self.combo_box:
            self.combo_box.unload()


class CompositionsConfig(QObject):
    compositionsSaved = pyqtSignal([])

    def __init__(self, parent):
        QObject.__init__(self)
        self.kompozycje = parent
        self.dodawanie = CompositionsAdder(parent)
        self.edycja = CompositionsEditor(parent, self)
        self.usuwanie = CompositionsDeleter(parent, self)
        self.model_kompozycji = QStandardItemModel()
        self.order_changed = False

    def save_to_project_file(self):
        self.save(False)
        QgsProject.instance().write()

    def check_for_changes_in_comps(self):
        def_comps_changed = self.check_update_comps(self.kompozycje.domyslne_kompozycje)
        usr_comps_changed = self.check_update_comps(self.kompozycje.stworzone_kompozycje)
        all_comp_changed = self.check_all_layers_comp()
        if any((def_comps_changed, usr_comps_changed, all_comp_changed)):
            CustomMessageBox(
                self.kompozycje.dock,
                tr('Changes in layer\'s panel detected\n'
                   'Compositions will be updated.')
                   ).button_ok()
            self.save_to_project_file()

    def create_table_model(self):
        self.model_kompozycji.clear()
        self.load_compositions(self.kompozycje.stworzone_kompozycje)
        self.order_changed = False

    def run(self):
        self.dlg = DodajKompozycjeDialog()

        # self.dlg.radioButton_1.clicked.connect(self.create_table_model)
        self.dlg.dodaj_kompozycje.clicked.connect(self.dodaj)
        self.dlg.edytuj_kompozycje.clicked.connect(self.edytuj)
        self.dlg.usun_kompozycje.clicked.connect(self.usun)
        self.dlg.zapisz.clicked.connect(self.write_file)
        self.dlg.wczytaj.clicked.connect(self.read_file)
        self.dlg.komp_dol.clicked.connect(self.move_comp_down)
        self.dlg.komp_gora.clicked.connect(self.move_comp_up)
        self.model_kompozycji.rowsInserted.connect(self.comps_order_change)

        self.check_for_changes_in_comps()
        self.create_table_model()
        if not self.dlg.isActiveWindow():
            self.dlg.show()
            dialog = self.dlg.exec_()
            if dialog:
                self.save()

    def write_file(self):
        saver = CompositionsSaver(self.kompozycje.stworzone_kompozycje)
        saver.run()
        self.dlg.activateWindow()
        self.dlg.showNormal()

    def read_file(self):
        suffix = '_wczytana'
        new_comps_dict = get_user_compositions_gui()
        no_current_comps = self.model_kompozycji.rowCount()
        for comp_name, value in list(new_comps_dict.items()):
            while comp_name in self.kompozycje.stworzone_kompozycje:
                comp_name += suffix
            self.kompozycje.stworzone_kompozycje[comp_name] = value
            self.kompozycje.stworzone_kompozycje[comp_name]['order'] += no_current_comps
        self.create_table_model()
        self.dlg.activateWindow()
        self.dlg.showNormal()

    def save(self, new_order=True):
        if new_order: # and self.dlg.radioButton_1.isChecked():
            for row in range(self.model_kompozycji.rowCount()):
                comp_name = self.model_kompozycji.item(row, 0).data(0)
                self.kompozycje.stworzone_kompozycje[comp_name]['order'] = row
        set_project_config('Kompozycje', 'stworzone_kompozycje',
                           str(self.kompozycje.stworzone_kompozycje))
        set_project_config('Kompozycje', 'domyslne_kompozycje',
                           str(self.kompozycje.domyslne_kompozycje))
        if new_order:
            self.compositionsSaved.emit()
            ConfigSaveProgressDialog(self.dlg).show()
            self.order_changed = False

    def dodaj(self):
        self.check_comps_order()
        order_no = self.dlg.tableView.model().rowCount()
        self.dodawanie.run_comp_adder(order_no)
        self.create_table_model()

    def edytuj(self):
        self.check_comps_order()
        self.edycja.run_comp_editor()
        self.create_table_model()

    def usun(self):
        self.check_comps_order()
        comp_deleted = self.usuwanie.run_comp_deleter()
        if comp_deleted:
            self.create_table_model()
            self.order_changed = True

    def load_compositions(self, compositions):
        sorted_comps = sorted(list(compositions.items()),
                              key=lambda x: x[1]['order'])
        sorted_comps_names = [y[0] for y in sorted_comps]
        for comp_name in sorted_comps_names:
            item = QStandardItem(str(comp_name))
            item.setEditable(False)
            self.model_kompozycji.appendRow(item)
        # self.model_kompozycji.setHorizontalHeaderLabels([tr("Compositions")])
        self.dlg.tableView.setModel(self.model_kompozycji)
        self.dlg.tableView.horizontalHeader().hide()
        self.dlg.tableView.verticalHeader().hide()

    def move_comp_up(self):
        table_sel_model = self.dlg.tableView.selectionModel()
        rows = table_sel_model.selectedRows()
        if rows:
            index = rows[0].row()
            if index > 0:
                taken_row = self.model_kompozycji.takeRow(index)
                self.model_kompozycji.insertRow(index - 1, taken_row)
                self.dlg.tableView.selectionModel().clear()
                self.dlg.tableView.selectionModel().select(self.dlg.tableView.model().index(index - 1, 0),
                                                           QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def move_comp_down(self):
        table_sel_model = self.dlg.tableView.selectionModel()
        rows = table_sel_model.selectedRows()
        if rows:
            index = rows[0].row()
            if index < self.dlg.tableView.model().rowCount() - 1:
                taken_row = self.model_kompozycji.takeRow(index)
                self.model_kompozycji.insertRow(index + 1, taken_row)
                self.dlg.tableView.selectionModel().clear()
                self.dlg.tableView.selectionModel().select(self.dlg.tableView.model().index(index + 1, 0),
                                                           QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def comps_order_change(self):
        self.order_changed = True

    def check_comps_order(self):
        if self.order_changed:
            stoper = CustomMessageBox(self.dlg,
                tr('The order of the compositions has not been saved! Do you want to save it?')).button_yes_no()
            if stoper == QMessageBox.Yes:
                self.save()

    def check_comps_schema(self, compositions, comp_type):
        for comp_name, comp_val in list(compositions.items()):
            if not isinstance(comp_val, dict):
                if self.update_comps_schema(compositions):
                    CustomMessageBox(
                        self.kompozycje.dock,
                        tr('Some layers from composition are missing, '
                           ' check composition') + f' {comp_type}'
                        ).button_ok()
                self.save_to_project_file()
                break
            else:
                return

    def update_comps_schema(self, compositions):
        new_compositions = dict()
        layers_not_found = False
        for order, (comp_name, comp_val) in enumerate(compositions.items()):
            all_layers_list = []
            for comp_tuple in comp_val:
                layer_group = comp_tuple[0]
                layer_name = comp_tuple[1]
                layer_list = [layer_group, layer_name]
                checked = comp_tuple[2]
                layer_list.append(checked)
                map_layer, layer_group, layer_name = get_map_layer(layer_group, layer_name)
                if map_layer:
                    layer_list.insert(2, map_layer.id())
                    all_layers_list.append(tuple(layer_list))
                else:
                    layers_not_found = True

            composition_params = dict()
            composition_params['id'] = str(uuid.uuid4())
            composition_params['order'] = order
            composition_params['layers'] = all_layers_list

            new_compositions[comp_name] = composition_params
        if compositions == self.kompozycje.domyslne_kompozycje:
            self.kompozycje.domyslne_kompozycje = new_compositions
        else:
            self.kompozycje.stworzone_kompozycje = new_compositions
        return layers_not_found

    def check_update_comps(self, compositions):
        new_compositions = dict()
        layertree_changed = False
        for comp_name, comp_val in list(compositions.items()):
            all_layers_list = []
            for layer_tuple in comp_val['layers']:
                layer_group = layer_tuple[0]
                layer_name = layer_tuple[1]
                layerid = layer_tuple[2]
                checked = layer_tuple[3]
                map_layer, layer_group, layer_name = get_map_layer(layer_group, layer_name)
                if map_layer:
                    layerid = map_layer.id() if map_layer.id() != layer_tuple[2] else layer_tuple[2]
                else:
                    map_layer = identify_layer_by_id(layerid)
                    if map_layer:
                        layer_group = get_groups(layerid)
                        layer_name = map_layer.name()
                    else:
                        layerid = None
                if layerid:
                    layer_list = [layer_group, layer_name, layerid, checked]
                    all_layers_list.append(tuple(layer_list))

            composition_params = dict()
            composition_params['id'] = comp_val['id']
            composition_params['order'] = comp_val['order']
            composition_params['layers'] = all_layers_list
            new_compositions[comp_name] = composition_params

            if sorted(all_layers_list) != sorted(comp_val['layers']):
                layertree_changed = True
        if layertree_changed:
            if compositions == self.kompozycje.domyslne_kompozycje:
                self.kompozycje.domyslne_kompozycje = new_compositions
            else:
                self.kompozycje.stworzone_kompozycje = new_compositions
        return layertree_changed

    def check_all_layers_comp(self):
        layertree_changed = False
        all_groups_layers = get_all_groups_layers()
        def_layers = [
            ':'.join([tup[0], tup[1]]) if tup[0] else tup[1] for tup in
            self.kompozycje.domyslne_kompozycje[tr('All layers')]['layers']
        ]
        if sorted(all_groups_layers) != sorted(def_layers):
            self.update_all_layers_comp(all_groups_layers)
            layertree_changed = True
        return layertree_changed

    def update_all_layers_comp(self, all_groups_layers):
        all_layers_list = []
        for group_layer in all_groups_layers:
            colon_index = group_layer.rfind(':')
            if colon_index == -1:
                layer_group = ''
            else:
                layer_group = group_layer[:colon_index]
            layer_name = group_layer[colon_index + 1:]
            layer_list = [layer_group, layer_name]
            map_layer, layer_group, layer_name = get_map_layer(layer_group, layer_name)
            layer_list.append(map_layer.id() if map_layer else '')

            layers = self.kompozycje.domyslne_kompozycje[tr('All layers')]['layers']
            checked_layers = [':'.join([tup[0], tup[1]]) for tup in filter(lambda x: x[3], layers)]
            checked = True if group_layer in checked_layers else False
            layer_list.append(checked)

            all_layers_list.append(tuple(layer_list))
        self.kompozycje.domyslne_kompozycje[tr('All layers')]['layers'] = all_layers_list


class CompositionsSaver(object):
    def __init__(self, comp_dict):
        self.comp_dict = comp_dict
        self.model = self.prepare_model()

    def prepare_model(self):
        new_model = QStandardItemModel()
        sorted_comps = sorted(self.comp_dict.items(), key=lambda x: x[1]['order'])
        sorted_comps_names = [y[0] for y in sorted_comps]
        for comp_name in sorted_comps_names:
            checkbox_item = QStandardItem(str(comp_name))
            checkbox_item.setEditable(False)
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(Qt.Checked)
            new_model.appendRow([checkbox_item])
        new_model.setHorizontalHeaderLabels([tr("Compositions")])
        return new_model

    def get_checked_compositions(self):
        table_model = self.dlg.tabela.model()
        comp_list = []
        if table_model:
            for row in range(table_model.rowCount()):
                item = table_model.item(row, 0)
                if item.checkState() == Qt.Checked:
                    comp_list.append(table_model.index(row, 0).data(0))
        checked_compositions = dict()
        for comp_name in comp_list:
            if comp_name in self.comp_dict:
                checked_compositions[comp_name] = self.comp_dict[comp_name]
        return checked_compositions

    def write(self):
        checked_compositions = self.get_checked_compositions()
        write_user_compositions_gui(str(checked_compositions))

    def run(self):
        self.dlg = CompositionsSaverDialog()
        self.dlg.tabela.setModel(self.model)
        self.dlg.tabela.horizontalHeader().hide()
        self.dlg.tabela.verticalHeader().hide()

        result = self.dlg.exec_()
        if result:
            self.write()


class CompositionsAdder(object):
    def __init__(self, parent):
        self.kompozycje = parent
        self.model_warstw = QStandardItemModel()  # model na wybrane warstwy do nowej kompozycji
        self.model_warstw.setHorizontalHeaderLabels([""])
        self.model_grup = QStandardItemModel()
        self.model_grup.setHorizontalHeaderLabels([""])
        self.model_grup_warstw = QStandardItemModel()
        self.model_grup_warstw.setHorizontalHeaderLabels([""])

    def run_comp_adder(self, order_no):
        self.model_warstw.clear()
        self.order_no = order_no
        self.root = QgsProject.instance().layerTreeRoot()
        if not len(self.root.children()):
            CustomMessageBox(
                self.kompozycje.dock, tr('No layers in project!')).button_ok()
            return
        self.dlg = NowaKompozycjaDialog()
        self.dlg.pushButton_2.clicked.connect(self.save)
        self.dlg.dodaj_warstwe.clicked.connect(self.add_layer)
        self.dlg.usun_warstwe.clicked.connect(self.del_layer)
        self.dlg.wdol_warstwe.clicked.connect(self.move_down)
        self.dlg.wgore_warstwe.clicked.connect(self.move_up)
        self.dlg.wdol_warstwe.hide()
        self.dlg.wgore_warstwe.hide()
        self.wczytaj_grupy()
        if not self.dlg.isActiveWindow():
            self.dlg.show()
            self.dlg.exec_()

    def save(self):
        comp_name = self.dlg.nazwa_lineEdit.text()
        if comp_name in list(self.kompozycje.stworzone_kompozycje.keys()) + \
                list(self.kompozycje.domyslne_kompozycje.keys()):
            CustomMessageBox(
                self.dlg,
                tr('Specified composition name already in use!')).button_ok()
            return
        if comp_name:
            composition_params = dict()
            composition_params['id'] = str(uuid.uuid4())
            composition_params['order'] = self.order_no
            composition_params['layers'] = self.get_all_comp_layers()
            self.kompozycje.stworzone_kompozycje[comp_name] = composition_params
            self.dlg.accept()
        else:
            CustomMessageBox(
                self.dlg, tr('Enter name for composition')).button_ok()

    def get_all_comp_layers(self):
        all_layers_list = []
        for row in range(self.model_warstw.rowCount()):
            item = self.model_warstw.item(row, 0)
            item_text = item.data(0)
            colon_index = item_text.rfind(':')
            if colon_index > 0:
                layer_group = item_text[:colon_index]
            else:
                layer_group = ''
            layer_name = item_text[colon_index + 1:]
            map_layer, layer_group, layer_name = get_map_layer(layer_group, layer_name)
            layer_list = [layer_group, layer_name]
            layer_list.append(map_layer.id() if map_layer else '')
            checked = True if item.checkState() == Qt.Checked else False
            layer_list.append(checked)

            all_layers_list.append(tuple(layer_list))
        return all_layers_list

    def wczytaj_grupy(self):
        self.model_grup.clear()
        self.groups_layers = OrderedDict()
        all_groups_layers = get_all_groups_layers()
        for group_layer in all_groups_layers:
            splitted_gp = group_layer.rsplit(':')
            layer = splitted_gp[-1]
            group = layer
            if len(splitted_gp) > 1:
                group = ':'.join(splitted_gp[:-1])
                if not self.root.findGroup(splitted_gp[-2]):
                    layer = ':'.join(splitted_gp[-2:])
                    group = ':'.join(splitted_gp[:-2]) \
                        if len(splitted_gp) > 2 else layer
            if group in self.groups_layers:
                self.groups_layers[group].append(layer)
                self.groups_layers[group].sort()
            else:
                self.groups_layers[group] = [layer]
        for key in list(self.groups_layers.keys()):
            item = QStandardItem(str(key))
            item.setEditable(False)
            self.model_grup.appendRow(item)

        self.dlg.grupy_table.setModel(self.model_grup)
        self.dlg.grupy_table.model().sort(0)
        self.dlg.grupy_table.selectionModel().selectionChanged.connect(self.wczytajWarstwy)

    def wczytajWarstwy(self):
        self.model_grup_warstw.clear()
        table = self.dlg.grupy_table
        model = table.selectionModel()
        rows = model.selectedRows()
        nazwa_grupy = rows[0].data(0)
        if nazwa_grupy in self.groups_layers:
            for layer_name in self.groups_layers[nazwa_grupy]:
                item = QStandardItem(str(layer_name))
                item.setEditable(False)
                self.model_grup_warstw.appendRow(item)

        self.dlg.warstwy_w_grupie_table.setModel(self.model_grup_warstw)
        self.dlg.warstwy_w_grupie_table.model().sort(0)

    def add_layer(self):
        group_rows = self.dlg.grupy_table.selectionModel().selectedRows()
        if group_rows:
            group_name = group_rows[0].data(0)
            layer_rows = self.dlg.warstwy_w_grupie_table.selectionModel().selectedRows()
            if layer_rows:
                for index_row in layer_rows:
                    layer_name = index_row.data(0)
                    if layer_name == group_name:  # jesli grupa i warstwa to to samo (czyli luzna warstwa wektorowa)
                        for root_group in self.root.children():
                            if get_qgs_layer_tree_node_name(root_group) == layer_name:
                                if root_group.nodeType() == QgsLayerTreeNode.NodeLayer:  # sprawdzamy czy jest to warstwa
                                    group_name = ""  # nazwe grupy ustawiamy na pusty string
                    group_layer_name = str(group_name + ":" + layer_name)
                    already_in_model = [self.model_warstw.item(x, 0).data(0) for x
                                        in range(self.model_warstw.rowCount())]
                    if group_layer_name not in already_in_model:
                        item = QStandardItem(group_layer_name)
                        item.setEditable(False)
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                        item.setCheckState(Qt.Checked)
                        self.model_warstw.appendRow(item)
                        self.dlg.warstwy_table.setModel(self.model_warstw)
                self.dlg.warstwy_table.model().sort(0)
            else:
                CustomMessageBox(
                    self.dlg,
                    tr('Choose layer, to add it to selected')
                ).button_ok()
        else:
            CustomMessageBox(
                self.dlg, tr('Select group, to choose layer.')
            ).button_ok()

    def del_layer(self):
        table_sel_model = self.dlg.warstwy_table.selectionModel()
        rows = table_sel_model.selectedRows()
        if not rows:
            CustomMessageBox(
                self.dlg, tr('Select layer, to remove it from selected.')
            ).button_ok()
        else:
            index_list = []
            for model_index in rows:
                index = QtCore.QPersistentModelIndex(model_index)
                index_list.append(index)

            for index in index_list:
                self.model_warstw.removeRow(index.row())
            self.dlg.warstwy_table.selectionModel().clear()

    def move_down(self):
        table_sel_model = self.dlg.warstwy_table.selectionModel()
        rows = table_sel_model.selectedRows()
        if rows:
            index = rows[0].row()
            if 0 <= index < self.dlg.warstwy_table.model().rowCount()-1:
                take = self.dlg.warstwy_table.model().takeRow(index)
                self.dlg.warstwy_table.model().insertRow(index + 1, take)
                self.dlg.warstwy_table.selectionModel().clear()
                self.dlg.warstwy_table.selectionModel().select(
                    self.dlg.warstwy_table.model().index(index + 1, 0),
                    QItemSelectionModel.Select)
        else:
            CustomMessageBox(
                self.dlg, tr('Choose composition, to change order')
            ).button_ok()

    def move_up(self):
        table_sel_model = self.dlg.warstwy_table.selectionModel()
        rows = table_sel_model.selectedRows()
        if rows:
            index = rows[0].row()
            if index:
                take = self.dlg.warstwy_table.model().takeRow(index)
                self.dlg.warstwy_table.model().insertRow(index - 1, take)
                self.dlg.warstwy_table.selectionModel().clear()
                self.dlg.warstwy_table.selectionModel().select(self.dlg.warstwy_table.model().index(index - 1, 0),
                                                               QItemSelectionModel.Select)
        else:
            CustomMessageBox(
                self.dlg, tr('Choose composition, to change order')
            ).button_ok()


class CompositionsEditor(CompositionsAdder):
    def __init__(self, parent, pokaz_kompozycje):
        CompositionsAdder.__init__(self, parent)
        self.pokaz_kompozycje = pokaz_kompozycje
        self.old_name = ""

    def run_comp_editor(self):
        self.model_warstw.clear()
        self.root = QgsProject.instance().layerTreeRoot()
        self.dlg = NowaKompozycjaDialog()
        self.dlg.title_label_3.setText(tr('Edit'))
        self.dlg.pushButton_2.clicked.connect(self.save)
        self.dlg.dodaj_warstwe.clicked.connect(self.add_layer)
        self.dlg.usun_warstwe.clicked.connect(self.del_layer)
        self.dlg.wdol_warstwe.clicked.connect(self.move_down)
        self.dlg.wgore_warstwe.clicked.connect(self.move_up)
        self.dlg.wdol_warstwe.hide()
        self.dlg.wgore_warstwe.hide()
        self.wczytaj_grupy()
        if self.ustaw_okno():
            if not self.dlg.isActiveWindow():
                self.dlg.show()
                self.dlg.exec_()

    def ustaw_okno(self):
        table = self.pokaz_kompozycje.dlg.tableView
        model = table.selectionModel()
        rows = model.selectedRows()
        if not rows:
            CustomMessageBox( table, tr('Select composition to edit')).button_ok()
            return False
        name = rows[0].data(0)
        domyslne_kompozycje = list(self.kompozycje.domyslne_kompozycje.keys())
        self.old_name = name
        self.dlg.nazwa_lineEdit.setText(name)
        all_groups_layers = get_all_groups_layers()
        if name in domyslne_kompozycje:  # zapisz jako dla domyslnych kompozycji
            self.czy_domyslna = True
            lista_warstw = self.kompozycje.domyslne_kompozycje[name]['layers']
            self.dlg.dodaj_warstwe.hide()
            self.dlg.usun_warstwe.hide()
            self.dlg.warstwy_w_grupie_table.hide()
            self.dlg.warstwy_w_grupie_label.hide()
            self.dlg.nazwa_lineEdit.setDisabled(True)
            self.dlg.grupy_table.hide()
            self.dlg.grupy_label.hide()
        else:
            self.czy_domyslna = False
            lista_warstw = self.kompozycje.stworzone_kompozycje[name]['layers']
        for warstwa in lista_warstw:
            item = QStandardItem(str(warstwa[0] + ":" + warstwa[1]))
            item.setEditable(False)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            if len(warstwa) > 2 and warstwa[3]:
                item.setCheckState(Qt.Checked)
            self.model_warstw.appendRow(item)
        if name in domyslne_kompozycje:
            to_remove_index = []
            if self.model_warstw.rowCount() != len(all_groups_layers):
                for grupa_warstw in all_groups_layers:
                    if not self.model_warstw.findItems(grupa_warstw):
                        item = QStandardItem(grupa_warstw)
                        item.setEditable(False)
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                        item.setCheckState(Qt.Unchecked)
                        self.model_warstw.appendRow(item)

                for index in range(0, self.model_warstw.rowCount()-1):
                    if not self.model_warstw.item(index).text() in all_groups_layers:
                        to_remove_index.append(index)

                to_remove_index.reverse()
                if to_remove_index:
                    for index in to_remove_index:
                        self.model_warstw.removeRow(index)

        self.dlg.warstwy_table.setModel(self.model_warstw)
        self.dlg.warstwy_table.model().sort(0)
        return True

    def save(self):
        name = self.dlg.nazwa_lineEdit.text()

        if name != self.old_name and (
                name in list(self.kompozycje.stworzone_kompozycje.keys())
                or name in list(self.kompozycje.domyslne_kompozycje.keys())
        ) and (not self.czy_domyslna):
            CustomMessageBox(
                self.dlg, tr('Specified composition name already in use!')
            ).button_ok()
            return

        if name:
            if self.czy_domyslna:
                self.kompozycje.domyslne_kompozycje[self.old_name]['layers'] = self.get_all_comp_layers()
                self.kompozycje.domyslne_kompozycje[name] = self.kompozycje.domyslne_kompozycje.pop(self.old_name)
            else:
                self.kompozycje.stworzone_kompozycje[self.old_name]['layers'] = self.get_all_comp_layers()
                self.kompozycje.stworzone_kompozycje[name] = self.kompozycje.stworzone_kompozycje.pop(self.old_name)
            self.dlg.accept()
        else:
            CustomMessageBox(self.dlg, tr('Enter composition name')).button_ok()


class CompositionsDeleter(object):
    def __init__(self, parent, pokaz_kompozycje):
        self.kompozycje = parent
        self.pokaz_kompozycje = pokaz_kompozycje

    def run_comp_deleter(self):
        table = self.pokaz_kompozycje.dlg.tableView
        model = table.selectionModel()
        rows = model.selectedRows()
        if not rows:
            CustomMessageBox(
                table, tr('Select composition to remove it')
            ).button_ok()
            return

        nazwa_kompozycji = rows[0].data(0)
        domyslne_kompozycje = list(self.kompozycje.domyslne_kompozycje.keys())
        if nazwa_kompozycji in domyslne_kompozycje:
            CustomMessageBox(
                table, tr('Selected composition is default!')).button_ok()
        else:
            stoper = CustomMessageBox(
                self.pokaz_kompozycje.dlg,
                tr('Selected composition will be deleted, proceed?')
            ).button_yes_no()
            if stoper == QMessageBox.Yes:
                comp_no_to_del = self.kompozycje.stworzone_kompozycje[nazwa_kompozycji]['order']
                for comp_attrs in list(self.kompozycje.stworzone_kompozycje.values()):
                    if comp_attrs['order'] > comp_no_to_del:
                        comp_attrs['order'] -= 1
                del self.kompozycje.stworzone_kompozycje[nazwa_kompozycji]
                return True
        return False


class CompositionsComboBox(object):
    def __init__(self, parent):
        self.cb = parent.widget.kompozycjeComboBox
        self.canvas = parent.canvas
        self.fill_with_kompozycje()
        self.cb.currentIndexChanged.connect(self.set_filter)

    def fill_with_kompozycje(self):
        c = DefaultCompositions.compositions_names()
        c.extend(UserCompositions.compositions_names())
        c.remove(tr('All layers'))
        c.insert(0, tr('All layers'))
        text = self.cb.currentText()
        self.cb.blockSignals(True)
        self.cb.clear()
        self.cb.addItems(c)
        if text:
            text_id = self.cb.findText(text)
            if text_id != -1:
                self.cb.setCurrentIndex(text_id)
        self.cb.blockSignals(False)
        self.set_filter()

    def set_filter(self):
        comp_name = self.cb.currentText()
        LayersPanel().runShow()
        LayersPanel().uncheckAllGroup()
        LayersPanel().uncheckAll()
        if comp_name in DefaultCompositions.compositions_names():
            DefaultCompositions.set_composition(comp_name)
        elif comp_name in UserCompositions.compositions_names():
            UserCompositions.set_composition(comp_name)
        QApplication.processEvents()
        QApplication.processEvents()
        self.canvas.refresh()

    def unload(self):
        self.cb.currentIndexChanged.disconnect(self.set_filter)
        self.cb.clear()


class CheckBoxDelegate(QItemDelegate):
    def __init__(self, parent):
        QItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        self.check_box = QCheckBox(self.parent())
        self.check_box.setChecked(True)
        if not self.parent().indexWidget(index):
            self.parent().setIndexWidget(index, self.check_box)


class ProgressDialog(QProgressDialog, SingletonModel):
    stylesheet = """
            * {
                background-color: rgb(53, 85, 109, 220);
                color: rgb(255, 255, 255);
                font: 10pt "Segoe UI";
            }
            """

    def __init__(self, parent=None, title='GIAP-Layout'):
        super(ProgressDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(':/plugins/giap_layout/icons/giap_logo.png'))
        self.setLabelText(tr('Please wait...'))
        self.setFixedWidth(300)
        self.setFixedHeight(100)
        self.setMaximum(100)
        self.setCancelButton(None)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.rejected.connect(self.stop)
        self.setWindowModality(Qt.WindowModal)

    def make_percent_step(self, step=100, new_text=None):
        if new_text:
            self.setLabelText(new_text)
            if "wczytywanie" in new_text:
                for pos in range(100 - self.value()):
                    sleep(0.0005)
                    self.setValue(self.value() + 1)
                return
        for pos in range(step):
            sleep(0.0005)
            self.setValue(self.value() + 1)
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def start_steped(self, title=tr('Loading\nPlease wait...')):
        self.setLabelText(title)
        self.setValue(1)
        self.show()
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def start(self):
        self.setFixedWidth(250)
        self.setMaximum(0)
        self.setCancelButton(None)
        self.show()
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def stop(self):
        self.setValue(100)
        self.close()
