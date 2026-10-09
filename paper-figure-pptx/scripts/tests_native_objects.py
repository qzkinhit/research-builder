#!/usr/bin/env python3
"""Standard-library regression tests; only temporary synthetic PPTX files change."""
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from xml.dom import minidom
from xml.sax.saxutils import escape
import zipfile

import native_objects as n

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jCXkAAAAASUVORK5CYII=')
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><path d="M0 0H8V8Z"/></svg>'


def shape(ident, name, text='', kind='rect', x=95250):
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{ident}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="95250"/><a:ext cx="952500" cy="190500"/></a:xfrm><a:prstGeom prst="{kind}"><a:avLst/></a:prstGeom></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr sz="1800" b="1"><a:latin typeface="Arial"/></a:rPr><a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp>'''


def fixture(path, interleaved=False, arrow=None, bad_target=False, duplicate_ids=False):
    first = shape(2, 'icon::part_a', 'Data α', x=95250)
    second = shape(2 if duplicate_ids else 3, 'icon::part_b', 'ABbest', x=1143000)
    middle = shape(4, 'short_arrow', kind='rightArrow', x=2190750)
    members = first + middle + second if interleaved else first + second + middle
    arrow_xml = f'<a:{arrow} type="triangle"/>' if arrow else ''
    connector = f'''<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="5" name="feedback"/><p:cNvCxnSpPr><a:stCxn id="2" idx="3"/><a:endCxn id="{'999' if bad_target else '3'}" idx="1"/></p:cNvCxnSpPr><p:nvPr/></p:nvCxnSpPr><p:spPr><a:xfrm><a:off x="1047750" y="190500"/><a:ext cx="95250" cy="1"/></a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom><a:ln w="19050">{arrow_xml}</a:ln></p:spPr></p:cxnSp>'''
    picture = '''<p:pic><p:nvPicPr><p:cNvPr id="6" name="heatmap"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="95250" y="952500"/><a:ext cx="952500" cy="952500"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'''
    slide = f'''<p:sld xmlns:p="{n.NS['p']}" xmlns:a="{n.NS['a']}" xmlns:r="{n.NS['r']}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{members}{connector}{picture}</p:spTree></p:cSld></p:sld>'''
    files = {
        '[Content_Types].xml': f'''<Types xmlns="{n.NS['ct']}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>''',
        '_rels/.rels': f'''<Relationships xmlns="{n.NS['rel']}"><Relationship Id="rId1" Type="{n.NS['r']}/officeDocument" Target="ppt/presentation.xml"/></Relationships>''',
        'ppt/presentation.xml': f'''<p:presentation xmlns:p="{n.NS['p']}" xmlns:r="{n.NS['r']}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="9144000" cy="4572000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>''',
        'ppt/_rels/presentation.xml.rels': f'''<Relationships xmlns="{n.NS['rel']}"><Relationship Id="rId1" Type="{n.NS['r']}/slide" Target="slides/slide1.xml"/></Relationships>''',
        'ppt/slides/slide1.xml': slide,
        'ppt/slides/_rels/slide1.xml.rels': f'''<Relationships xmlns="{n.NS['rel']}"><Relationship Id="rId1" Type="{n.IMAGE_REL}" Target="../media/image1.png"/></Relationships>''',
        'ppt/media/image1.png': PNG,
    }
    with zipfile.ZipFile(path, 'w') as archive:
        for key, value in files.items():
            archive.writestr(key, value)


def read_slide(path):
    with zipfile.ZipFile(path) as archive:
        return minidom.parseString(archive.read('ppt/slides/slide1.xml'))


def texts(doc):
    return ''.join(t.firstChild.data if t.firstChild else '' for t in n.descendants(doc, 'a', 't'))


def rewrite_slide(path, edit):
    _, files = n.read_pptx(path)
    doc = minidom.parseString(files['ppt/slides/slide1.xml'])
    edit(doc)
    files['ppt/slides/slide1.xml'] = doc.toxml(encoding='UTF-8')
    with zipfile.ZipFile(path, 'w') as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)


def wrap_compatibility(doc, shape, fallback_id=None):
    doc.documentElement.setAttribute('xmlns:mc', n.NS['mc'])
    doc.documentElement.setAttribute('xmlns:a14', 'http://schemas.microsoft.com/office/drawing/2010/main')
    alternate = n.make(doc, 'mc', 'AlternateContent')
    choice = n.make(doc, 'mc', 'Choice', Requires='a14')
    fallback = n.make(doc, 'mc', 'Fallback')
    replacement = shape.cloneNode(deep=True)
    if fallback_id is not None:
        n.cnvpr(replacement).setAttribute('id', str(fallback_id))
    shape.parentNode.insertBefore(alternate, shape)
    alternate.appendChild(choice)
    alternate.appendChild(fallback)
    choice.appendChild(shape)
    fallback.appendChild(replacement)
    return alternate


def wrap_group(doc, shape, ident, name):
    group = n.make(doc, 'p', 'grpSp')
    nonvisual = n.make(doc, 'p', 'nvGrpSpPr')
    nonvisual.appendChild(n.make(doc, 'p', 'cNvPr', id=ident, name=name))
    nonvisual.appendChild(n.make(doc, 'p', 'cNvGrpSpPr'))
    nonvisual.appendChild(n.make(doc, 'p', 'nvPr'))
    group.appendChild(nonvisual)
    props, transform = n.make(doc, 'p', 'grpSpPr'), n.make(doc, 'a', 'xfrm')
    for kind, attrs in [('off', {'x':95250, 'y':190500}),
                        ('ext', {'cx':4762500, 'cy':2381250}),
                        ('chOff', {'x':95250, 'y':190500}),
                        ('chExt', {'cx':4762500, 'cy':2381250})]:
        transform.appendChild(n.make(doc, 'a', kind, **attrs))
    props.appendChild(transform)
    group.appendChild(props)
    shape.parentNode.insertBefore(group, shape)
    group.appendChild(shape)
    return group, transform


class NativeObjectsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source, self.output = self.root / 'source.pptx', self.root / 'result.pptx'
        fixture(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def map_file(self, name, content):
        path = self.root / name
        path.write_text(json.dumps(content))
        return path

    def test_group_preserves_text_coordinates_ids_and_is_idempotent(self):
        before = read_slide(self.source)
        before_shapes = {n.object_name(s): s.toxml() for s in n.descendants(before, 'p', 'sp')}
        result = n.package(self.source, self.output)
        after = read_slide(self.output)
        self.assertTrue(result['passed'])
        self.assertEqual(texts(before), texts(after))
        self.assertEqual(before_shapes, {n.object_name(s): s.toxml() for s in n.descendants(after, 'p', 'sp')})
        group = n.descendants(after, 'p', 'grpSp')[0]
        xf = n.direct(n.direct(group, 'p', 'grpSpPr'), 'a', 'xfrm')
        for a, b, keys in [('off', 'chOff', ['x', 'y']), ('ext', 'chExt', ['cx', 'cy'])]:
            for key in keys:
                self.assertEqual(n.direct(xf, 'a', a).getAttribute(key), n.direct(xf, 'a', b).getAttribute(key))
        second = self.root / 'second.pptx'
        result2 = n.package(self.output, second)
        self.assertEqual(result2['created_groups'], [])
        self.assertEqual(len(n.descendants(read_slide(second), 'p', 'grpSp')), 1)

    def test_svg_keeps_fallback_and_svg_bytes(self):
        (self.root / 'plot.svg').write_bytes(SVG)
        svg_map = self.map_file('svg.json', {'heatmap': 'plot.svg'})
        result = n.package(self.source, self.output, svg_map_path=svg_map)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.read('ppt/media/image1.png'), PNG)
            self.assertEqual(archive.read(result['embedded_svgs'][0]['media']), SVG)
        self.assertEqual(len(n.descendants(read_slide(self.output), 'p', 'pic')), 1)
        self.assertEqual(len(n.descendants(read_slide(self.output), 'asvg', 'svgBlip')), 1)
        second = self.root / 'second.pptx'
        n.package(self.output, second, svg_map_path=svg_map)
        self.assertEqual(len(n.descendants(read_slide(second), 'asvg', 'svgBlip')), 1)

    def test_routes_remain_native_connector_and_keep_arrow_and_refs(self):
        fixture(self.source, arrow='tailEnd')
        route = self.map_file('route.json', {'feedback': {'points': [[110,20],[120,20],[120,50],[180,50]]}})
        result = n.package(self.source, self.output, route_map_path=route)
        doc = read_slide(self.output)
        connectors = n.descendants(doc, 'p', 'cxnSp')
        self.assertEqual(len(connectors), 1)
        self.assertEqual(n.cnvpr(connectors[0]).getAttribute('id'), '5')
        self.assertEqual(n.descendants(connectors[0], 'a', 'prstGeom')[0].getAttribute('prst'), 'bentConnector3')
        self.assertEqual(n.descendants(connectors[0], 'a', 'tailEnd')[0].getAttribute('type'), 'triangle')
        self.assertEqual(n.descendants(connectors[0], 'a', 'stCxn')[0].getAttribute('id'), '2')
        self.assertLess(result['routed_connectors'][0]['max_vertex_error_px'], .01)
        self.assertEqual(len(n.descendants(doc, 'p', 'sp')), 3)

    def test_vertical_route_optional_anchor_is_native_and_repeatable(self):
        route = self.map_file('route.json', {'feedback': {'points': [[110,20],[110,40],[140,40],[140,50]], 'start_anchor': {'side': 'bottom'}}})
        result = n.package(self.source, self.output, route_map_path=route)
        self.assertEqual(result['routed_connectors'][0]['rotation_degrees'], 90)
        self.assertEqual(len(n.descendants(read_slide(self.output), 'p', 'cxnSp')), 1)
        second = self.root / 'second.pptx'
        n.package(self.output, second, route_map_path=route)
        self.assertEqual(sum(n.object_name(s).endswith('__route_start_anchor') for s in n.descendants(read_slide(second), 'p', 'sp')), 1)

    def test_arrowless_line_and_native_block_arrow_are_legal(self):
        result = n.package(self.source, self.output)
        self.assertTrue(result['passed'])
        self.assertTrue(any('no explicit arrow' in warning for warning in result['warnings']))
        self.assertTrue(result['slides'][0]['native_block_arrows'])
        self.assertFalse(any('triangle' in warning for warning in result['warnings']))
        self.assertEqual(result['errors'], [])
        restricted = self.root / 'restricted.pptx'
        with self.assertRaisesRegex(ValueError, 'Audit failed'):
            n.package(self.source, restricted, require_end_arrows=True)
        self.assertFalse(restricted.exists())
        fixture(self.source, arrow='headEnd')
        n.package(self.source, restricted, require_end_arrows=True)

    def test_overwrite_requires_opt_in_and_failures_keep_existing_bytes(self):
        original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'In-place'):
            n.package(self.source, self.source)
        self.assertEqual(self.source.read_bytes(), original)
        self.output.write_bytes(b'old output')
        with self.assertRaises(FileExistsError):
            n.package(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b'old output')
        with self.assertRaisesRegex(ValueError, 'Audit failed'):
            n.package(self.source, self.output, expected_ratio=3, overwrite=True)
        self.assertEqual(self.output.read_bytes(), b'old output')
        self.assertFalse(list(self.root.glob('.*.tmp')))
        n.package(self.source, self.output, overwrite=True)
        with zipfile.ZipFile(self.output) as archive:
            self.assertIsNone(archive.testzip())

    def test_interleaved_groups_are_rejected_by_default(self):
        fixture(self.source, interleaved=True)
        with self.assertRaisesRegex(ValueError, 'interleaved'):
            n.package(self.source, self.output)
        self.assertFalse(self.output.exists())
        result = n.package(self.source, self.output, allow_interleaved_groups=True)
        self.assertTrue(any('z-order' in warning for warning in result['warnings']))

    def test_compatibility_and_unknown_drawings_are_group_order_barriers(self):
        for kind in ['compatibility', 'unknown']:
            with self.subTest(kind=kind):
                fixture(self.source, interleaved=True)
                def edit(doc):
                    middle = next(s for s in n.descendants(doc, 'p', 'sp')
                                  if n.object_name(s) == 'short_arrow')
                    if kind == 'compatibility':
                        wrap_compatibility(doc, middle, fallback_id=7)
                    else:
                        wrapper = doc.createElementNS('urn:test:drawing', 'x:drawing')
                        wrapper.setAttribute('xmlns:x', 'urn:test:drawing')
                        middle.parentNode.insertBefore(wrapper, middle)
                        wrapper.appendChild(middle)
                rewrite_slide(self.source, edit)
                original = self.source.read_bytes()
                self.output.write_bytes(b'previous output')
                with self.assertRaisesRegex(ValueError, 'interleaved'):
                    n.package(self.source, self.output, overwrite=True)
                self.assertEqual(self.source.read_bytes(), original)
                self.assertEqual(self.output.read_bytes(), b'previous output')
                self.assertFalse(list(self.root.glob('.*.tmp')))

    def test_routes_reject_transformed_ancestors_before_publishing(self):
        route = self.map_file('routes.json', {'feedback': {
            'points': [[110,20],[140,20],[140,60]], 'detach': True}})
        for change in ['scale', 'translation', 'rotation', 'flipH', 'flipV']:
            with self.subTest(change=change):
                fixture(self.source)
                def edit(doc):
                    connector = n.descendants(doc, 'p', 'cxnSp')[0]
                    inner, _ = wrap_group(doc, connector, 10, 'identity_inner')
                    _, transform = wrap_group(doc, inner, 11, 'transformed_outer')
                    if change == 'scale':
                        n.direct(transform, 'a', 'ext').setAttribute('cx', '9525000')
                    elif change == 'translation':
                        n.direct(transform, 'a', 'off').setAttribute('x', '190500')
                    elif change == 'rotation':
                        transform.setAttribute('rot', '5400000')
                    else:
                        transform.setAttribute(change, '1')
                rewrite_slide(self.source, edit)
                original = self.source.read_bytes()
                self.output.write_bytes(b'previous output')
                with self.assertRaisesRegex(ValueError, 'ancestor group transform'):
                    n.package(self.source, self.output, route_map_path=route, overwrite=True)
                self.assertEqual(self.source.read_bytes(), original)
                self.assertEqual(self.output.read_bytes(), b'previous output')
                absent = self.root / 'never-written.pptx'
                with self.assertRaisesRegex(ValueError, 'ancestor group transform'):
                    n.package(self.source, absent, route_map_path=route)
                self.assertFalse(absent.exists())
                self.assertFalse(list(self.root.glob('.*.tmp')))

    def test_routes_in_identity_groups_preserve_slide_coordinates(self):
        def edit(doc):
            connector = n.descendants(doc, 'p', 'cxnSp')[0]
            inner, _ = wrap_group(doc, connector, 10, 'identity_inner')
            wrap_group(doc, inner, 11, 'identity_outer')
        rewrite_slide(self.source, edit)
        before = read_slide(self.source)
        transforms = [n.direct(g, 'p', 'grpSpPr').toxml() for g in n.descendants(before, 'p', 'grpSp')]
        route = self.map_file('routes.json', {'feedback': {
            'points': [[110,20],[140,20],[140,60]], 'detach': True}})
        result = n.package(self.source, self.output, route_map_path=route)
        self.assertTrue(result['passed'])
        event = result['routed_connectors'][0]
        self.assertEqual(event['requested_points_px'], event['rendered_points_px'])
        existing_groups = [g for g in n.descendants(read_slide(self.output), 'p', 'grpSp')
                           if n.object_name(g).startswith('identity_')]
        self.assertEqual(transforms, [n.direct(g, 'p', 'grpSpPr').toxml() for g in existing_groups])

    def test_mutually_exclusive_compatibility_ids_are_allowed_and_preserved(self):
        def edit(doc):
            picture = n.descendants(doc, 'p', 'pic')[0]
            wrap_compatibility(doc, picture)
        rewrite_slide(self.source, edit)
        original = n.descendants(read_slide(self.source), 'mc', 'AlternateContent')[0].toxml()
        result = n.package(self.source, self.output)
        self.assertTrue(result['passed'])
        after = n.descendants(read_slide(self.output), 'mc', 'AlternateContent')[0]
        self.assertEqual(after.toxml(), original)
        self.assertEqual([n.cnvpr(p).getAttribute('id') for p in n.descendants(after, 'p', 'pic')], ['6', '6'])

    def test_coexisting_compatibility_duplicate_ids_are_still_rejected(self):
        for conflict in ['same_branch', 'outside', 'separate_wrapper']:
            with self.subTest(conflict=conflict):
                fixture(self.source)
                def edit(doc):
                    picture = n.descendants(doc, 'p', 'pic')[0]
                    extra = picture.cloneNode(deep=True)
                    alternate = wrap_compatibility(doc, picture)
                    if conflict == 'same_branch':
                        n.direct(alternate, 'mc', 'Choice').appendChild(extra)
                    else:
                        alternate.parentNode.appendChild(extra)
                        if conflict == 'separate_wrapper':
                            wrap_compatibility(doc, extra)
                rewrite_slide(self.source, edit)
                original = self.source.read_bytes()
                self.output.write_bytes(b'previous output')
                with self.assertRaisesRegex(ValueError, 'duplicate object IDs'):
                    n.package(self.source, self.output, overwrite=True)
                self.assertEqual(self.source.read_bytes(), original)
                self.assertEqual(self.output.read_bytes(), b'previous output')

    def test_unmatched_maps_fail_without_artifact(self):
        (self.root / 'plot.svg').write_bytes(SVG)
        bad_svg = self.map_file('svg.json', {'missing': 'plot.svg'})
        bad_route = self.map_file('routes.json', {'missing': [[10,10],[20,10],[20,20]]})
        bad_sub = self.map_file('subs.json', {'Qbest': {'base':'Q', 'subscript':'best'}})
        for key, value in [('svg_map_path', bad_svg), ('route_map_path', bad_route), ('subscript_map_path', bad_sub)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'did not match'):
                n.package(self.source, self.output, **{key:value})
            self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.*.tmp')))

    def test_audit_errors_are_rejected_before_writing(self):
        for options in [{'bad_target':True}, {'duplicate_ids':True}]:
            fixture(self.source, **options)
            with self.assertRaisesRegex(ValueError, 'Audit failed'):
                n.package(self.source, self.output)
            self.assertFalse(self.output.exists())

    def test_generic_subscripts_keep_text_and_multicharacter_base(self):
        submap = self.map_file('subs.json', {'ABbest': {'base':'AB', 'subscript':'best'}})
        before = read_slide(self.source)
        result = n.package(self.source, self.output, subscript_map_path=submap)
        doc = read_slide(self.output)
        self.assertEqual(texts(doc), texts(before))
        self.assertEqual(len(result['formatted_subscripts']), 1)
        runs = n.descendants(doc, 'a', 'r')
        best = next(r for r in runs if n.direct(r, 'a', 't').firstChild.data == 'best')
        self.assertEqual(n.direct(best, 'a', 'rPr').getAttribute('baseline'), '-25000')
        self.assertEqual(n.direct(best, 'a', 'rPr').getAttribute('sz'), '1260')
        self.assertEqual(n.direct(best, 'a', 'rPr').getAttribute('b'), '1')

    def test_slide_selectors_follow_presentation_order(self):
        _, files = n.read_pptx(self.source)
        files['ppt/slides/slide2.xml'] = files['ppt/slides/slide1.xml']
        files['ppt/slides/_rels/slide2.xml.rels'] = files['ppt/slides/_rels/slide1.xml.rels']
        files['ppt/presentation.xml'] = files['ppt/presentation.xml'].replace(
            b'<p:sldId id="256" r:id="rId1"/>',
            b'<p:sldId id="257" r:id="rId2"/><p:sldId id="256" r:id="rId1"/>')
        rel = f'<Relationship Id="rId2" Type="{n.NS["r"]}/slide" Target="slides/slide2.xml"/>'
        files['ppt/_rels/presentation.xml.rels'] = files['ppt/_rels/presentation.xml.rels'].replace(
            b'</Relationships>', rel.encode() + b'</Relationships>')
        with zipfile.ZipFile(self.source, 'w') as archive:
            for name, payload in files.items():
                archive.writestr(name, payload)
        route = self.map_file('route.json', [{'name':'feedback', 'slide':1,
            'points':[[110,20],[120,20],[120,50]]}])
        result = n.package(self.source, self.output, route_map_path=route)
        self.assertEqual(result['slides'][0]['part'], 'ppt/slides/slide2.xml')
        self.assertEqual(result['slides'][0]['connector_details'][0]['geometry'], 'bentConnector2')
        self.assertEqual(result['slides'][1]['connector_details'][0]['geometry'], 'line')

    def test_cli_audit_only_is_read_only(self):
        original = self.source.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = n.main([str(self.source), '--audit-only', '--strict'])
            failure = n.main([str(self.source), '--audit-only', '--strict', '--require-end-arrows'])
        self.assertEqual(code, 0)
        self.assertEqual(failure, 2)
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
