import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QInputDialog, QMessageBox

from ..utils import DEFAULT_STYLE, tr, Qt

################################################################
from qgis.PyQt.QtCore import QSize
################################################################

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui_stylemanager.ui'))


class StyleManagerDialog(QDialog, FORM_CLASS):
    def __init__(self, style_mn):
        super(StyleManagerDialog, self).__init__()

        self.setupUi(self)
        self.setWindowFlag(Qt.Window)

        self.mn = style_mn

        self.listWidget.blockSignals(True)
        self.listWidget.addItems(self.mn.config.get_style_list())
        self.listWidget.blockSignals(False)

        # self.pushButton_add.clicked.connect(self.add_style)
        # self.pushButton_delete.clicked.connect(self.delete_style)
        
        self.pushButton_default.clicked.connect(self.set_default)
        self.pushButton_activate.clicked.connect(self.change_style)
        
        ########################################################################
        self.icon_size = 24
        
        # icon_size = 16  
        # self.pushButton_default.setIconSize(QSize(icon_size, icon_size))
        # self.pushButton_activate.setIconSize(QSize(icon_size, icon_size))

        # self.adjust_icon_sizes()
        ########################################################################

    def add_style(self):
        """ add new style"""
        filename, _ = QFileDialog.getOpenFileName(
            self, tr("Open qss"), '', "*.qss"
        )
        text, ok = QInputDialog.getText(
            self, tr('Style Name'), tr('Enter name for style:'),
        )

        if ok:
            if str(text) in ['', 'None', 'False']:
                msg = QMessageBox()
                msg.setText(tr('Not valid name, try again!'))
                msg.exec_()
                return
            self.mn.set_style(text, filename)
            self.listWidget.addItem(text)

    def delete_style(self):
        """ Delete selected style"""
        try:
            name = self.listWidget.selectedItems()[0].text()
        except Exception:
            return

        res = self.mn.remove_style(name)
        if res:
            self.listWidget.takeItem(self.listWidget.currentRow())

    def set_default(self):
        """Set default qgis style"""
        res, msg = self.mn.activate_style(DEFAULT_STYLE)

    def change_style(self):
        """Change style to user selected"""

        try:
            name = self.listWidget.currentItem().text()
        except Exception:
            return

        res, msg = self.mn.activate_style(name)
    
    ########################################################################
    def adjust_icon_sizes(self):
        self.pushButton_default.setIconSize(QSize(self.icon_size, self.icon_size))
        self.pushButton_activate.setIconSize(QSize(self.icon_size, self.icon_size))

    # def set_default(self):
    #     """Set default qgis style"""
    #     res, msg = self.mn.activate_style(DEFAULT_STYLE)
    #     if res:
    #         QMessageBox.information(self, tr("Set Default Style"), tr("Default style set successfully."))
    #     else:
    #         QMessageBox.warning(self, tr("Set Default Style"), tr("Failed to set default style: %s") % msg)

    # def change_style(self):
    #     """Change style to user selected"""
    #     try:
    #         name = self.listWidget.currentItem().text()
    #     except Exception:
    #         return
    #     res, msg = self.mn.activate_style(name)
    #     if res:
    #         QMessageBox.information(self, tr("Change Style"), tr("Style changed successfully."))
    #     else:
    #         QMessageBox.warning(self, tr("Change Style"), tr("Failed to change style: %s") % msg)
    ########################################################################

    def hide(self):
        """unload dialog"""
        self.hide()
