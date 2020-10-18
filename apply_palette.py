#!/usr/bin/env python3
# -*- mode: python; coding: utf-8 -*-
# By HarJIT in 2020. MIT/Expat licence.

import json, getopt, sys, re, os, glob, pprint
pprint.repr = json.dumps

with open("colour_replacements.json") as f:
    colour_replacements = json.load(f)

def _do_split(inpt, pattern):
    if isinstance(pattern, str):
        return inpt.split(pattern)
    return pattern.split(inpt)

def simulreplace(b, *args):
    if not args:
        return b
    frm, to = args[0]
    if isinstance(frm, tuple):
        if len(frm) == 1:
            frm, = frm
        else:
            return to.join(simulreplace(i, (frm[1:], to), *args[1:]) for i in _do_split(b, frm[0]))
    return to.join(simulreplace(i, *args[1:]) for i in _do_split(b, frm))

by_filename = {}
rby_filename = {}
for source, dests in colour_replacements.items():
    for dest, fns in dests.items():
        for fn in fns:
            by_filename.setdefault(fn, []).append((re.compile(source, flags=re.I), dest))
            rby_filename.setdefault(fn, []).append((dest, source))

palette = set()
for source, dests in colour_replacements.items():
    palette |= set(dests.keys())

print("Destination palette length: {:d}".format(len(palette)))
print("Source palette length: {:d}".format(len(colour_replacements)))

complex_first_level = set()

for source, dests in colour_replacements.items():
    if len(dests) > 1:
        complex_first_level |= {source}
    elif (source in palette) and (source not in dests):
        complex_first_level |= {source}
    elif "#ffdd67" in dests: # i.e. makes it look like Fitzpatrick base
        complex_first_level |= {source}

complex_second_level = set()

for source, dests in colour_replacements.items():
    if set(dests.keys()) & complex_first_level:
        # This would potentially include e.g. some participants in chain displacements
        complex_second_level |= {source}

complexes = complex_first_level | complex_second_level
simples = set(colour_replacements.keys()) ^ complexes

print("Simple cases: {:d}".format(len(simples)))
print("Directly complex cases: {:d}".format(len(complex_first_level)))
print("Indirectly complex cases: {:d}".format(len(complex_second_level)))
print("Anyhow complex cases: {:d}".format(len(complexes)))

def apply(mapping):
    for pn in glob.glob("**/*.svg", recursive=True):
        i = os.path.basename(pn)
        if i not in mapping:
            continue
        with open(pn) as f:
            b = borig = f.read()
        b = simulreplace(b, *mapping[i])
        if b != borig:
            print(pn)
            with open(pn, "w") as f:
                f.write(b)

opts, args = getopt.getopt(sys.argv[1:], "ard")
mode = "apply"
for opt, param in opts:
    if opt == "-a": # Apply palette.
        mode = "apply"
    elif opt == "-r": # Reverse apply palette.
        mode = "reverse"
    elif opt == "-d": # Dry run
        mode = "dummy"

if mode == "apply":
    print("Applying palette transform")
    apply(by_filename)
elif mode == "reverse":
    print("Reversing palette transform")
    apply(rby_filename)

print("Creating simplified palette file")
for source in colour_replacements.copy():
    if source in simples:
        colour_replacements[source] = next(iter(colour_replacements[source]))
with open("colour_replacements_oneway.json", "w") as f:
    f.write(pprint.pformat(colour_replacements))





