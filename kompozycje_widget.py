# -*- coding: utf-8 -*-

import os

from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.uic import loadUiType

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'kompozycje_widget.ui'))


class kompozycjeWidget(QWidget, FORM_CLASS):
    districts_completers_dict = None

    def __init__(self, parent=None):
        super(kompozycjeWidget, self).__init__(parent)
        self.setupUi(self)
