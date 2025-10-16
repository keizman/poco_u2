"""
Android UIAutomation v1 entry now backed by UIAutomator2 only.

This file preserves the legacy class names (AndroidUiautomationPoco / Helper)
but routes all behavior to the UIAutomator2 implementation to ensure:
 - Exclusive use of UIAutomator2 APIs
 - Proper package attribute preservation in dumps
 - More stable dumps during video playback (no intrusive operations)
"""

import warnings

from .uiautomation2 import AndroidUiautomator2Poco, AndroidUiautomator2Helper

__all__ = ['AndroidUiautomationPoco', 'AndroidUiautomationHelper']


class AndroidUiautomationPoco(AndroidUiautomator2Poco):
    def __init__(self, device=None, device_id=None, using_proxy=True, force_restart=False,
                 use_airtest_input=False, screenshot_each_action=False, **options):
        # Inform users once that backend moved to UIAutomator2
        if not hasattr(self.__class__, '_deprecation_warned'):
            warnings.warn(
                'AndroidUiautomationPoco now uses UIAutomator2 backend exclusively. '
                'Legacy pocoservice/uiautomator is no longer used.',
                DeprecationWarning,
                stacklevel=2,
            )
            self.__class__._deprecation_warned = True

        super(AndroidUiautomationPoco, self).__init__(
            device=device,
            device_id=device_id,
            using_proxy=using_proxy,
            force_restart=force_restart,
            use_airtest_input=use_airtest_input,
            screenshot_each_action=screenshot_each_action,
            **options
        )


class AndroidUiautomationHelper(AndroidUiautomator2Helper):
    pass
