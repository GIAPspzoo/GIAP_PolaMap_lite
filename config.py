import json
import os

from qgis.core import QgsMessageLog

from .utils import DEFAULT_STYLE


class Config:
    def __init__(self):
        """Constructor"""
        # load config from file
        self.setts = {}
        self.conf_dir = os.path.dirname(__file__)
        config_path = os.path.join(self.conf_dir, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as fl:
                conf = fl.read()
            try:
                self.setts = json.loads(conf)[0]
            except ValueError:
                QgsMessageLog.logMessage(
                    'Failed to load config from config.json')

    def save_config(self):
        """
        Saves config to json file
        """

        save_file = open(os.path.join(self.conf_dir, 'config.json'), 'w')
        json.dump([self.setts], save_file)
        save_file.close()

    def save_original_toolbars(self, tbrs):
        """ Save toolbars to reinstitute them after unload
        :tbrs: [str, str, str]
        """
        # save only if don't have anything in storage
        if 'org_toolbars' in self.setts:
            # if we have something in storage, dont change it
            if len(self.setts['org_toolbars']) > 0:
                return

        self.setts['org_toolbars'] = tbrs
        self.save_config()

    def save_user_ribbon_setup(self, val):
        """ Saves user setup to config qgis file
        {'ribbons': {
            'tab_name': 'name',
            'sections': [
                {
                    'label': 'lab_name',
                    'btn_size': 30,
                    'btns': [
                        [action, row, col],
                    ], ...
                }
                ],
            }, ... },
         'fast_access': [ action, action, ... ]
        }
        """
        if not isinstance(val, list):
            return False

        self.setts['ribbons_config'] = val
        self.save_config()

    def save_custom_sections_setup(self, val):
        """ Saves custom sections to config qgis file
        {'ribbons': {
            'tab_name': 'name',
            'sections': [
                {
                    'label': 'lab_name',
                    'btn_size': 30,
                    'btns': [
                        [action, row, col],
                    ], ...
                }
                ],
            }, ... },
         'fast_access': [ action, action, ... ]
        }
        """
        if not isinstance(val, list):
            return False

        self.setts['custom_sections'] = val
        self.save_config()

    def load_user_ribbon_setup(self):
        if 'ribbons_config' not in self.setts:
            return False

        lay = self.setts['ribbons_config']
        if not lay:
            return False

        return self.setts['ribbons_config']

    def load_custom_sections_setup(self):
        if 'custom_sections' not in self.setts:
            return False
        lay = self.setts['custom_sections']
        if not lay:
            return False
        return self.setts['custom_sections']

    def get_original_toolbars(self):
        """ Return list of objectnames toolbars originally opened before first
        run
        :return: [str, str, str]
        """
        try:
            org_tbrs = self.setts['org_toolbars']
            if 'GiapToolBar' in org_tbrs:  # insurance
                org_tbrs.remove('GiapToolBar')
        except Exception:
            # something goes wrong, we don't have previous version of user
            # layout in this case, recover main toolbars
            org_tbrs = []

        if len(org_tbrs) == 0:
            org_tbrs = [
                'mFileToolBar',
                'mLayerToolBar',
                'mDigitizeToolBar',
                'mMapNavToolBar',
                'mAttributesToolBar',
                'mPluginToolBar',
                'mLabelToolBar',
                'mSnappingToolBar',
                'mSelectionToolBar',
            ]
        return org_tbrs

    def set_value(self, key, val):
        """ Sets value under key in settings, value if exists will be
        overwritten
        :key: str
        :val: object
        """
        self.setts[key] = val
        self.save_config()

    def get_value(self, key):
        """read value saved in config
        :key: str (full path ie 'giap/test')
        """
        return self.setts[key]

    def delete_value(self, key):
        """delete key from config
        :key: str
        """
        try:
            del self.setts[key]
        except Exception:
            pass

    def get_style_path(self, style):
        """ read path o style from config
        :return: str
        """

        try:
            return self.setts['styles'][style]
        except KeyError:
            return ''

    def get_style_list(self):
        """ return list of available styles
        :return: list
        """
        try:
            return list(self.setts['styles'].keys())
        except Exception:
            return []

    def get_active_style(self):
        """ return name of active style from settings
        :return: str
        """
        try:
            return self.setts['active_style']
        except KeyError:
            return ''

    def set_style(self, style, path):
        """ Set style in config, for user to choose it
        :style: style name
        :path: style name (style.qss)
        """
        self.setts['styles'][style] = path

    def set_default_style(self, dic_styles):
        if 'styles' not in self.setts:
            self.setts['styles'] = dic_styles
        if 'active_style' not in self.setts:
            self.setts['active_style'] = DEFAULT_STYLE
        self.save_config()

    def set_active_style(self, style):
        """
        set name of active style in config
        """
        self.setts['active_style'] = style
        self.save_config()

    def remove_style(self, style):
        if style in self.setts['style']:
            del self.setts['style'][style]
        self.save_config()
