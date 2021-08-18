import os

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui_settings_layout.ui'))


class SettingsDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)

        if str(QSettings().value('locale/overrideFlag')) == "false":
            self.radioButton_sys.setChecked(True)
        else:
            if str(QSettings().value('locale/userLocale')) == "en":
                self.radioButton_en.setChecked(True)
            elif str(QSettings().value('locale/userLocale')) == "pl_PL":
                self.radioButton_pl.setChecked(True)



