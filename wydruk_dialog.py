# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

from qgis.PyQt import QtWidgets, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wydruk_dialog.ui'))


class WydrukDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(WydrukDialog, self).__init__(parent)
        self.setupUi(self)
        self.progressBar.hide()
