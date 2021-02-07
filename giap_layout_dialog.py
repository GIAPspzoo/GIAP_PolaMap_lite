# -*- coding: utf-8 -*-

import os

from PyQt5.QtWidgets import QWidget
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'giap_layout_dialog_base.ui'))


class MainTabQgsWidgetDialog(QWidget, FORM_CLASS):

    def __init__(self, parent=None):
        super(MainTabQgsWidgetDialog, self).__init__(parent)
        self.setupUi(self)
