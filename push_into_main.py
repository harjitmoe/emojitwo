#!/usr/bin/env python3
# -*- mode: python; coding: utf-8 -*-
# By HarJIT in 2020. MIT/Expat licence.

import os, shutil, glob

for pn in glob.glob("**/*.svg", recursive=True):
    i = os.path.basename(pn)
    if "draft" in i.casefold():
        continue
    print(i)
    if "-BW" in i:
        shutil.copy(pn, os.path.join("..", "emojitwo", "svg_bw", i.replace("-BW", "")))
    else:
        shutil.copy(pn, os.path.join("..", "emojitwo", "svg", i))







