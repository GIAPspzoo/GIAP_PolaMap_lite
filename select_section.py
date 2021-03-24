import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from .utils import STANDARD_TOOLS

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_section_dialog.ui'))


class SelectSection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(SelectSection, self).__init__(parent)
        self.setupUi(self)

        tools = [x['label'] for x in STANDARD_TOOLS]
        self.toolList.addItems(tools)
