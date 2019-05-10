#!/usr/bin/env python
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#
from dataclasses import dataclass
import os
import re
import sys
import yaml



class CalibBlock():
    dataTypes = []

    def __init__(self, blockName, yamlBlock):
        self.name = blockName
        self.data = {}

        for dt, block in yamlBlock.items():
            if dt not in self.dataTypes:
                print("Saw unknown dataType \"%s\" in block %s (expected %s)" %
                      (dt, blockName, ", ".join(self.dataTypes)))
                continue

            self.data[dt] = dataclass()

            # config[s]
            self.data[dt].configs = []
            if "config" in block:
                self.data[dt].configs.append(block["config"])
            if "configs" in block:
                for c in block["configs"]:
                    self.data[dt].configs.append(c)

            # visit[s]
            self.data[dt].visits = []
            if "visit" in block:
                self.data[dt].visits.append(block["visit"])
            if "visits" in block:
                for v in block["visits"]:
                    if isinstance(v, str):
                        mat = re.match(r"^(\d+)\.\.(\d+)(:\d+)?$", v)
                        if mat:
                            v1, v2, stride = mat.groups()
                            v1 = int(v1)
                            v2 = int(v2)
                            stride = 1 if stride is None else int(stride[1:])
                        else:
                            v1 = int(v)
                            v2 = v1
                            stride = 1

                        for v in range(v1, v2 + 1, stride):
                            self.data[dt].visits.append(v)
                    else:
                        self.data[dt].visits.append(v)


def executeBootstrap(dataDir, tmpCalib, detectorMaps, mode):
    detectorMaps = " ".join(detectorMaps)

    print(f"""\
ingestCalibs.py {dataDir} --output {dataDir}/{tmpCalib} --validity 1800 {detectorMaps} \
--create --mode link || return 1"""
          )


def executeBlock(block, mode, dataDir, tmpCalib, rerun, dataTypes=None, processes=1, verbose=False):
    """Execute a calibration block"""
    if dataTypes is None:
        dataTypes = CalibBlock.dataTypes

    if verbose:
        print(f"Processing block '{block.name}'", file=sys.stderr)
    for dt in dataTypes:
        if dt in block.data:
            configs = " ".join(block.data[dt].configs)
            visits = visitsToString(block.data[dt].visits)
            
            if dt == "bias":
                cmd = "constructBias.py"
            elif dt == "dark":
                cmd = "constructDark.py"
            elif dt == "flat":
                cmd = "constructFiberFlat.py"
            elif dt == "fiberTrace":
                cmd = "constructFiberTrace.py"
            else:
                continue

            print(f"""
{cmd} {dataDir} --calib {dataDir}/{tmpCalib} --rerun {rerun} %s \
                --id visit {visits} \
                --batch-type none -j {processes} || return 1""" % (f"--config {configs}" if configs else ""))

            ingestCalibs(dt, dataDir, rerun, tmpCalib, mode)
            if dt == "fiberTrace":
                ingestCalibs("DETECTORMAP", dataDir, rerun, tmpCalib, mode)


def ingestCalibs(dataType, dataDir, rerun, tmpCalib, mode):
    dataType = dataType.upper()
    print(f"""ingestCalibs.py {dataDir} --output {dataDir}/{tmpCalib} --validity 1800 \
                    {dataDir}/rerun/{rerun}/{dataType}/*.fits --mode {mode} || return 1""")


def processYaml(yamlFile):
    """Process the yaml file, returning the boostrap dict and processing blocks"""
    with open(yamlFile) as fd:
        content = yaml.load(fd, Loader=yaml.CSafeLoader)

    dataTypes = content["dataTypes"]
    CalibBlock.dataTypes = dataTypes

    calibBlocks = {}
    for blockName, yamlBlock in content["calibBlocks"].items():
        calibBlocks[blockName] = CalibBlock(blockName, yamlBlock)

    return content["bootstrap"], calibBlocks


def visitsToString(vals):
    """Convert a list of numbers into a string, merging consecutive values

    The string uses LSST command line dataId syntax, e.g. 12..20:2^100
    """
    if not vals:
        return ""

    vals = sorted(list(vals))

    def addPairToName(valName, val0, val1, stride=1):
        """Add a pair of values, val0 and val1, to the valName list"""
        sval0 = None
        if isinstance(val0, str) and isinstance(val1, str):
            if val0 != val1:
                pre = os.path.commonprefix([val0, val1])
                sval0 = val0[len(pre):]
                sval1 = val1[len(pre):]
        else:
            sval0 = str(val0)
            sval1 = str(val1)

        if sval0 is None:
            return ""

        if sval1 == sval0:
            dvn = str(val0)
        else:
            if val1 == val0 + stride:
                dvn = "%s^%s" % (sval0, sval1)
            else:
                dvn = "%s..%s" % (sval0, sval1)
                if stride > 1:
                    dvn += ":%d" % stride
        valName.append(dvn)
    #
    # Find the minimum spacing between values and interpret it as a stride
    #
    if len(vals) <= 1 or not isinstance(vals[0], int):
        stride = 1
        oval = None
    else:
        stride = vals[1] - vals[0]
        oval = vals[1]
    for val in vals[2:]:
        if val - oval < stride:
            stride = val - oval
        if stride == 1:
            break
        oval = val

    valName = []
    val0 = vals[0]
    val1 = val0
    for val in vals[1:]:
        if isinstance(val, int) and val == val1 + stride:
            val1 = val
        else:
            addPairToName(valName, val0, val1, stride=stride)
            val0 = val
            val1 = val0

    addPairToName(valName, val0, val1, stride)

    return "^".join(valName)
