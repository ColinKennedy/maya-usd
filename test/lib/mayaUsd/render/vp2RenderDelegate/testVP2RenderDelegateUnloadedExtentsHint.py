#!/usr/bin/env mayapy
#
# Copyright 2026 Autodesk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import unittest

import fixturesUtils
import imageUtils
import mayaUtils
import testUtils

from maya import cmds
from pxr import UsdGeom

import mayaUsd.ufe

try:
    from PySide6.QtGui import QImage
except ImportError:
    from PySide2.QtGui import QImage


class testVP2RenderDelegateUnloadedExtentsHint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fixturesUtils.setUpClass(
            __file__, initializeStandalone=False, loadPlugin=False)
        cls._testDir = os.path.abspath('.')

    def setUp(self):
        cmds.file(new=True, force=True)
        mayaUtils.loadPlugin('mayaUsdPlugin')

    def _snapshot(self, name):
        path = os.path.join(self._testDir, name)
        imageUtils.snapshot(path, width=800, height=600)
        return path

    def _differentPixelCount(self, firstPath, secondPath):
        first = QImage(firstPath)
        second = QImage(secondPath)
        self.assertFalse(first.isNull())
        self.assertFalse(second.isNull())
        self.assertEqual(first.size(), second.size())

        count = 0
        for y in range(first.height()):
            for x in range(first.width()):
                if first.pixel(x, y) != second.pixel(x, y):
                    count += 1
        return count

    def _maximumRgbChannelDifference(self, firstPath, secondPath):
        first = QImage(firstPath)
        second = QImage(secondPath)
        self.assertFalse(first.isNull())
        self.assertFalse(second.isNull())
        self.assertEqual(first.size(), second.size())

        maximum = 0
        for y in range(first.height()):
            for x in range(first.width()):
                firstRgb = first.pixel(x, y)
                secondRgb = second.pixel(x, y)
                maximum = max(
                    maximum,
                    abs(((firstRgb >> 16) & 0xff) - ((secondRgb >> 16) & 0xff)),
                    abs(((firstRgb >> 8) & 0xff) - ((secondRgb >> 8) & 0xff)),
                    abs((firstRgb & 0xff) - (secondRgb & 0xff)))
        return maximum

    def testUnloadedModelDrawsAuthoredExtentsHint(self):
        usdFile = testUtils.getTestScene(
            'extentsHint', 'unloadedModel.usda')

        shape = cmds.createNode('mayaUsdProxyShape')
        cmds.setAttr(shape + '.loadPayloads', False)
        cmds.setAttr(shape + '.filePath', usdFile, type='string')

        shapePath = cmds.ls(shape, long=True)[0]
        stage = mayaUsd.ufe.getStage(shapePath)
        prim = stage.GetPrimAtPath('/model')
        extentsHint = UsdGeom.ModelAPI(prim).GetExtentsHintAttr()

        self.assertTrue(prim.IsModel())
        self.assertTrue(prim.HasPayload())
        self.assertFalse(prim.IsLoaded())
        self.assertTrue(extentsHint.HasAuthoredValueOpinion())

        panel = mayaUtils.activeModelPanel()
        self.assertIsNotNone(panel)
        cmds.modelEditor(panel, edit=True, rendererName='vp2Renderer')
        cmds.modelEditor(panel, edit=True, rendererOverrideName='')
        cmds.modelEditor(panel, edit=True, grid=False)
        cmds.modelEditor(panel, edit=True, displayAppearance='smoothShaded')
        cmds.setFocus(panel)
        cmds.viewFit(all=True, animate=False)
        cmds.select(clear=True)

        unloadedBefore = self._snapshot('unloadedExtentsHintBefore.png')

        cmds.setAttr(shape + '.visibility', False)
        hidden = self._snapshot('unloadedExtentsHintHidden.png')
        cmds.setAttr(shape + '.visibility', True)
        self.assertGreater(
            self._differentPixelCount(unloadedBefore, hidden), 100)
        self.assertGreater(
            self._maximumRgbChannelDifference(unloadedBefore, hidden), 20)

        cmds.select(shapePath + ',/model')
        unloadedSelected = self._snapshot('unloadedExtentsHintSelected.png')
        self.assertGreater(
            self._differentPixelCount(unloadedBefore, unloadedSelected), 100)
        cmds.select(clear=True)

        prim.Load()
        self.assertTrue(prim.IsLoaded())
        loaded = self._snapshot('unloadedExtentsHintLoaded.png')
        self.assertGreater(self._differentPixelCount(loaded, hidden), 100)

        prim.Unload()
        self.assertFalse(prim.IsLoaded())
        unloadedAfter = self._snapshot('unloadedExtentsHintAfter.png')
        self.assertEqual(
            self._differentPixelCount(unloadedBefore, unloadedAfter), 0)


if __name__ == '__main__':
    fixturesUtils.runTests(globals())
