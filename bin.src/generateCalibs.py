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
import argparse
from dataclasses import dataclass
import os
import re
import sys
import yaml
import lsst.generateCalibrations.parseYaml as genCalibs

parser = argparse.ArgumentParser(description="""
Process a yaml file and generate the desired calibrations
""")

parser.add_argument('specFile', type=str, help="Name of file specifying the work")
parser.add_argument('--bootstrap', action="store_true", help="Bootstrap the calibrations?")
parser.add_argument('--blocks', type=str, nargs="+", help="Blocks to execute")
parser.add_argument('--calib', type=str, help="Name of output calibration directory", default="CALIB")
parser.add_argument('--dataDir', type=str, help="Source of data")
parser.add_argument('--dataTypes', type=str, nargs="+", help="Types of data to process")
parser.add_argument('--force', action="store_true", help="Continue in the face of problems", default=False)
parser.add_argument("-j", "--processes", type=int, default=1, help="Number of processes to use")
parser.add_argument("--mode", choices=["move", "copy", "link", "skip"], default="link",
                    help="How to move files into calibration directory")
parser.add_argument('--rerun', type=str, help="Name of rerun to use for calib processing")
parser.add_argument('--tmpCalib', type=str,
                    help="Name of calib directory to be used during processing", default="TMP_CALIB")
parser.add_argument('--verbose', action="store_true", help="How chatty should I be?", default=False)

args = parser.parse_args()

force = args.force
bootstrap, calibBlocks = genCalibs.processYaml(args.specFile)
blockNames = calibBlocks.keys() if args.blocks is None else args.blocks
calib = args.calib
dataDir = args.dataDir
dataTypes = args.dataTypes
mode = args.mode
processes = args.processes
rerun = args.rerun
tmpCalib = args.tmpCalib
verbose = args.verbose

if dataDir is None:
    raise SystemExit("Please specify --dataDir and try again")
if not os.path.exists(dataDir):
    print(f"Warning: {dataDir} doesn't exist", file=sys.stdout)
    if not force:
        sys.exit(1)    
#
# Bootstrap the calibrations
#
if args.bootstrap:
    bootstrapDir = bootstrap["dirName"]
    if not os.path.isabs(bootstrapDir):
        bootstrapDir = os.path.join(dataDir, bootstrapDir)
    if verbose:
        print("Reading bootstrap files from %s" % (bootstrapDir))

    detectorMaps = []
    for arm in bootstrap["arms"]:
        detectorMaps.append(os.path.join(bootstrapDir, bootstrap["detectorMapFmt"] % arm))

    genCalibs.executeBootstrap(dataDir, tmpCalib, detectorMaps, mode)
#
# Process the main blocks
#
for blockName in blockNames:
    if blockName not in calibBlocks:
        print(f"Unrecognised block: '{blockName}'%s" % (" ignoring" if force else ""),
              file=sys.stderr)
        if verbose:
            print(f"Possible blocks are {list(calibBlocks.keys())}")
        if force:
            continue
        else:
            sys.exit(1)

    genCalibs.executeBlock(calibBlocks[blockName], mode, dataDir, tmpCalib, rerun, dataTypes,
                           processes=processes, verbose=verbose)
