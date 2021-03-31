# -*- coding: utf-8 -*-


import os
from qgis.PyQt import QtWidgets
from qgis.PyQt import uic
from PyQt5.QtCore import Qt

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__),
    'compositions_saver.ui'))


class CompositionsSaverDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CompositionsSaverDialog, self).__init__(parent)
        self.setupUi(self)

        self.zapisz.clicked.connect(self.accept)

        self.zaznacz.clicked.connect(self.check_choosen)
        self.odznacz.clicked.connect(self.uncheck_choosen)

        self.zaznacz_wszystkie.clicked.connect(self.check_all)
        self.odznacz_wszystkie.clicked.connect(self.uncheck_all)

    def check_all(self):
        table = self.tabela
        model = table.model()
        if model:
            for r in range(model.rowCount()):
                item = model.item(r, 0)
                item.setCheckState(Qt.Checked)

    def uncheck_all(self):
        table = self.tabela
        model = table.model()
        if model:
            for r in range(model.rowCount()):
                item = model.item(r, 0)
                item.setCheckState(Qt.Unchecked)

    def check_choosen(self):
        table = self.tabela
        model = table.model()
        selection_model = table.selectionModel()
        rows = selection_model.selectedRows()
        if rows:
            for row in rows:
                item = model.item(row.row(), 0)
                item.setCheckState(Qt.Checked)

    def uncheck_choosen(self):
        table = self.tabela
        model = table.model()
        selection_model = table.selectionModel()
        rows = selection_model.selectedRows()
        if rows:
            for row in rows:
                item = model.item(row.row(), 0)
                item.setCheckState(Qt.Unchecked)
