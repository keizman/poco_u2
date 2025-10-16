# coding=utf-8
"""
Verification script (mock-based) for UIAutomator1→Poco data compatibility
using the new UIAutomator2-backed implementation in tmp.poco_v1.

This script does NOT require a real device. It mocks the device.info and
device.dump_hierarchy() return to validate that:
 - Dump shape matches Poco v1 expectations (name/payload/children)
 - 'package' attribute is preserved in payload for all nodes
 - Visibility filtering is bypassed (nodes with visible-to-user="false" remain)
 - Normalized coordinates (pos/size/bounds) are computed correctly

Run:
  python -m tmp.poco_v1.tests.verify_uia2_backcompat_mock
"""
from __future__ import print_function

import json
from xml.sax.saxutils import escape

from tmp.poco_v1.drivers.android.uiautomation2 import UIAutomator2Dumper


class FakeDevice(object):
    def __init__(self, xml, width=1080, height=1920):
        self._xml = xml
        self.info = {'displayWidth': width, 'displayHeight': height}

    def dump_hierarchy(self):
        return self._xml


def build_sample_xml():
    # Two nodes: one visible button, one video view marked not visible-to-user
    nodes = []
    nodes.append(
        '<node index="0" text="Play" resource-id="com.app:id/play" '
        'class="android.widget.Button" package="com.app" content-desc="Play Button" '
        'bounds="[10,20][210,120]" clickable="true" enabled="true" visible-to-user="true" />'
    )
    nodes.append(
        '<node index="1" text="" resource-id="com.app:id/player" '
        'class="com.app.VideoView" package="com.app" '
        'bounds="[0,300][1080,1300]" clickable="false" enabled="true" visible-to-user="false" />'
    )
    return '<hierarchy>{}</hierarchy>'.format(''.join(nodes))


def count_nodes_with_package(dump_dict):
    def _rec(n):
        if not isinstance(n, dict):
            return 0
        cnt = 1 if n.get('payload', {}).get('package') else 0
        for c in n.get('children', []) or []:
            cnt += _rec(c)
        return cnt
    return _rec(dump_dict)


def count_total_nodes(dump_dict):
    def _rec(n):
        if not isinstance(n, dict):
            return 0
        cnt = 1
        for c in n.get('children', []) or []:
            cnt += _rec(c)
        return cnt
    return _rec(dump_dict)


def run():
    xml = build_sample_xml()
    dev = FakeDevice(xml, 1080, 1920)
    dumper = UIAutomator2Dumper(dev)
    dump_data = dumper.dumpHierarchy()

    assert isinstance(dump_data, dict), 'dump should return a dict'
    assert 'payload' in dump_data, 'root must contain payload'
    assert 'children' in dump_data, 'root must contain children'
    children = dump_data['children']
    assert isinstance(children, list) and len(children) >= 2, 'two child nodes expected'

    # Ensure package attribute preserved on children
    pkg_count = count_nodes_with_package(dump_data)
    total = count_total_nodes(dump_data)
    print('Total nodes:', total)
    print('Nodes with package:', pkg_count)
    assert pkg_count >= 2, 'package attribute should be present on child nodes'

    # Find the video view (not visible-to-user) should still be present
    classes = []
    for c in children:
        classes.append(c.get('payload', {}).get('type'))
    print('Top-level child classes:', classes)
    assert any('VideoView' in (x or '') for x in classes), 'VideoView node should be present despite not visible-to-user'

    # Validate normalized bounds on the button
    button = next((c for c in children if c.get('payload', {}).get('text') == 'Play'), None)
    assert button is not None, 'Play button node must exist'
    b_payload = button['payload']
    # bounds: [10,20][210,120] on 1080x1920
    expected_bounds = [10.0/1080, 20.0/1920, 210.0/1080, 120.0/1920]
    assert all(abs(a - b) < 1e-6 for a, b in zip(b_payload.get('bounds', []), expected_bounds)), 'normalized bounds mismatch'

    # Output readable JSON for manual inspection
    print('\nSample dump (truncated):')
    print(json.dumps({'children': dump_data.get('children', [])[:1]}, indent=2))
    print('\nSUCCESS: Mock verification passed.')
    return True


if __name__ == '__main__':
    ok = run()
    raise SystemExit(0 if ok else 1)

