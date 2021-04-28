# -*- coding: utf-8 -*-

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from ..utils import tr

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dodaj_kompozycje.ui'))


class DodajKompozycjeDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(DodajKompozycjeDialog, self).__init__(parent)
        self.setupUi(self)

        self.groupBox_35.setTitle(tr("User Compositions"))
        self.dodaj_kompozycje.show()
        self.usun_kompozycje.show()
        self.wczytaj.show()
        self.zapisz.show()
