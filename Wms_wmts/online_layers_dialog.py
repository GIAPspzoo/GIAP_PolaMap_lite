# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtCore import Qt
from ..utils import CustomMessageBox, tr, OtherProperSortFilterProxyModel

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'online_layers_dialog.ui'))


class OnlineLayersDialog(QDialog, FORM_CLASS):
    def __init__(self, input_list, checked_layers=[], parent=None):
        super(OnlineLayersDialog, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.input_list = input_list
        self.checked_list = []
        self.checked_layers = checked_layers
        self.setup_dialog()

    def setup_dialog(self) -> None:
        self.select_btn.clicked.connect(self.select_deselect)
        self.save_btn.clicked.connect(self.check_save)
        self.setup_listview()

    def check_save(self) -> None:
        self.checked_list = [
            self.base_model.item(row).text()
            for row in range(self.base_model.rowCount())
            if self.base_model.item(row).checkState() == Qt.Checked]
        if self.checked_list:
            self.accept()
        else:
            CustomMessageBox(self, tr('No layer left.')).button_ok()

    def select_deselect(self) -> None:
        if hasattr(self, 'select_state') and self.select_state:
            self.select_state = self.manage_rows(False)
        else:
            self.select_state = self.manage_rows()

    def setup_listview(self) -> None:
        self.base_model = QStandardItemModel()
        for elem in self.input_list.keys():
            item = QStandardItem(elem)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            if elem in self.checked_layers:
                item.setCheckState(Qt.Checked)
            self.base_model.appendRow(item)
        self.sort = OtherProperSortFilterProxyModel()
        self.sort.setSourceModel(self.base_model)
        self.sort.setDynamicSortFilter(True)
        self.sort.setFilterKeyColumn(-1)
        self.sort.sort(-1, Qt.AscendingOrder)
        self.layers_checklist.setModel(self.sort)
        self.lineEdit.textChanged.connect(
            lambda text: self.sort.setFilterFixedString(text))

    def manage_rows(self, state: bool = True) -> bool:
        for row in range(self.base_model.rowCount()):
            item = self.base_model.item(row)
            item.setCheckState(Qt.Checked if state else Qt.Unchecked)
        return state
