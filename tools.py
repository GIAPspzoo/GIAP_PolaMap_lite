import os
import re

from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtCore import QFileSystemWatcher

from .utils import tr
from .utils import DEFAULT_STYLE


class StyleManager:
    def __init__(self, parent):
        self.app = QApplication.instance()

        self.config = parent.config
        # keep watch on file, there are applications that change or remove a
        # file
        self.watch = QFileSystemWatcher()
        self.watch.fileChanged.connect(self.reload_style)

        self.style_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'styles'
        ))

        # here add default styles, otherwise the will not be seen in qgis
        self.styles = {
            'GIAP Navy Blue': 'giap.qss',
            #'blueglass': 'blueglass.qss',
            #'coffee': 'coffee.qss',
            #'darkblue': 'darkblue.qss',
            #'darkorange': 'darkorange.qss',
            #'lightblue': 'lightblue.qss',
            'GIAP Dark': 'wombat.qss',
        }

    def get_style_list(self):
        return [x for x in self.styles.keys()]

    def get_style_dictionary(self):
        return self.styles

    def run_last_style(self):
        """ load active style on stratup"""
        try:
            last = self.config.get_active_style()
            if last not in [None, '', False]:
                last_pth = os.path.join(
                    self.style_dir, last, self.config.get_style_path(last)
                )
                self.reload_style(last_pth)
        except Exception:
            return

    def remove_style(self, name):
        """Remove style from qgis config"""
        if self.config.get_active_style() == name:
            self.config.set_active_style('')
            self.activate_style('')
        self.config.delete_style(name)

    def reload_style(self, path):
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

        # if path to style not found set default style
        if pth in ['', None]:
            self.app.setStyleSheet(DEFAULT_STYLE)
            pth = ''

        # check if file exist
        if not os.path.exists(pth):
            self.app.setStyleSheet(DEFAULT_STYLE)  # return do default, and save it in con
            if name == 'default':
                self.config.set_active_style(DEFAULT_STYLE)
                return False, tr('Default style set')
            else:
                return False, tr('Path to *.qss not found, load default style')

        self.reload_style(pth)
        self.config.set_active_style(name)
        return True, tr('Style activated!')
