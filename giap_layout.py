# -*- coding: utf-8 -*-
import os.path

from qgis.PyQt.QtCore import QTranslator, QCoreApplication, QSize, \
    Qt, QRect, QPropertyAnimation, QEasingCurve, QEvent
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar, QToolButton, QWidget, \
    QHBoxLayout, QDockWidget, QMenu, QVBoxLayout

# Initialize Qt resources from file resources.py
from qgis._core import QgsProject, Qgis

from .QuickPrint import PrintMapTool

from .Kompozycje.Kompozycje import CompositionsTool
from .kompozycje_widget import kompozycjeWidget
# from .resources import *
# Import the code for the dialog
# from .giap_layout_dialog import MainTabQgsWidgetDialog
from .config import Config
from .tools import StyleManager

from .StyleManager.stylemanager import StyleManagerDialog
from .OrtoTools import OrtoAddingTool

from .giap_dynamic_layout import Widget
from .ribbon_config import RIBBON_DEFAULT

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
        self.main_widget = Widget(self.iface.mainWindow())
        self.kompozycje_widget = kompozycjeWidget()

        # list with hidden left docs, to reinstitute on user click
        self.left_docks = []
        # setup config structure for maintainning, toolbar and user interface
        # customization
        self.config = Config()

        # initialize StyleManager for styling handling
        self.style_manager = StyleManager(self)

        self.iface.projectRead.connect(self.projekt_wczytany)

    def initGui(self):
        style = self.main_widget.styleSheet()
        self.iface.mainWindow().statusBar().setStyleSheet(style + """
        QSpinBox {
            height: 25px;
        }
        """)
        self.save_default_user_layout()
        self.style_manager.run_last_style()

        self.kompozycje = CompositionsTool(self.iface, self)

        # turn on ribbon editing
        self.main_widget.edit_session_toggle()

        ribbon_conf = self.config.load_user_ribbon_setup()
        if not ribbon_conf:
            ribbon_conf = RIBBON_DEFAULT

        for dtab in ribbon_conf:
            itab, tab = self.main_widget.add_tab(dtab['tab_name'])
            for dsec in dtab['sections']:
                sec = self.main_widget.add_section(
                    itab, dsec['label'], dsec['btn_size']
                )
                for btn in dsec['btns']:
                    child = self.iface.mainWindow().findChild(QAction, btn[0])
                    if child is None:
                        sec.add_action(*btn)
                    else:
                        sec.add_action(child, *btn[1:])

                if dsec['label'] == 'Prints':
                    self.custom_prints()

        self.setup_orto()
        self.main_widget.tabWidget.setCurrentIndex(0)
        # turn off ribbon editing
        self.main_widget.edit_session_toggle()

        self.toolbar = QToolBar('GiapToolBar', self.iface.mainWindow())
        self.toolbar.setObjectName('GiapToolBar')
        self.iface.mainWindow().addToolBar(self.toolbar)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.addWidget(self.main_widget)

        self.ustaw_legende()
        self.menuButton = QToolButton()
        self.menuButton.setText("Show menu")
        self.menuButton.setCheckable(True)
        self.menuButton.setBaseSize(QSize(80, 25))
        self.menuButton.toggled.connect(self.menu_show)

        self.editButton = QToolButton()
        self.editButton.setText("Edit menu")
        self.editButton.setCheckable(True)
        self.editButton.setBaseSize(QSize(25, 25))
        self.editButton.toggled.connect(self.main_widget.edit_session_toggle)
        self.menu_show()

        self.styleButton = QToolButton()
        self.styleButton.setText("Theme")
        self.styleButton.setBaseSize(QSize(25, 25))
        self.styleButton.clicked.connect(self.show_style_manager_dialog)
        self.styleButton.setObjectName('ThemeButton')

        corner_widget = QWidget(self.main_widget.tabWidget)
        corner_layout = QHBoxLayout()
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.addWidget(self.menuButton)
        corner_layout.addWidget(self.editButton)
        corner_layout.addWidget(self.styleButton)

        corner_widget.setLayout(corner_layout)
        self.main_widget.tabWidget.setCornerWidget(corner_widget)
        self.iface.mapCanvas().refresh()

        # signals
        self.main_widget.editChanged.connect(self.save_user_ribbon_config)
        self.main_widget.printsAdded.connect(self.custom_prints)

        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.toolbar.show()

        # set strong focus to get keypressevent
        self.main_widget.setFocusPolicy(Qt.StrongFocus)

    def custom_prints(self):
        """Load custom tools to qgis"""
        self.quick_print = PrintMapTool(self.iface, self.main_widget)

        b_qprints = self.main_widget.findChildren(
            QToolButton, 'giapQuickPrint')
        for b_qprint in b_qprints:
            b_qprint.clicked.connect(self.quick_print.run)
            b_qprint.setToolTip("Szybki wydruk widoku mapy")
            b_qprint.setIcon(QIcon(f'{self.plugin_dir}/icons/quick_print.png'))

        b_mprints = self.main_widget.findChildren(QToolButton, 'giapMyPrints')
        for b_mprint in b_mprints:
            b_mprint.setIcon(QIcon(f'{self.plugin_dir}/icons/my_prints.png'))

        self.my_prints_setup()

    def save_default_user_layout(self):
        """ Saves active user toolbars in qgis user settings. Saves as string
        under flag org_toolbars in json config file (user scope).
        Assumes that all toolbars have specified name if not, we can't find
        them, and therefore will not be loaded again
        :return:
        """
        # select all active toolbars from mainwindow
        active_toolbars = []
        for x in self.iface.mainWindow().findChildren(QToolBar):
            try:
                if x.parent().windowTitle() == \
                        self.iface.mainWindow().windowTitle() and \
                        x.isVisible():
                    active_toolbars.append(x)
            except Exception:
                pass

        # hide toolbars
        for x in active_toolbars:
            x.hide()

        # unique and not empty objects name from toolbars
        tbars_names = [
            x.objectName() for x in active_toolbars
            if x.objectName() not in ['', None, 'NULL', 'GiapToolBar']
        ]

        self.config.save_original_toolbars(tbars_names)

    def save_user_ribbon_config(self, opt):
        """Saves user ribbon setup to config on exit
        :opt: bool for edit session, False will save config
        :return: None
        """
        if not opt:
            conf = self.main_widget.generate_ribbon_config()
            self.config.save_user_ribbon_setup(conf)

    def load_default_user_layout(self):
        """Restores original user toolbars to qgis window from settings
        :return:
        """
        toolbars_name = self.config.get_original_toolbars()

        # find toolbars and swich their visiblity on
        for tname in toolbars_name:
            tbar = self.iface.mainWindow().findChild(QToolBar, tname)
            if tbar is not None:
                tbar.show()

        # show menu bar
        self.iface.mainWindow().menuBar().show()

    def my_prints_setup(self):
        btns = self.iface.mainWindow().findChildren(
            QToolButton, 'giapMyPrints')
        for btn in btns:
            btn.setToolTip("Moje wydruki")
            btn.setPopupMode(QToolButton.InstantPopup)
            self.action_my_prints_menu()
            self.projectLayoutManager.layoutAdded.connect(
                self.action_my_prints_menu
            )
            self.projectLayoutManager.layoutRemoved.connect(
                self.action_my_prints_menu
            )

    def action_my_prints_menu(self):
        btns = self.iface.mainWindow().findChildren(
            QToolButton, 'giapMyPrints')
        for btn in btns:
            main_widget = self.main_widget
            menu = QMenu(main_widget)
            actions = []
            projectInstance = QgsProject.instance()
            self.projectLayoutManager = projectInstance.layoutManager()
            for layout in self.projectLayoutManager.layouts():
                title = layout.name()
                action = QAction(title, main_widget)
                action.triggered.connect(
                    lambda checked, item=action:
                    self.open_layout_by_name(item.text()))
                actions.append(action)
            actions.sort(key=lambda x: x.text())
            list(map(menu.addAction, actions))
            btn.setMenu(menu)

    def open_layout_by_name(self, action_name):
        layout = self.projectLayoutManager.layoutByName(action_name)
        self.iface.openLayoutDesigner(layout)

    def unload(self):
        self.iface.mainWindow().menuBar().show()
        self.style_manager.activate_style('')
        self.save_user_ribbon_config(False)
        self.kompozycje.unload()
        self.toolbar.hide()
        self.orto_add.disconnect_ortofotomapa_group()

        # reinstitute original qgis layout
        self.load_default_user_layout()

        self.iface.messageBar().pushMessage(
            'GIAP Layout',
            # QApplication.translate('giap_pl', 'Please, restart QGIS!'),
            'Please, restart QGIS!',
            Qgis.Info,
            0
        )

    def menu_show(self):
        """Toggle visiblity of menubar"""
        if self.menuButton.isChecked():
            self.iface.mainWindow().menuBar().show()
        else:
            self.iface.mainWindow().menuBar().hide()

    def ustaw_legende(self):
        self.layer_panel = self.iface.mainWindow().findChild(
            QDockWidget, 'Layers')
        self.layer_panel.setTitleBarWidget(QWidget())

        self.layer_view = self.iface.layerTreeView()
        self.layer_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layer_toolbar = self.layer_view.parent().children()[1]

        layer_toolbar.children()[9].setPopupMode(2)
        widget_w_warstwach = QWidget()
        layout_widgetu = QVBoxLayout()
        layout_widgetu.addWidget(layer_toolbar)
        layout_widgetu.addWidget(self.kompozycje_widget)
        layout_widgetu.addWidget(self.layer_view)
        layout_widgetu.setContentsMargins(0, 7, 0, 4)
        widget_w_warstwach.setLayout(layout_widgetu)
        self.layer_panel.setWidget(widget_w_warstwach)
        self.layer_panel.setTitleBarWidget(QWidget())
        self.main_widget.pokaz_warstwy.toggled.connect(self.warstwy_show)

    def get_left_docks(self):
        docks = [x for x in self.iface.mainWindow().findChildren(QDockWidget)
                 if x.isVisible()
                 ]
        left_docks = [
            x for x in docks if
            self.iface.mainWindow().dockWidgetArea(x) == Qt.LeftDockWidgetArea
        ]
        return left_docks

    def warstwy_show(self):
        if self.main_widget.pokaz_warstwy.isChecked():
            left_docks = self.left_docks
            # there shoulde be docks if there is none add default from qgis.
            # (User turned off qgis with hidden docks)
            if len(self.left_docks) == 0:
                for dock in ['Layers', 'Browser']:
                    child = self.iface.mainWindow().findChild(QDockWidget,
                                                              dock)
                    if child:
                        left_docks.append(child)
        else:
            left_docks = self.get_left_docks()

        for ldock in left_docks:
            splitter_start = QRect(
                -ldock.width(), ldock.y(),
                ldock.width(), ldock.height())
            splitter_end = QRect(
                0, ldock.y(),
                ldock.width(), ldock.height())
            if self.main_widget.pokaz_warstwy.isChecked():
                ldock.show()
                self.set_animation(
                    ldock, splitter_start, splitter_end, 200
                )
                self.layer_view.resizeColumnToContents(0)
            else:
                self.set_animation(
                    ldock, splitter_end, splitter_start, 200, 'out'
                )

        self.left_docks = []
        if not self.main_widget.pokaz_warstwy.isChecked():
            self.left_docks = left_docks

    def set_animation(
            self, widget, qrect_start, qrect_end, duration, mode='in'):
        animation_in = QPropertyAnimation(widget, b"geometry")
        animation_in.setStartValue(qrect_start)
        animation_in.setEndValue(qrect_end)
        animation_in.setDuration(duration)
        animation_in.setEasingCurve(QEasingCurve.InOutQuad)
        animation_in.start()
        animation_in.finished.connect(
            lambda: self.delete_animation(animation_in, widget, mode)
        )

    def repair_layers_names_for_compositions(self):
        for layer in list(project.mapLayers().values()):
            layer.setName(layer.name().replace(':', '_'))

    def projekt_wczytany(self):
        """ setup after loading new project
        """
        if not project.fileName():
            return

        self.repair_layers_names_for_compositions()
        self.kompozycje.start()
        # self.main_widget.btn_projekt_3.clicked.connect(
        #     self.kompozycje.modify_tool.check_for_changes_in_comps)
        self.kompozycje.modify_tool.check_for_changes_in_comps()

    def setup_orto(self):
        """Setup qtoolbutton with menu, adds wms/wmts services to map
        """
        parent = self.main_widget
        btn = self.main_widget.btn_orto_2

        # przycisk dodawania ortofotomap
        self.orto_add = OrtoAddingTool(parent, btn)

        connect_orto = self.orto_add.connect_ortofotomapa_group
        for service in self.orto_add.services:
            service.orto_group_added.connect(connect_orto)

    def delete_animation(self, animation, widget, mode):
        del animation
        if mode == 'out':
            widget.hide()

    def show_style_manager_dialog(self):
        """Show dialog to manage qgis styles"""
        self.style_manager_dlg = StyleManagerDialog(self.style_manager)
        self.style_manager_dlg.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint
        )
        self.style_manager_dlg.exec_()
