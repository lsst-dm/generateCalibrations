# generateCalibrations
An experimental package for generating calibrations given a description of which visits to use for what

For example,
    setup -r .
    generateCalibs.py policy/LAM/test.yaml --dataDir /Users/rhl/Data/LAM -j 8
will generate the sh commands needed to generate the calibrations for a set of Prime Focus Spectrograph (PFS)
data taken in Marseille, at LAM.  If you're more interested in LSST, try e.g.
     generateCalibs.py policy/AuxTel/tucson.yaml --dataDir /project/shared/auxTel --block 2019-03-08
