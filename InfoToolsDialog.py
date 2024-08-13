# -*- coding: utf-8 -*-
import os

from PyQt5.QtWidgets import QMenu
from qgis.PyQt import QtWidgets, uic, QtCore


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'karta_informacjna_dialog.ui'))


class InfoToolsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent : QtWidgets=None) -> None:
        """Constructor."""
        super(InfoToolsDialog, self).__init__(parent)
        self.setupUi(self)

        self.menu = QMenu(self)

        self.identify_feature = self.menu.addAction("Identify Feature(s)")

        self.selectObjectPushButton.setMenu(self.menu)
        # self.menu.addAction("Identify Feature(s) on Mouse Over")
        # self.selectObjectPushButton.setMenu(self.menu)
        #
        # self.menu.addAction("Identify Features by Polygon")
        # self.selectObjectPushButton.setMenu(self.menu)
        #
        # self.menu.addAction("Identify Features Freehand ")
        # self.selectObjectPushButton.setMenu(self.menu)
        #
        # self.menu.addAction("Identify Features by Radius")
        # self.selectObjectPushButton.setMenu(self.menu)
