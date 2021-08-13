# -*- coding: utf-8 -*-
import os.path
import webbrowser
from qgis.utils import iface
import qgis
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QPushButton
from qgis.PyQt.QtCore import QTranslator, QCoreApplication, QSize, \
    Qt, QRect, QPropertyAnimation, QEasingCurve, QSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar, QToolButton, QWidget, \
    QHBoxLayout, QDockWidget, QMenu, QVBoxLayout, QMessageBox

# Initialize Qt resources from file resources.py
from qgis._core import QgsProject, Qgis, QgsMessageLog

from .Settings.settings_layout import SettingsDialog
from .OrtoTools import OrtoAddingTool
from .QuickPrint import PrintMapTool

from .Kompozycje.Kompozycje import CompositionsTool
from .kompozycje_widget import kompozycjeWidget
# from .resources import *
# Import the code for the dialog
# from .giap_layout_dialog import MainTabQgsWidgetDialog
from .config import Config
from .tools import StyleManager
from .utils import tr

from .StyleManager.stylemanager import StyleManagerDialog
from .Searcher.searchTool import SearcherTool

from .giap_dynamic_layout import Widget, CustomToolButton
from .ribbon_config import RIBBON_DEFAULT
from .CustomMessageBox import CustomMessageBox
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
        self.install_translator()
        # initialize locale
        self.main_widget = Widget(self.iface.mainWindow())
        self.kompozycje_widget = kompozycjeWidget()

        # list with hidden left docs, to reinstitute on user click
        self.left_docks = []
        # setup config structure for maintainning, toolbar and user interface
        # customization
        self.config = Config()
        self.searcher = SearcherTool(self.main_widget, self.iface)

        # initialize StyleManager for styling handling
        self.style_manager = StyleManager(self)
        self.print_map_tool = PrintMapTool(self.iface)
        self.iface.projectRead.connect(self.projekt_wczytany)
        self.iface.newProjectCreated.connect(self.projekt_wczytany)
        self.iface.initializationCompleted.connect(self.load_ribbons)
        self.iface.newProjectCreated.connect(self.missingCorePlugins)

    def missingCorePlugins(self):
        if len(iface.mainWindow().findChild(QToolBar, 'mVectorToolBar').actions()) == 0:
            CustomMessageBox(None, f'{tr("Switch on manually missing core plugin: Topology Checker")}').button_ok()

    def initGui(self):
        # set default style and active style if config.json doesn't extists
        dic_style = self.style_manager.get_style_dictionary()
        self.config.set_default_style(dic_style)

        style = self.main_widget.styleSheet()
        self.iface.mainWindow().statusBar().setStyleSheet(style + """
        QSpinBox {
            height: 20px;
        }
        """)
        self.save_default_user_layout()
        self.style_manager.run_last_style()

        self.kompozycje = CompositionsTool(self.iface, self)

        self.toolbar = QToolBar('GiapToolBar', self.iface.mainWindow())
        self.toolbar.setObjectName('GiapToolBar')
        self.iface.mainWindow().addToolBar(self.toolbar)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.addWidget(self.main_widget)

        self.layer_view = self.iface.layerTreeView()
        self.layer_toolbar = self.layer_view.parent().children()[1]
        self.layer_toolbar.setGeometry(0,0, 280, 35)
        for toolbar_item in range(2, 13):
            if isinstance(self.layer_toolbar.children()[toolbar_item], QToolButton):
                self.layer_toolbar.children()[toolbar_item].setStyleSheet(
                    'width: 20px;'
                    'heigth 25px;'
                    'margin-left: 3px;'
                    'border-radius: 4px;'
                    'padding: 3px;'
                )

        if isinstance(self.layer_toolbar.children()[9], QToolButton):
            self.layer_toolbar.children()[9].setPopupMode(2)

        self.layer_view.setGeometry(0, 79, 280, 1200)
        self.layer_view.setTextElideMode(Qt.ElideRight)
        self.kompozycje_widget.setGeometry(0, 35, 280, 50)
        self.main_widget.pokaz_warstwy.toggled.connect(self.warstwy_show)
        self.kompozycje_widget.setParent(self.iface.mapCanvas())
        self.layer_view.setParent(self.iface.mapCanvas())
        self.layer_toolbar.setParent(self.iface.mapCanvas())
        self.menuButton = QToolButton()
        self.menuButton.setText(tr("Show menu"))
        self.menuButton.setCheckable(True)
        self.menuButton.setBaseSize(QSize(80, 25))
        self.menuButton.toggled.connect(self.menu_show)

        self.editButton = QToolButton()
        self.editButton.setText(tr("Edit menu"))
        self.editButton.setCheckable(True)
        self.editButton.setBaseSize(QSize(25, 25))
        self.editButton.toggled.connect(self.set_edit_session)
        self.menu_show()

        self.styleButton = QToolButton()
        self.styleButton.setText(tr("Theme"))
        self.styleButton.setBaseSize(QSize(25, 25))
        self.styleButton.clicked.connect(self.show_style_manager_dialog)
        self.styleButton.setObjectName('ThemeButton')

        self.settingsButton = QToolButton()
        self.settingsButton.setText(tr("Settings"))
        self.settingsButton.setBaseSize(QSize(25, 25))
        self.settingsButton.clicked.connect(self.show_settings_dialog)
        self.settingsButton.setObjectName('SettingsButton')

        corner_widget = QWidget(self.main_widget.tabWidget)
        corner_layout = QHBoxLayout()
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.addWidget(self.menuButton)
        corner_layout.addWidget(self.editButton)
        corner_layout.addWidget(self.styleButton)
        corner_layout.addWidget(self.settingsButton)

        #logo icon
        plug_dir = os.path.dirname(__file__)
        gbut = QPushButton()
        gbut.clicked.connect(lambda: webbrowser.open('www.giap.pl'))
        gbut.setIcon(
            QIcon(os.path.join(plug_dir, 'icons', 'giap.png'))
        )
        gbut.setCursor(QCursor(Qt.PointingHandCursor))
        gbut.setToolTip("GIAP.pl - Strona WWW")
        gbut.setStyleSheet(
            'QPushButton{border-width: 0px; width: 220px; height:72px;'
            'background-color: transparent;}'
        )
        gbut.setIconSize(QSize(216, 68))

        #toolbar with only logo
        self.logo_toolbar = QToolBar('GiapLogoBar', self.iface.mainWindow())
        self.logo_toolbar.setObjectName('GiapLogoBar')
        self.iface.mainWindow().addToolBar(self.logo_toolbar)
        self.logo_toolbar.setMovable(False)
        self.logo_toolbar.setFloatable(True)
        self.logo_toolbar.addWidget(gbut)
        self.toolbar.visibilityChanged.connect(self.visible_logo_giap_toolbar)
        self.logo_toolbar.setLayoutDirection(Qt.RightToLeft)

        corner_widget.setLayout(corner_layout)
        self.main_widget.tabWidget.setCornerWidget(corner_widget)
        self.iface.mapCanvas().refresh()

        # signals
        self.main_widget.editChanged.connect(self.save_user_ribbon_config)
        self.main_widget.editChanged.connect(self.kompozycje.update_buttons)
        self.main_widget.printsAdded.connect(self.custom_prints)
        self.main_widget.editChanged.connect(self.custom_prints)
        self.project_path = os.path.dirname(
            os.path.abspath(project.fileName()))
        self.toolbar.show()

        #tools under GIAP logo
        self.main_widget.runQuickPrintButton.clicked.connect(self.print_map_tool.run)
        self.main_widget.runQuickPrintButton.setToolTip(tr("Map fast print"))
        self.main_widget.runQuickPrintButton.setIcon(QIcon(f'{self.plugin_dir}/icons/quick_print.png'))

        self.main_widget.runCompositionButton.clicked.connect(self.kompozycje.config)
        self.main_widget.runCompositionButton.setIcon(QIcon(f'{self.plugin_dir}/icons/compositions_giap.png'))
        self.main_widget.runCompositionButton.setToolTip(tr("Composition settings"))

        orto_button = self.main_widget.runOrtoTool
        orto_button.setIcon(QIcon(f'{self.plugin_dir}/icons/orto_icon2.png'))
        self.orto = OrtoAddingTool(self.main_widget, orto_button)

        self.visibility_search_tool = False
        self.main_widget.offOnSearchButton.clicked.connect(lambda: self.off_on_search_tool(self.visibility_search_tool))
        self.main_widget.offOnSearchButton.setIcon(QIcon(f'{self.plugin_dir}/styles/giap/icons/close.png'))

        #self.searcher.run()
        # set strong focus to get keypressevent
        self.main_widget.setFocusPolicy(Qt.StrongFocus)

        process = qgis.utils.plugins.get('processing')
        if process:
            process.initGui()
            process.initProcessing()
            self.load_ribbons()

    def load_ribbons(self):
        # turn on ribbon editing
        self.main_widget.edit_session_toggle()

        ribbon_conf = self.config.load_user_ribbon_setup()
        if not ribbon_conf:
            ribbon_conf = RIBBON_DEFAULT

        for dtab in ribbon_conf:
            itab, tab = self.main_widget.add_tab(dtab['tab_name'])
            for dsec in dtab['sections']:
                sec = self.main_widget.add_section(
                    itab, tr(dsec['label']), dsec['btn_size']
                )
                for btn in dsec['btns']:
                    child = self.iface.mainWindow().findChild(QAction, btn[0])
                    if child is None:
                        sec.add_action(*btn)
                    else:
                        if btn[0] == 'mActionShowAlignRasterTool':
                            child.setIcon(QIcon(f'{self.plugin_dir}/icons/orto_icon2.png'))
                        sec.add_action(child, *btn[1:])
                if dsec['label'] == 'Prints':
                    self.custom_prints()

        self.main_widget.tabWidget.setCurrentIndex(0)
        # turn off ribbon editing
        self.main_widget.edit_session_toggle()

    def visible_logo_giap_toolbar(self, visible):
        self.logo_toolbar.setVisible(not visible)

    def off_on_search_tool(self, visibility):
        elements = ['comboBox_woj', 'comboBox_pow', 'comboBox_gmina', 'comboBox_obr',
                    'lineEdit_parcel', 'lineEdit_address', 'line']

        for elem in elements:
            getattr(self.main_widget, elem).setVisible(visibility)
        self.visibility_search_tool = not visibility

    def custom_prints(self):
        """Load custom tools to qgis"""

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
            btn.setToolTip(tr("My Prints"))
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
        # self.main_widget.unload_custom_actions()
        self.kompozycje.unload()
        self.toolbar.hide()

        # reinstitute original qgis layout
        self.kompozycje_widget.hide()
        self.load_default_user_layout()

        self.iface.messageBar().pushMessage(
            'GIAP Layout',
            tr('Please, restart QGIS!'),
            Qgis.Info,
            0
        )

    def menu_show(self):
        """Toggle visiblity of menubar"""
        mbar = self.iface.mainWindow().menuBar()
        splitter_start = QRect(0, -20, mbar.width(), 20)
        splitter_end = QRect(0, 0, mbar.width(), 20)
        if self.menuButton.isChecked():
            mbar.show()
            self.set_animation(mbar, splitter_start, splitter_end, 200)
        else:
            self.set_animation(mbar, splitter_end, splitter_start, 200)
            mbar.hide()

    def set_edit_session(self):
        if self.editButton.isChecked():
            self.editButton.setText(tr("Complete edit"))
            self.main_widget.edit_session_toggle()
        else:
            self.editButton.setText(tr("Edit menu"))
            self.main_widget.edit_session_toggle(True)

            if self.main_widget.save == QMessageBox.No:

                for tabind in range(len(self.main_widget.tabs)):
                    self.main_widget.remove_tab(0)
                self.load_ribbons()

    def warstwy_show(self):
        if self.main_widget.pokaz_warstwy.isChecked():
            self.layer_view.show()
            self.layer_toolbar.show()
            self.kompozycje_widget.show()
            canvas_geom = self.iface.mapCanvas().geometry()
            self.layer_view.setGeometry(0, 79, 280, canvas_geom.height()-79)
            self.layer_view.resizeColumnToContents(0)
        else:
            self.layer_view.hide()
            self.layer_toolbar.hide()
            self.kompozycje_widget.hide()

    def resize_layer_view(self):
        canvas_geom = self.iface.mapCanvas().geometry()
        self.layer_view.setGeometry(0, 79, 280, canvas_geom.height()-79)

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

        self.repair_layers_names_for_compositions()
        self.kompozycje.start()
        self.kompozycje.modify_tool.check_for_changes_in_comps()

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

    def show_settings_dialog(self):
        self.set_dlg=SettingsDialog()
        self.set_dlg.pushButton_restore.clicked.connect(self.restore_default_ribbon_settings)
        self.set_dlg.radioButton_pl.toggled.connect(self.set_polish)
        self.set_dlg.radioButton_en.toggled.connect(self.set_english)
        self.set_dlg.exec_()

    def set_polish(self):
        QSettings().setValue('locale/userLocale', 'pl')

    def set_english(self):
        QSettings().setValue('locale/userLocale', 'en')

    def restore_default_ribbon_settings(self):
        self.set_dlg.pushButton_restore.clicked.disconnect()
        edit_ses_on_start = self.main_widget.edit_session
        if edit_ses_on_start:
            self.main_widget.edit_session_toggle()
        for tabind in range(len(self.main_widget.tabs)):
            self.main_widget.remove_tab(0)
        self.save_user_ribbon_config(False)
        self.load_ribbons()
        if edit_ses_on_start:
            self.main_widget.edit_session_toggle()
        self.set_dlg.pushButton_restore.clicked.connect(self.restore_default_ribbon_settings)

    def install_translator(self):
        locale = 'en'
        try:
            # not always locale can be converted to str, apparently
            loc = str(QSettings().value('locale/userLocale'))
            if len(locale) > 1:
                locale = loc[:2]
        except Exception:
            # do not install translator -> english
            return

        if locale == 'en':
            return

        trans_path = os.path.join(self.plugin_dir, 'i18n', f'giap_{locale}.qm')
        if not os.path.exists(trans_path):
            return

        self.translator = QTranslator()
        self.translator.load(trans_path)
        QCoreApplication.installTranslator(self.translator)
