#!/usr/bin/env python3
# -*- mode: python; coding: utf-8 -*-
# By HarJIT in 2020. MIT/Expat licence.

import ast, os, xml.dom.minidom, unicodedata, shutil, glob

cldrnames = {}
_document = xml.dom.minidom.parse("CLDR/annotations/en.xml")
for _i in _document.getElementsByTagName("annotation"):
    if _i.hasAttribute("type") and _i.getAttribute("type") == "tts":
        cldrnames[_i.getAttribute("cp")] = _i.firstChild.wholeText
_document = xml.dom.minidom.parse("CLDR/annotationsDerived/en.xml")
for _i in _document.getElementsByTagName("annotation"):
    if _i.hasAttribute("type") and _i.getAttribute("type") == "tts":
        cldrnames[_i.getAttribute("cp")] = _i.firstChild.wholeText
rcldrnames = dict(zip(cldrnames.values(), (i.casefold() for i in cldrnames.keys())))
for i in list(cldrnames.keys())[:]:
    cldrnames[i.replace("\u200D", "")] = cldrnames[i]

def get_cldrname(ucs):
    if ucs in cldrnames:
        return cldrnames[ucs]
    if len(ucs) == 1:
        altname = unicodedata.name(ucs, None)
        if altname:
            altname = altname.title()
            if altname.casefold() in rcldrnames:
                altname = "Unicode " + altname
            return altname
    if len(ucs) > 1:
        n = [get_cldrname(i) for i in ucs]
        if None not in n:
            ret = ", ".join(n)
            if ret.endswith("skin tone"):
                ret = ":".join(ret.rsplit(",", 1))
            return ret
    return None

dat = ast.literal_eval(open("BlendedEmojiData.txt").read())
sumps = {
    # Properties: ([presents…], [absents…])
    "ID.DoCoMo": ([], []),
    "ID.au": ([], []),
    "ID.SoftBank": ([], []),
    "SBCS.Webdings": ([], []),
    "SBCS.Wingdings_1": ([], []),
    "SBCS.Wingdings_2": ([], []),
    "SBCS.Wingdings_3": ([], []),
    "SBCS.ZapfDingbats": ([], []),
    "JIS.ARIB": ([], []),
    "JIS.2004": ([], []),
    "MBCS_EUC.Wansung": ([], []),
    "MBCS_EUC.KPS": ([], []),
}
# May be lower than the sum due to overlap between sets
total_present = []
total_wanted = []

exists = [os.path.basename(pn) for pn in glob.glob("**/*.svg", recursive=True)]

for i in dat:
    for key in ("UCS.Standard", "UCS.PUA.SoftBank", "UCS.PUA.Google", "UCS.PUA.au.web", "UCS.PUA.DoCoMo"):
        if key in dat[i]:
            j = dat[i][key].replace("\u200d", "").replace("\ufe0f", "")
            k = "{}.svg".format("-".join("{:04x}".format(ord(m)) for m in j))
            if k in exists:
                for m in sumps:
                    if m in dat[i]:
                        sumps[m][0].append(dat[i]) # present
                total_present.append(dat[i])
                break
    else: # i.e. didn't encounter break
        j = i.replace("\u200d", "").replace("\ufe0f", "")
        k = "{}.svg".format("-".join("{:04x}".format(ord(m)) for m in j))
        print(k, i)
        for m in sumps:
            if m in dat[i]:
                sumps[m][1].append(dat[i]) # absent
        total_wanted.append(dat[i])

print()
for i in sumps:
    print("{}: {:d} present, {:d} wanted: ".format(i, len(sumps[i][0]), len(sumps[i][1])),
            *(j["UCS.Standard"] for j in sumps[i][1] if "UCS.Standard" in j))
print("Overall: {:d} present, {:d} wanted".format(len(total_present), len(total_wanted)))

print("Sorting out names")
for pn in glob.glob("**/*.svg", recursive=True):
    i = os.path.basename(pn)
    if "draft" in i.casefold():
        continue
    ucs = "".join(chr(int(j, 16)) for j in os.path.splitext(i)[0].replace("-BW", "").split("-"))
    document = xml.dom.minidom.parse(pn)
    cldrname = get_cldrname(ucs)
    if cldrname:
        if not document.getElementsByTagName("title"):
            title = document.createElement("title")
            title.appendChild(document.createTextNode(cldrname))
            document.documentElement.insertBefore(title, document.documentElement.firstChild)
            document.documentElement.insertBefore(document.createTextNode("\n    "), title)
            #print("Adding name to", i)
        else:
            title = document.getElementsByTagName("title")[0]
            if "," not in cldrname and title.firstChild.wholeText.strip().casefold() != cldrname.casefold():
                for j in title.childNodes:
                    title.removeChild(j)
                title.appendChild(document.createTextNode(cldrname))
                #print("Updating name of", i)
        if cldrname.startswith("Unicode "):
            cfn = cldrname[8:].casefold()
            collision = rcldrnames[cfn]
            collision = "-".join("{:04x}".format(ord(j)) for j in collision)
            comment = "CLDR {!r} is {}".format(cfn, collision)
            print(comment)
            if title.lastChild.nodeName != "#comment": # i.e. if not already added.
                title.appendChild(document.createComment(comment))
        shutil.move(pn, pn + "~")
        with open(pn, "w") as f:
            x = document.toxml().replace("<?xml version=\"1.0\" ?>", "")
            f.write(x)
            os.unlink(pn + "~")







