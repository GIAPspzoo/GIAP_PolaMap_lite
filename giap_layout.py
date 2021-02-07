# -*- coding: utf-8 -*-
import qgis
from PIL import Image
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QSize, \
    Qt, QRect, QPropertyAnimation, QEasingCurve
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QAction, QToolBar, QToolButton, QWidget, \
    QHBoxLayout, QStyleFactory, QDockWidget, QMenu

# Initialize Qt resources from file resources.py
from qgis._core import QgsProject

from .QuickPrint import PrintMapTool
from .utils import OBJECT_ACTION_DICT
from .resources import *
# Import the code for the dialog
from .giap_layout_dialog import MainTabQgsWidgetDialog
import os.path
project = QgsProject.instance()
class MainTabQgsWidget:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        self.main_widget = MainTabQgsWidgetDialog()

    def initGui(self):
        style = self.main_widget.styleSheet()
        self.iface.mainWindow().statusBar().setStyleSheet(style + """
        QSpinBox {
            height: 25px;
        }
        """)
        self.iface.mainWindow().menuBar().hide()
        for child in self.iface.mainWindow().children():
            if type(child) == QToolBar:
                child.hide()
            #   Zaawansowana digitalizacja
            if child.objectName() == 'mSnappingToolBar':
                for child2 in child.children():
                    if isinstance(child2, QToolButton) and \
                            child2.defaultAction() and \
                            child2.defaultAction().objectName() == 'EnableTracingAction':
                        self.main_widget.btn_dig_2.setDefaultAction(child2.defaultAction())
                        child2.defaultAction().menu().setStyleSheet(style + """
                                QMenu {
                                    background-color: rgb(53, 85, 109);
                                    color: rgb(255, 255, 255);
                                    font: 10pt "Segoe UI";
                                }
                                """)

            for dlg_object, standard_tool in OBJECT_ACTION_DICT.items():
                if child.objectName() == standard_tool:
                    self.main_widget.__getattribute__(dlg_object).setDefaultAction(child)


            if child.objectName() == 'Layers':
                child.hide()

        self.toolbar = QToolBar('GiapToolBar', self.iface.mainWindow())
        self.toolbar.setObjectName('GiapToolBar')
        self.iface.mainWindow().addToolBar(self.toolbar)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.addWidget(self.main_widget)
        self.ustaw_legende(style)
        self.menuButton = QToolButton()
        self.menuButton.setText("Pokaż menu")
        self.menuButton.setCheckable(True)
        self.menuButton.setBaseSize(QSize(80, 25))
        self.menuButton.toggled.connect(self.menu_show)
        corner_widget = QWidget(self.main_widget)
        corner_layout = QHBoxLayout()
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.addWidget(self.menuButton)

        corner_widget.setLayout(corner_layout)
        self.main_widget.tabWidget.setCornerWidget(corner_widget)
        self.iface.mapCanvas().refresh()

        self.quick_print = PrintMapTool(self.iface, self.main_widget)
        self.main_widget.btn_szybki_wydruk.clicked.connect(
            self.quick_print.run)
        self.main_widget.btn_szybki_wydruk.setToolTip(
            "Szybki wydruk widoku mapy")
        self.my_prints_setup()
        self.main_widget.btn_dig_18.actions()[0].setIcon(QIcon(f'{self.plugin_dir}/icons/magnet_tool.png'))
        self.main_widget.btn_moje_wydruki.setIcon(QIcon(f'{self.plugin_dir}/icons/my_prints.png'))
        self.main_widget.btn_szybki_wydruk.setIcon(QIcon(f'{self.plugin_dir}/icons/quick_print.png'))
        self.project_path = os.path.dirname(os.path.abspath(project.fileName()))

        self.toolbar.show()

    def my_prints_setup(self):
        btn = self.main_widget.btn_moje_wydruki
        btn.setToolTip("Moje wydruki")
        btn.setPopupMode(QToolButton.InstantPopup)
        self.action_my_prints_menu()
        self.projectLayoutManager.layoutAdded.connect(self.action_my_prints_menu)
        self.projectLayoutManager.layoutRemoved.connect(self.action_my_prints_menu)

    def action_my_prints_menu(self):
        if 'giap_layout' in qgis.utils.plugins:
            qgis.utils.plugins['giap_layout'].unload()
        main_widget = self.main_widget
        btn = main_widget.btn_moje_wydruki
        menu = QMenu(main_widget)
        actions = []
        projectInstance = QgsProject.instance()
        self.projectLayoutManager = projectInstance.layoutManager()
        for layout in self.projectLayoutManager.layouts():
            title = layout.name()
            action = QAction(title, main_widget)
            action.triggered.connect(lambda checked, item=action: self.open_layout_by_name(item.text()))
            actions.append(action)
        actions.sort(key=lambda x: x.text())
        list(map(menu.addAction, actions))
        btn.setMenu(menu)

    def open_layout_by_name(self, action_name):
        layout = self.projectLayoutManager.layoutByName(action_name)
        self.iface.openLayoutDesigner(layout)

    def unload(self):
        for child in self.iface.mainWindow().children():
            if type(child) == QToolBar and child.objectName() == 'GiapToolBar':
                child.hide()

    def menu_show(self):
        if self.menuButton.isChecked():
            self.iface.mainWindow().menuBar().show()
        else:
            self.iface.mainWindow().menuBar().hide()

    def ustaw_legende(self, style):
        qt_style = QStyleFactory.create('Cleanlooks')
        self.layer_panel = self.iface.mainWindow().findChildren(QDockWidget, 'Layers')[0]
        self.layer_panel.setTitleBarWidget(QWidget())
        self.layer_panel.setStyle(qt_style)
        self.layer_panel.setStyleSheet(style + """
        QToolBar {
            spacing: 7px;
            margin: 7px;
            border: none;
        }
        QToolButton  {
            padding: 3px 3px 3px 3px;
        }
        QMenu {
            background-color: rgb(53, 85, 109);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
        }
        QMenu::item:disabled {
            color: rgb(200, 200, 200);
        }
        * {
            background-color: rgb(53, 85, 109);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
        }
        """)
        self.layer_view = self.iface.layerTreeView()
        self.layer_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.layer_view.setStyle(qt_style)
        self.layer_view.setStyleSheet(style + """
        QTreeView::item, QTreeView::branch {
            color: rgb(255, 255, 255);
        }
        QTreeView {
            border: 2px solid;
            border-top-color: rgb(79, 118, 150);
            border-left: none;
            border-bottom-color: rgb(79, 118, 150);
            border-right: none;
            padding-top: 5px;
        }
        * {
            background-color: rgb(53, 85, 109);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
        }
        """)
        layer_toolbar = self.layer_view.parent().children()[1]
        layer_toolbar.children()[6].menu().setStyleSheet(style + """
        QMenu {
            background-color: rgb(53, 85, 109);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
        }
        QMenu::item:disabled {
            color: rgb(200, 200, 200);
        }
        """)
        layer_toolbar.children()[9].setPopupMode(2)
        self.main_widget.pokaz_warstwy.toggled.connect(self.warstwy_show)
        self.main_widget.pokaz_warstwy.toggle()

    def warstwy_show(self):
        splitter_start = QRect(-self.layer_panel.width(), self.layer_panel.y(),
                               self.layer_panel.width(), self.layer_panel.height())
        splitter_end = QRect(0, self.layer_panel.y(),
                             self.layer_panel.width(), self.layer_panel.height())
        if self.main_widget.pokaz_warstwy.isChecked():
            self.layer_panel.show()
            self.set_animation(self.layer_panel, splitter_start, splitter_end, 200)
            self.layer_view.resizeColumnToContents(0)
        else:
            self.set_animation(self.layer_panel, splitter_end, splitter_start, 200, 'out')

    def set_animation(self, widget, qrect_start, qrect_end, duration, mode='in'):
        animation_in = QPropertyAnimation(widget, b"geometry")
        animation_in.setStartValue(qrect_start)
        animation_in.setEndValue(qrect_end)
        animation_in.setDuration(duration)
        animation_in.setEasingCurve(QEasingCurve.InOutQuad)
        animation_in.start()
        animation_in.finished.connect(lambda: self.delete_animation(animation_in, widget, mode))

    def delete_animation(self, animation, widget, mode):
        del animation
        if mode == 'out':
            widget.hide()