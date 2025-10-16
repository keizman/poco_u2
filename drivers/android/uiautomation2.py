# coding=utf-8
__author__ = 'refactor-bot'

"""
UIAutomator2-based Android driver for tmp.poco_v1

Goals:
- Use UIAutomator2 exclusively for hierarchy, attributes, and input.
- Preserve backward-compatible dump structure expected by Poco v1.
- Ensure package and other XML attributes are fully propagated.
- Improve robustness for dynamic content (e.g., video playback) by
  avoiding visibility-based filtering and intrusive screen operations.
"""

import time
import warnings
import xml.etree.ElementTree as ET
import sys as _sys
import glob as _glob
import os as _os
import re as _re

# Python 3.6 compatibility shims for libraries expecting 3.7+
try:  # re.Pattern/re.Match were introduced in 3.7
    _ = _re.Pattern  # type: ignore[attr-defined]
except Exception:
    try:
        _re.Pattern = type(_re.compile(''))  # type: ignore[attr-defined]
    except Exception:
        pass
try:
    _ = _re.Match  # type: ignore[attr-defined]
except Exception:
    try:
        _re.Match = type(_re.match('', ''))  # type: ignore[attr-defined]
    except Exception:
        pass


def _bootstrap_thirdparty_paths():
    """Add bundled third‑party wheels/dirs to sys.path if present.

    For embedded Python in AirtestIDE, place dependencies into one of:
      - <poco>/thirdparty
      - <poco>/_deps
      - <poco>/_vendor
    as extracted directories or .whl/.zip files. Also respects env
    POCO_THIRDPARTY for an absolute directory.
    """
    # poco root = .../poco
    poco_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), _os.pardir, _os.pardir))
    candidates = [
        _os.environ.get('POCO_THIRDPARTY'),
        _os.path.join(poco_root, 'thirdparty'),
        _os.path.join(poco_root, 'thirdparty', 'site-packages'),
        _os.path.join(poco_root, 'thirdparty', 'Lib', 'site-packages'),
        _os.path.join(poco_root, 'thirdparty', 'lib', 'site-packages'),
        _os.path.join(poco_root, 'thirdparty', 'whl'),
        _os.path.join(poco_root, '_deps'),
        _os.path.join(poco_root, '_vendor'),
    ]
    debug = _os.environ.get('POCO_THIRDPARTY_DEBUG') == '1'
    for p in [c for c in candidates if c]:
        try:
            added = []
            if _os.path.isdir(p) and p not in _sys.path:
                _sys.path.insert(0, p)
                added.append(p)
            # Common nested site-packages locations
            for sub in ('site-packages', _os.path.join('Lib', 'site-packages'), _os.path.join('lib', 'site-packages')):
                sp = _os.path.join(p, sub)
                if _os.path.isdir(sp) and sp not in _sys.path:
                    _sys.path.insert(0, sp)
                    added.append(sp)
            # Include any wheels/zips inside root and nested site-packages
            for base in [p] + [ap for ap in added if ap != p]:
                for whl in _glob.glob(_os.path.join(base, '*.whl')) + _glob.glob(_os.path.join(base, '*.zip')):
                    # Never add uiautomator2 wheel into sys.path to ensure asset files are read from extracted package
                    if 'uiautomator2-' in _os.path.basename(whl):
                        continue
                    if whl not in _sys.path:
                        _sys.path.insert(0, whl)
                        added.append(whl)
            if debug and added:
                try:
                    warnings.warn('POCO_THIRDPARTY added paths: {}'.format(added))
                    # also write to a debug file for offline checking
                    with open(_os.path.join(poco_root, 'thirdparty', '_debug_paths.txt'), 'a', encoding='utf-8') as f:
                        f.write('added from {} -> {}\n'.format(p, added))
                except Exception:
                    pass
        except Exception:
            pass


# Always bootstrap before first import to avoid caching old PIL
_bootstrap_thirdparty_paths()

# Work around environment shadowing + missing dependency: some IDE bundles
# include a flat progress.py(c) which breaks `from progress.bar import Bar`.
# 1) Prefer the real package from thirdparty by removing flat module entries.
# 2) If still unavailable, install a minimal shim that satisfies imports.
try:
    import importlib as _importlib
    if 'progress' in _sys.modules and not hasattr(_sys.modules['progress'], '__path__'):
        _sys.modules.pop('progress', None)
    # try real package first
    try:
        _importlib.import_module('progress.bar')
    except Exception:
        # Prefer real package if present in thirdparty site-packages
        try:
            # Ensure progress directory is prioritized
            for p in list(_sys.path):
                if p.endswith(_os.path.join('thirdparty','site-packages')):
                    if p in _sys.path:
                        _sys.path.remove(p)
                        _sys.path.insert(0, p)
            _importlib.invalidate_caches()
            _importlib.import_module('progress.bar')
        except Exception:
            # final fallback: provide a tiny shim so imports won't fail
            import types as _types
            class _Bar(object):
                def __init__(self, *a, **k): pass
                def next(self, *a, **k): pass
                def finish(self, *a, **k): pass
            base = _sys.modules.get('progress')
            if base is None:
                base = _types.ModuleType('progress')
                _sys.modules['progress'] = base
            # mark as package
            if not hasattr(base, '__path__'):
                base.__path__ = []
            sub = _types.ModuleType('progress.bar')
            sub.Bar = _Bar
            base.bar = sub
            _sys.modules['progress.bar'] = sub
except Exception:
    pass

# Prefer extracted uiautomator2 package (with real file assets) over .whl
try:
    poco_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), _os.pardir, _os.pardir))
    extracted_assets = _os.path.join(poco_root, 'thirdparty', 'site-packages', 'uiautomator2', 'assets', 'app-uiautomator.apk')
    if _os.path.exists(extracted_assets):
        # Remove ANY uiautomator2 wheel entries to force file-based import
        _sys.path[:] = [p for p in _sys.path if 'uiautomator2-' not in (p or '')]
        # If u2 already imported from whl, unload it so we can re-import
        mod = _sys.modules.get('uiautomator2')
        if mod is not None and '.whl' in str(getattr(mod, '__file__', '') or ''):
            for k in list(_sys.modules.keys()):
                if k == 'uiautomator2' or k.startswith('uiautomator2.'):
                    _sys.modules.pop(k, None)
except Exception:
    pass

# Try import uiautomator2, tolerating old PIL by shimming UnidentifiedImageError
u2 = None
_uia2_import_error = None

# If an old PIL (e.g., 5.4.1) is already imported by IDE, define missing symbol
try:
    import PIL as _PIL
    if not hasattr(_PIL, 'UnidentifiedImageError'):
        # Provide a compatible placeholder for code catching this exception
        class _UE(Exception):
            pass
        _PIL.UnidentifiedImageError = _UE
except Exception:
    pass

try:
    import uiautomator2 as u2  # type: ignore
    try:
        src = getattr(u2, '__file__', '')
        if src:
            warnings.warn('uiautomator2 loaded from: {}'.format(src))
    except Exception:
        pass
except Exception as e:
    _uia2_import_error = e

from poco.pocofw import Poco
from poco.agent import PocoAgent
from poco.sdk.interfaces.hierarchy import HierarchyInterface
from poco.sdk.interfaces.input import InputInterface
from poco.sdk.interfaces.screen import ScreenInterface
from poco.sdk.AbstractNode import AbstractNode
from poco.sdk.AbstractDumper import AbstractDumper
from poco.sdk.Attributor import Attributor
from poco.utils import six

__all__ = [
    'AndroidUiautomator2Poco',
    'AndroidUiautomator2Helper',
    # exported for tests/mocks
    'UIAutomator2Node',
    'UIAutomator2Dumper',
]


class UIAutomator2Node(AbstractNode):
    """UIAutomator2 node wrapper compatible with Poco v1 attributes.

    This maps standard UIAutomator XML attributes (class, resource-id, package,
    text, content-desc, bounds, etc.) to Poco's expected attribute names and
    normalized coordinate system.
    """

    def __init__(self, xml_element, screen_size=(1280, 720)):
        super(UIAutomator2Node, self).__init__()
        self.xml_element = xml_element
        self.screen_width, self.screen_height = screen_size
        self._parent = None
        self._children = None

    def getParent(self):  # pragma: no cover - simple getter
        return self._parent

    def setParent(self, parent):  # pragma: no cover - simple setter
        self._parent = parent

    def getChildren(self):
        if self._children is None:
            self._children = []
            for child_elem in self.xml_element:
                child_node = UIAutomator2Node(child_elem, (self.screen_width, self.screen_height))
                child_node.setParent(self)
                self._children.append(child_node)
        return self._children

    def _parse_bounds(self):
        # Root hierarchy case: no bounds
        if self.xml_element.tag == 'hierarchy':
            return 0, 0, 0, 0

        bounds_str = self.xml_element.attrib.get('bounds', '[0,0][0,0]')
        try:
            bounds_str = bounds_str.replace('[', '').replace(']', ',')
            coords = [int(x) for x in bounds_str.split(',') if x]
            if len(coords) >= 4:
                return coords[0], coords[1], coords[2], coords[3]  # x1, y1, x2, y2
        except Exception:
            pass
        return 0, 0, 0, 0

    def _get_normalized_pos(self):
        if self.xml_element.tag == 'hierarchy':
            return [0.0, 0.0]
        x1, y1, x2, y2 = self._parse_bounds()
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        return [cx / float(self.screen_width), cy / float(self.screen_height)]

    def _get_normalized_size(self):
        if self.xml_element.tag == 'hierarchy':
            return [0.0, 0.0]
        x1, y1, x2, y2 = self._parse_bounds()
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        return [w / float(self.screen_width), h / float(self.screen_height)]

    def _get_bounds_array(self):
        if self.xml_element.tag == 'hierarchy':
            return []
        x1, y1, x2, y2 = self._parse_bounds()
        return [
            x1 / float(self.screen_width),
            y1 / float(self.screen_height),
            x2 / float(self.screen_width),
            y2 / float(self.screen_height),
        ]

    def getAttr(self, attrName):
        attrib = self.xml_element.attrib

        # Handle hierarchy root defaults
        if self.xml_element.tag == 'hierarchy':
            defaults = {
                'name': '<Unknown>',
                'type': 'Unknown',
                'visible': True,
                'enabled': False,
                'pos': [0.0, 0.0],
                'size': [0.0, 0.0],
                'bounds': [],
                'text': '',
                'resourceId': '',
                'package': '',
                'clickable': False,
                'touchable': False,
                'focusable': False,
                'focused': False,
                'scrollable': False,
                'selected': False,
                'checkable': False,
                'checked': False,
                'longClickable': False,
                'editable': False,
                'dismissable': False,
                'scale': [1.0, 1.0],
                'anchorPoint': [0.5, 0.5],
                'zOrders': {'local': 0, 'global': 0},
                'boundsInParent': [],
            }
            return defaults.get(attrName, None)

        if attrName == 'name':
            txt = attrib.get('text', '').strip()
            return txt if txt else attrib.get('class', '<Unknown>')
        if attrName == 'type':
            return attrib.get('class', 'Unknown')
        if attrName == 'class_name':
            return attrib.get('class', '')
        if attrName == 'visible':
            return attrib.get('visible-to-user', 'true').lower() == 'true'
        if attrName == 'enabled':
            return attrib.get('enabled', 'true').lower() == 'true'
        if attrName == 'pos':
            return self._get_normalized_pos()
        if attrName == 'size':
            return self._get_normalized_size()
        if attrName == 'bounds':
            return self._get_bounds_array()
        if attrName == 'text':
            return attrib.get('text', '')
        if attrName == 'resourceId':
            return attrib.get('resource-id', '')
        if attrName == 'package':
            # Critical: preserve package attribute from XML
            return attrib.get('package', '')
        if attrName == 'contentDesc':
            return attrib.get('content-desc', '')
        if attrName == 'clickable':
            return attrib.get('clickable', 'false').lower() == 'true'
        if attrName == 'touchable':
            return attrib.get('clickable', 'false').lower() == 'true'
        if attrName == 'focusable':
            return attrib.get('focusable', 'false').lower() == 'true'
        if attrName == 'focused':
            return attrib.get('focused', 'false').lower() == 'true'
        if attrName == 'scrollable':
            return attrib.get('scrollable', 'false').lower() == 'true'
        if attrName == 'selected':
            return attrib.get('selected', 'false').lower() == 'true'
        if attrName == 'checkable':
            return attrib.get('checkable', 'false').lower() == 'true'
        if attrName == 'checked':
            return attrib.get('checked', 'false').lower() == 'true'
        if attrName == 'longClickable':
            return attrib.get('long-clickable', 'false').lower() == 'true'
        if attrName == 'editable':
            return 'EditText' in attrib.get('class', '')
        if attrName == 'dismissable':
            return False
        if attrName == 'scale':
            return [1.0, 1.0]
        if attrName == 'anchorPoint':
            return [0.5, 0.5]
        if attrName == 'zOrders':
            try:
                order = int(attrib.get('drawing-order', '0'))
            except Exception:
                order = 0
            return {'local': order, 'global': order}
        if attrName == 'boundsInParent':
            return self._get_normalized_size()

        return super(UIAutomator2Node, self).getAttr(attrName)

    def getAvailableAttributeNames(self):
        base = list(super(UIAutomator2Node, self).getAvailableAttributeNames())
        android_attrs = [
            'text', 'resourceId', 'package', 'contentDesc', 'class_name',
            'clickable', 'touchable', 'focusable', 'focused', 'scrollable',
            'selected', 'checkable', 'checked', 'longClickable', 'editable',
            'dismissable', 'bounds', 'boundsInParent', 'enabled',
        ]
        return base + android_attrs


class UIAutomator2Dumper(AbstractDumper):
    """Dumper using UIAutomator2 device to obtain hierarchy.

    Key behaviors:
    - Uses device.dump_hierarchy() (non-intrusive; avoids screen shrink side-effects)
    - Bypasses visibility-only filtering to keep nodes present in dynamic/video UIs
    - Preserves all XML attributes, especially 'package'
    """

    def __init__(self, device):
        super(UIAutomator2Dumper, self).__init__()
        self.device = device
        self._root_node = None
        self._screen_size = (1280, 720)

    def _update_hierarchy(self):
        try:
            # Use window_size as authoritative basis (matches Javacap/screenshot & IDE overlay)
            try:
                ws = self.device.window_size()  # (width, height)
                screen_size = (int(ws[0]), int(ws[1]))
            except Exception:
                info = getattr(self.device, 'info', {}) or {}
                screen_size = (
                    int(info.get('displayWidth', 1280)),
                    int(info.get('displayHeight', 720)),
                )
            self._screen_size = screen_size

            # Get XML hierarchy with full details (avoid compressed trees hiding overlay controls)
            try:
                xml_content = self.device.dump_hierarchy(compressed=False)
            except TypeError:
                try:
                    xml_content = self.device.dump_hierarchy(False)
                except Exception:
                    xml_content = self.device.dump_hierarchy()
            root_element = ET.fromstring(xml_content)
            self._root_node = UIAutomator2Node(root_element, screen_size)
        except Exception as e:
            warnings.warn('Failed to update hierarchy: {}'.format(e))
            self._screen_size = (1280, 720)
            self._root_node = UIAutomator2Node(ET.Element('hierarchy'), self._screen_size)

    def getRoot(self):
        if self._root_node is None:
            self._update_hierarchy()
        return self._root_node

    def dumpHierarchy(self, onlyVisibleNode=True):  # noqa: N802
        # Always bypass visibility-only filtering to better capture playback overlays
        self._root_node = None  # force refresh
        return super(UIAutomator2Dumper, self).dumpHierarchy(False)

    def invalidate_cache(self):  # pragma: no cover - simple cache control
        self._root_node = None

    def get_screen_size(self):
        # Ensure updated at least once
        if self._root_node is None:
            try:
                self._update_hierarchy()
            except Exception:
                pass
        return self._screen_size


class UIAutomator2Attributor(Attributor):
    def __init__(self, device):
        super(UIAutomator2Attributor, self).__init__()
        self.device = device

    def getAttr(self, node, attrName):  # noqa: N802
        if isinstance(node, UIAutomator2Node):
            return node.getAttr(attrName)
        return None

    def setAttr(self, node, attrName, attrVal):  # noqa: N802
        # Minimal implementation; UIAutomator2 direct attribute setting is limited
        if not isinstance(node, UIAutomator2Node):
            return False

        if attrName == 'text':
            try:
                rid = node.getAttr('resourceId')
                if rid:
                    self.device(resourceId=rid).set_text(attrVal)
                    return True
                # fallback by text/class coordinates
                pos = node.getAttr('pos')
                if pos:
                    x, y = pos
                    # convert normalized to pixels
                    info = self.device.info
                    px = int(x * info.get('displayWidth', 1280))
                    py = int(y * info.get('displayHeight', 720))
                    self.device.click(px, py)
                    # use set_text after focus
                    self.device.set_fastinput_ime(True)
                    self.device.send_keys(attrVal)
                    self.device.set_fastinput_ime(False)
                    return True
            except Exception as e:
                warnings.warn('setAttr(text) failed: {}'.format(e))
        return False


class UIAutomator2Input(InputInterface):
    def __init__(self, device, dumper=None):
        super(UIAutomator2Input, self).__init__()
        self.device = device
        self.dumper = dumper
        self.default_touch_down_duration = 0.01
        self._cached_screen = None

    def _screen_info(self):
        if self._cached_screen is None:
            if self.dumper is not None and hasattr(self.dumper, 'get_screen_size'):
                w, h = self.dumper.get_screen_size()
            else:
                try:
                    ws = self.device.window_size()
                    w, h = int(ws[0]), int(ws[1])
                except Exception:
                    info = self.device.info
                    w, h = info.get('displayWidth', 1280), info.get('displayHeight', 720)
            self._cached_screen = {'width': w, 'height': h}
        return self._cached_screen

    def _to_px(self, x, y):
        s = self._screen_info()
        return int(x * s['width']), int(y * s['height'])

    def click(self, x, y):
        px, py = self._to_px(x, y)
        self.device.click(px, py)

    def right_click(self, x, y):  # compatibility; simulate long click
        self.long_click(x, y, 0.5)

    def double_click(self, x, y):
        px, py = self._to_px(x, y)
        try:
            self.device.double_click(px, py)
        except Exception:
            # emulate a double tap if method unavailable
            self.device.click(px, py)
            time.sleep(0.05)
            self.device.click(px, py)

    def long_click(self, x, y, duration=2.0):
        px, py = self._to_px(x, y)
        self.device.long_click(px, py, duration)

    # legacy alias
    def longClick(self, x, y, duration=2.0):  # noqa: N802
        return self.long_click(x, y, duration)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        x1, y1 = self._to_px(x1, y1)
        x2, y2 = self._to_px(x2, y2)
        self.device.swipe(x1, y1, x2, y2, duration)

    def drag(self, x1, y1, x2, y2, duration=2.0):
        x1, y1 = self._to_px(x1, y1)
        x2, y2 = self._to_px(x2, y2)
        self.device.drag(x1, y1, x2, y2, duration)

    def keyevent(self, keyname):
        mapping = {
            'HOME': 'home', 'BACK': 'back', 'MENU': 'menu', 'ENTER': 'enter',
            'DELETE': 'del', 'VOLUME_UP': 'volume_up', 'VOLUME_DOWN': 'volume_down',
        }
        self.device.press(mapping.get(keyname, keyname.lower()))

    def setTouchDownDuration(self, duration):  # noqa: N802
        self.default_touch_down_duration = duration

    def getTouchDownDuration(self):  # noqa: N802
        return self.default_touch_down_duration

    def applyMotionEvents(self, events):  # noqa: N802
        warnings.warn('applyMotionEvents has limited support in UIAutomator2')
        for e in events:
            if not e:
                continue
            t = e[0]
            if t == 'd':
                pos = e[1]
                px, py = self._to_px(pos[0], pos[1])
                self.device.click(px, py)
            elif t == 's':
                time.sleep(e[1])


class UIAutomator2Screen(ScreenInterface):
    def __init__(self, device, dumper=None):
        super(UIAutomator2Screen, self).__init__()
        self.device = device
        self.dumper = dumper

    def getScreen(self, width):
        try:
            import base64, io
            from PIL import Image
            im = self.device.screenshot(format='pillow')
            if width and width > 0:
                ratio = width / float(im.width)
                im = im.resize((width, int(im.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=80)
            return base64.b64encode(buf.getvalue()).decode('utf-8'), 'jpg'
        except Exception as e:
            warnings.warn('Failed to capture screen: {}'.format(e))
            return None, None

    def getPortSize(self):  # noqa: N802
        if self.dumper is not None and hasattr(self.dumper, 'get_screen_size'):
            w, h = self.dumper.get_screen_size()
            return [w, h]
        info = self.device.info
        return [info.get('displayWidth', 1280), info.get('displayHeight', 720)]


class UIAutomator2Hierarchy(HierarchyInterface):
    def __init__(self, dumper, selector, attributor):
        super(UIAutomator2Hierarchy, self).__init__()
        self.dumper = dumper
        self.selector = selector  # unused
        self.attributor = attributor

    def dump(self):
        return self.dumper.dumpHierarchy()

    def getAttr(self, node, attrName):  # noqa: N802
        return self.attributor.getAttr(node, attrName)

    def setAttr(self, node, attrName, attrVal):  # noqa: N802
        return self.attributor.setAttr(node, attrName, attrVal)

    def select(self, query, multiple=False):
        # Basic tree traversal/attribute match to remain compatible with v1 expectations
        try:
            root = self.dumper.getRoot()
            if not root:
                return []
            matches = self._select_nodes(root, query, multiple=True) or []
            return matches if multiple else matches[:1]
        except Exception as e:
            warnings.warn('Selection failed: {}'.format(e))
            return []

    def _select_nodes(self, root, query, multiple=False):
        def evaluate(node, conditions):
            if not conditions:
                return True
            for cond in conditions:
                if not isinstance(cond, tuple) or len(cond) != 3:
                    continue
                op, attr, expected = cond
                actual = node.getAttr(attr)
                if op == 'attr=' and actual != expected:
                    return False
                if op == 'attr.*=' and str(expected) not in str(actual):
                    return False
            return True

        def normalize_query(q):
            # Convert Poco's query tuples into flat condition list where possible
            if isinstance(q, list):
                return q
            if isinstance(q, tuple) and len(q) >= 2:
                op = q[0]
                operands = q[1]
                if op == 'and' and isinstance(operands, (list, tuple)):
                    conds = []
                    for item in operands:
                        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], tuple):
                            pred, kv = item
                            conds.append((pred, kv[0], kv[1]))
                    return conds
                # child/parent ops: evaluate right side on current node for compatibility
                if op in ('>', '/', '-', '^'):
                    try:
                        return normalize_query(operands[1])
                    except Exception:
                        return []
                if op == 'index':
                    return []
            return []

        conditions = normalize_query(query)
        out = []

        def dfs(n):
            if evaluate(n, conditions):
                out.append(n)
                if not multiple:  # early exit for single match
                    return True
            for c in n.getChildren() or []:
                if dfs(c) and not multiple:
                    return True
            return False

        dfs(root)
        return out


class AndroidUiautomator2Agent(PocoAgent):
    def __init__(self, device, use_airtest_input=False):
        dumper = UIAutomator2Dumper(device)
        selector = None  # unused in this simple implementation
        attributor = UIAutomator2Attributor(device)
        hierarchy = UIAutomator2Hierarchy(dumper, selector, attributor)

        if use_airtest_input:
            try:
                from poco.utils.airtest.input import AirtestInput
                inputer = AirtestInput()
            except Exception:
                warnings.warn('use_airtest_input=True but Airtest not available; falling back to UIAutomator2 input')
                inputer = UIAutomator2Input(device, dumper)
        else:
            inputer = UIAutomator2Input(device, dumper)

        super(AndroidUiautomator2Agent, self).__init__(hierarchy, inputer, UIAutomator2Screen(device, dumper), None)


class AndroidUiautomator2Poco(Poco):
    """Primary entry for tmp.poco_v1 Android using UIAutomator2 backend only."""

    def __init__(self, device=None, device_id=None, using_proxy=True, force_restart=False,
                 use_airtest_input=False, screenshot_each_action=False, **options):
        # lazy import check
        if _uia2_import_error is not None or u2 is None:  # pragma: no cover
            msg = str(_uia2_import_error)
            tips = (
                'uiautomator2 is required but not available.\n'
                'If using AirtestIDE embedded Python, place py3.6-compatible wheels or extracted packages into one of:\n'
                '  <AirtestIDE>/poco/thirdparty, <AirtestIDE>/poco/_deps, <AirtestIDE>/poco/_vendor\n'
                'or set env POCO_THIRDPARTY to a folder containing the wheels.\n'
                'Typical wheels: uiautomator2, adbutils, apkutils2, requests, urllib3, certifi, idna, charset_normalizer, packaging, logzero.\n'
                'If you see Pillow core/version mismatch (e.g., _imaging built for 5.4.1), remove Pillow from thirdparty and use the IDE\'s built-in PIL,\n'
                'our driver provides a fallback for UnidentifiedImageError on old PIL.'
            )
            raise ImportError('uiautomator2 is required: {}\n{}'.format(_uia2_import_error, tips))

        self.screenshot_each_action = bool(screenshot_each_action)

        # Support Airtest device object to extract serial
        if device is not None and hasattr(device, 'serialno'):
            device_id = device.serialno
            warnings.warn('Using Airtest device object; consider passing device_id for better performance')

        # Connect to device
        try:
            d = u2.connect(device_id) if device_id else u2.connect()
        except Exception as e:  # pragma: no cover
            raise RuntimeError('Failed to connect to Android device: {}'.format(e))

        self.device = d

        if force_restart:
            try:
                self.device.uiautomator.stop()
                time.sleep(1)
                self.device.uiautomator.start()
                warnings.warn('force_restart: restarted UIAutomator2 daemon')
            except Exception as e:
                warnings.warn('force_restart failed: {}'.format(e))

        agent = AndroidUiautomator2Agent(self.device, use_airtest_input)
        super(AndroidUiautomator2Poco, self).__init__(agent, **options)

    def on_pre_action(self, action, ui, args):  # screenshot hook for Airtest logs
        if self.screenshot_each_action:
            try:
                from airtest.core.api import snapshot
                msg = repr(ui)
                if not isinstance(msg, six.text_type):
                    msg = msg.decode('utf-8')
                snapshot(msg='{}: {}'.format(action, msg))
            except Exception:
                warnings.warn('screenshot_each_action enabled but airtest not available')

    # Convenience helpers
    def get_device_info(self):
        return getattr(self.device, 'info', {})

    def refresh_hierarchy(self):
        if hasattr(self.agent.hierarchy, 'dumper') and hasattr(self.agent.hierarchy.dumper, 'invalidate_cache'):
            self.agent.hierarchy.dumper.invalidate_cache()

    def get_normalized_coordinates(self, x, y):
        # Prefer authoritative size from dumper
        w = h = None
        if hasattr(self.agent.hierarchy, 'dumper') and hasattr(self.agent.hierarchy.dumper, 'get_screen_size'):
            try:
                w, h = self.agent.hierarchy.dumper.get_screen_size()
            except Exception:
                w = h = None
        if not w or not h:
            try:
                ws = self.device.window_size()
                w, h = int(ws[0]), int(ws[1])
            except Exception:
                info = self.get_device_info()
                w, h = info.get('displayWidth', 1280), info.get('displayHeight', 720)
        return [float(x) / float(w), float(y) / float(h)]

    def get_pixel_coordinates(self, nx, ny):
        w = h = None
        if hasattr(self.agent.hierarchy, 'dumper') and hasattr(self.agent.hierarchy.dumper, 'get_screen_size'):
            try:
                w, h = self.agent.hierarchy.dumper.get_screen_size()
            except Exception:
                w = h = None
        if not w or not h:
            try:
                ws = self.device.window_size()
                w, h = int(ws[0]), int(ws[1])
            except Exception:
                info = self.get_device_info()
                w, h = info.get('displayWidth', 1280), info.get('displayHeight', 720)
        return [int(nx * float(w)), int(ny * float(h))]


class AndroidUiautomator2Helper(object):
    _instances = {}

    @classmethod
    def get_instance(cls, device_id=None):
        key = device_id or 'default'
        if key not in cls._instances:
            cls._instances[key] = AndroidUiautomator2Poco(device_id=device_id)
        return cls._instances[key]

    @classmethod
    def clear_instances(cls):  # pragma: no cover
        cls._instances.clear()
# Ensure thirdparty/site-packages comes before thirdparty/whl on sys.path
try:
    sp = _os.path.join('thirdparty', 'site-packages')
    wl = _os.path.join('thirdparty', 'whl')
    # stable copy to reorder
    paths = list(_sys.path)
    # remove whl entries
    whl_entries = [p for p in paths if wl in (p or '')]
    for p in whl_entries:
        try:
            _sys.path.remove(p)
        except Exception:
            pass
    # append them to the end
    for p in whl_entries:
        _sys.path.append(p)
except Exception:
    pass
