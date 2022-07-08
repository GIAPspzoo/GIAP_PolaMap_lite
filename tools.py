import os
import re

from qgis.PyQt.QtCore import QFileSystemWatcher
from qgis.PyQt.QtWidgets import QApplication

from .utils import DEFAULT_STYLE, tr
from .Settings.settings_layout import SettingsDialog
from qgis.utils import iface

class StyleManager:
    def __init__(self, parent):
        self.app = QApplication.instance()
        self.parent = parent
        self.main_widget = self.parent.main_widget
        self.status_bar = iface.statusBarIface()
        self.menu_bar = iface.mainWindow().menuBar()
        self.tab_bar = self.parent.tab_bar

        self.config = parent.config
        self.watch = QFileSystemWatcher()
        self.watch.fileChanged.connect(self.reload_style)

        self.style_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'styles'
        ))

        self.styles = {
            'GIAP Navy Blue': 'giap.qss',
            # 'blueglass': 'blueglass.qss',
            # 'coffee': 'coffee.qss',
            # 'darkblue': 'darkblue.qss',
            # 'darkorange': 'darkorange.qss',
            # 'lightblue': 'lightblue.qss',
            'GIAP Dark': 'wombat.qss',
        }

    def get_style_list(self):
        return [style for style in self.styles.keys()]

    def get_style_dictionary(self):
        return self.styles

    def run_last_style(self, value=None):
        """ load active style on stratup"""
        try:
            last = self.config.get_active_style()
            if last not in [None, '', False]:
                last_pth = os.path.join(
                    self.style_dir, last, self.config.get_style_path(last)
                )
                self.reload_style(last_pth, value)
        except Exception:
            return

    def remove_style(self, name):
        """Remove style from qgis config"""
        if self.config.get_active_style() == name:
            self.config.set_active_style('')
            self.activate_style('')
        self.config.delete_style(name)

    def reload_style(self, path, value=None):
        """ load style to qgis, and set watch on it to remain active
        :path: str  ( path to style)
        :return: bool, str
        """
        self.watch.removePaths(self.watch.files())
        self.watch.addPath(path)
        with open(path, "r") as f:
            stylesheet = f.read()
            # Update the image paths to use full paths.
            # Fixes image loading in styles
            path = os.path.dirname(path).replace("\\", "/")
            stylesheet = re.sub(r'url\((.*?)\)', r'url("{}/\1")'.format(path),
                                stylesheet)

            if value:
            #     self.main_widget.setStyleSheet(f'{stylesheet} \nQMenuBar,\
            #     QWidget, QToolTip, QMenu, QAbstractItemView, QTabBar,\
            #     QPushButton, QComboBox, QToolBar, QDockWidget, QLabel,\
            #     QToolButton, QTabWidget, QLineEdit, QGroupBox, QScrollBar,\
            #     QTabBar, QDialog, QHeaderView, QDateEdit, QListView, QTreeView,\
            #     QTableView, QTextEdit, QDialog, QPlainTextEdit, QToolBar QLabel,\
            #     QToolBar QToolButton, QDialog QLabel {{font: {value}pt;}}')
                self.status_bar.setStyleSheet(f'{stylesheet} \n\
                QWidget, QComboBox {{font: {value}pt;}}')
                self.menu_bar.setStyleSheet(f'{stylesheet} \nQMenuBar,\
                QMenu {{font: {value}pt;}}')
                self.app.setStyleSheet(f'{stylesheet} \n QTabBar, \
                QAbstractItemView {{font: {value}pt;}}')
                self.tab_bar.setStyleSheet(f'{stylesheet} \n\
                {{font: {value}pt;}}')


            else:
                self.app.setStyleSheet(stylesheet)
            self.app.processEvents()

    def activate_style(self, name):
        """activate selected style, or set default if problem occured
        :res: bool
        :name: str (message for user)
        """
        self.watch.removePaths(self.watch.files())
        pth = ''
        styles = self.config.get_style_list()
        if name in styles:
            pth = os.path.join(
                self.style_dir, name, self.config.get_style_path(name)
            )

        if pth in ['', None]:
            self.app.setStyleSheet(DEFAULT_STYLE)
            pth = ''

        if not os.path.exists(pth):
            self.app.setStyleSheet(DEFAULT_STYLE)
            if name == 'default':
                self.config.set_active_style(DEFAULT_STYLE)
                return False, tr('Default style set')
            else:
                return False, tr('Path to *.qss not found, load default style')

        self.reload_style(pth)
        self.config.set_active_style(name)
        return True, tr('Style activated!')
