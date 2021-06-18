# -*- coding: utf-8 -*-

import os
from qgis.PyQt import QtWidgets, uic, QtCore, QtGui

from ..CustomMessageBox import CustomMessageBox
from ..utils import tr


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'nowa_kompozycja.ui'))


class NowaKompozycjaDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(NowaKompozycjaDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.Window)

        # żeby nie dało się upuszczać na elementach (inaczej "drop" zastępuje elementy na liście!)
        standard_item_flags = int(QtGui.QStandardItem().flags())
        self.new_flags = QtCore.Qt.ItemFlags(standard_item_flags - 8)

        self.checkPushButton.clicked.connect(self.check)
        self.uncheckPushButton.clicked.connect(self.uncheck)
        self.checkAllPushButton.clicked.connect(self.check_all)
        self.uncheckAllPushButton.clicked.connect(self.uncheck_all)

    def check(self):
        try:
            table = self.warstwy_table
            sel_model = table.selectionModel()
            model = table.model()
            rows = sel_model.selectedRows()
            for row in rows:
                item = model.itemFromIndex(row)
                item.setCheckState(QtCore.Qt.Checked)
            if not model.rowCount():
                raise AttributeError("No layers in 'selected layer'")
        except AttributeError:
            CustomMessageBox(table, tr('No layers in selected layer')).button_ok()

    def uncheck(self):
        try:
            table = self.warstwy_table
            sel_model = table.selectionModel()
            model = table.model()
            rows = sel_model.selectedRows()
            for row in rows:
                item = model.itemFromIndex(row)
                item.setCheckState(QtCore.Qt.Unchecked)
            if not model.rowCount():
                raise AttributeError("No layers in 'selected layer'")
        except AttributeError:
            CustomMessageBox(None, tr("No layers in selected layer")).button_ok()

    def check_all(self):
        try:
            table = self.warstwy_table
            model = table.model()
            for row in range(model.rowCount()):
                item = model.itemFromIndex(model.index(row, 0))
                item.setCheckState(QtCore.Qt.Checked)
            if not model.rowCount():
                raise AttributeError("No layers in 'selected layer'")
        except AttributeError:
            CustomMessageBox(None, tr("No layers in selected layer")).button_ok()

    def uncheck_all(self):
        try:
            table = self.warstwy_table
            model = table.model()
            for row in range(model.rowCount()):
                item = model.itemFromIndex(model.index(row, 0))
                item.setCheckState(QtCore.Qt.Unchecked)
            if not model.rowCount():
                raise AttributeError("No layers in 'selected layer'")
        except AttributeError:
            CustomMessageBox(None, tr("No layers in selected layer")).button_ok()
