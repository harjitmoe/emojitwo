#!/usr/bin/env python3
# -*- mode: python; coding: utf-8 -*-
# By HarJIT in 2020. MIT/Expat licence.

import os, xml.dom.minidom, unicodedata, shutil, glob, re, collections, itertools
from PIL import Image

colours = collections.defaultdict(int)

hexcolre = re.compile("(?i)#[0123456789abcdef]{6}")

def getcols(b):
    offset = 0
    while 1:
        match = hexcolre.search(b, offset)
        if not match:
            break
        yield match.group(0).casefold()
        offset = match.end(0)

def unpack(hexcol):
    assert hexcolre.match(hexcol)
    red = int(hexcol[1:3], 16)
    green = int(hexcol[3:5], 16)
    blue = int(hexcol[5:7], 16)
    return red, green, blue

def distance(hexcol, hexcol2):
    red, green, blue = unpack(hexcol)
    red2, green2, blue2 = unpack(hexcol2)
    # Standards and monitor settings vary but, as a rule of thumb, #00FF00 is twice the
    # effective brightness of #FF0000, which is in turn three times that of #0000FF.
    distance = ((red - red2) ** 2) + (((green - green2) * 2) ** 2) + (((blue - blue2) / 3) ** 2)
    distance **= 0.5
    return distance

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

# Obtain the complete set of colours used anywhere in EmojiTwo
print("Scanning")
togethers = []
for pn in glob.glob("**/*.svg", recursive=True):
    i = os.path.basename(pn)
    if "draft" in i.casefold():
        continue
    with open(pn) as f:
        b = f.read()
    togethers.append(set(getcols(b)))
    for i in togethers[-1]:
        colours[i] += 1

# Start with every colour paired to every other colour
colours_dict = dict(zip(list(colours.keys()), [None] * len(colours)))
for i in colours_dict:
    # Can't just do this in the list repetition expression above since then we just end up with
    #   1196 references to the same set object
    colours_dict[i] = set(colours.keys())

# Find the smallest threshold distance for quantisation which will leave every colour paired to at
#   least one other colour (prior to elimination of contrastive pairs)
print("Calibrating")
maxmindist = 0
for col, targets in colours_dict.items():
    mindist = 577
    ref = None
    for target in targets:
        if target == col:
            # No point eliminating these first, they'll go with the contrastive pairs.
            # Just ignore them
            continue
        if (dist := distance(col, target)) < mindist:
            mindist = dist
            ref = target
    if mindist > 45:
        print(col, ref)
    if mindist > maxmindist:
        maxmindist = mindist

# Remove colour pairings which are used contrastively, i.e. within a single glyph.
#   This might in theory leave some colours unpaired.
print("Contrasting")
for together in togethers:
    for i in together:
        for j in together:
            if j in colours_dict[i]:
                colours_dict[i] ^= {j}

# Constrain pairings to that quantisation threshold
print("Constraining")
for i in colours_dict:
    for j in frozenset(colours_dict[i]):
        if distance(i, j) > maxmindist:
            colours_dict[i] ^= {j}

# Prune colours, least common first
print("Pruning")
prunable = sorted(list(colours.keys()), key=colours.__getitem__)
# don't mess with (base) skin tones
protected = {"#ffdd67", "#ffe1bd", "#fed0ac", "#d6a57c", "#b47d56", "#8a6859"}
for i in protected:
    prunable.remove(i)
pruned = {}
rpruned = collections.defaultdict(set)
while (len(prunable) + len(protected)) > 128: # reminder: we're rendering down from 1196
    if not prunable:
        raise ValueError("cannot shrink the palette this small")
    available = set(i for i in colours_dict[prunable[0]] if i in prunable)
    # Further refine to colours which aren't already merged with colours which are not mergeable
    #   with prunable[0] (i.e. are potentially used contrastively somewhere)
    truly_available = set()
    for i in available:
        if i in rpruned:
            for j in rpruned[i]:
                if prunable[0] not in colours_dict[j]:
                    break
            else: # for…else, i.e. did not encounter break
                truly_available |= {i}
        else:
            truly_available |= {i}
    # If prunable[0] cannot be merged into anything, protect it.
    if not truly_available:
        protected |= {prunable[0]}
        prunable.pop(0)
    else:
        destination = sorted(truly_available, key=lambda i: distance(prunable[0], i))[0]
        pruned[prunable[0]] = destination
        rpruned[destination] |= {prunable[0]}
        prunable.pop(0)

print("Previewing")
pal = sorted(list(itertools.chain(protected, prunable)))
palout = Image.new("RGB", (16, 8))
for n, i in enumerate(pal):
    x, y = n % 16, n // 16
    r, g, b = unpack(i)
    palout.putpixel((x, y), (r, g, b))
palout.save("emojitwopal.png")

print("Enforcing")
# Note that using the pruned dict for everything isn't necessarily good: an individual emoji might
#   not use two colours contrastively just because they're used contrastively *somewhere*, so it
#   is often possible to do better than that.
for pn in glob.glob("**/*.svg", recursive=True):
    i = os.path.basename(pn)
    if "draft" in i.casefold():
        continue
    with open(pn) as f:
        b = borig = f.read()
    cols = set(list(getcols(b)))
    maps = {}
    rmaps = collections.defaultdict(set)
    for col in cols:
        mapped = sorted(pal, key = lambda j: distance(j, col))[0]
        maps[col] = mapped
        rmaps[mapped] |= {col}
    while len(rmaps) < len(maps): # While we have a collision
        for mapped in rmaps:
            if len(rmaps[mapped]) < 2:
                continue
            options = []
            for col in rmaps[mapped]:
                alternative = sorted([i for i in pal if i not in rmaps],
                    key = lambda j: distance(j, col))[0]
                options.append((col, alternative))
            col, alternative = sorted(options, key=lambda a: distance(a[0], a[1]))[0]
            maps[col] = alternative
            rmaps[alternative] |= {col}
            rmaps[mapped] ^= {col}
            break # i.e. re-start for loop with modified rmaps dict
    replacements = []
    for frm, to in maps.items():
        replacements.append((re.compile(frm, flags=re.I), to))
    b = simulreplace(b, *replacements)
    if b != borig:
        print(pn)
        with open(pn, "w") as f:
            f.write(b)




