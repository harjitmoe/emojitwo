import re

expects = {
    "z": 0,
    "h": 1,
    "v": 1,
    "l": 2,
    "m": 2,
    "t": 2,
    "s": 4,
    "q": 4,
    "c": 6,
    "a": 7}

pathre = re.compile(r"\s+|(?<=\S)\s*(?=[-MmLlHhVvCcSsQqTtAaZz])|(?<=[MmLlHhVvCcSsQqTtAaZz])\s*(?=.)")

feminine = [('M', [1.5, -0.02]), ('c', [-0.32, 0.0, -0.5, 0.2, -0.5, 0.47]), ('v', [0.55]), ('h', [1.0]), ('v', [-0.55]), ('c', [0.0, -0.4, -0.27, -0.39, -0.27, -0.39]), ('s', [-0.02, -0.08, -0.23, -0.08]), ('z', [])]
fem_characteristic = "Mcvhvcs"
fem_scale = 1

masculine = [('M', [0.62, 1.59]), ('h', [0.77]), ('l', [0.03, -0.08]), ('c', [0.0, -0.31, -0.08, -0.44, -0.41, -0.44]), ('c', [-0.34, -0.0, -0.43, 0.14, -0.43, 0.45]), ('l', [-0.01, -0.01]), ('l', [0.05, 0.08]), ('z', [])]
masc_characteristic = "Mlhlcc"
masc_scale = 0.77
masc_shift = (-0.43, 0.51)

def stack_points(l):
    for i in l:
        if i.count(".") < 2:
            yield i
        else:
            multi = i.split(".")
            yield multi[0] + "." + multi[1]
            yield from iter(multi[2:])

def _grok_d(d):
    d = list(stack_points(pathre.split(d.strip())))
    current_command = "M"
    x = y = savex = savey = 0
    first = True
    while d:
        if d[0].casefold() in expects:
            current_command = d.pop(0)
        expecting = expects[current_command.casefold()]
        args = d[:expecting]
        del d[:expecting]
        args = [float(i) for i in args]
        if current_command != current_command.casefold():
            if current_command == "M":
                pass
            elif current_command == "H":
                args[0] -= x
                current_command = current_command.casefold()
            elif current_command == "V":
                args[0] -= y
                current_command = current_command.casefold()
            elif current_command == "A":
                args[-2] -= x
                args[-1] -= y
                current_command = current_command.casefold()
            else:
                for n in range(len(args)):
                    if n % 2:
                        args[n] -= y
                    else:
                        args[n] -= x
                current_command = current_command.casefold()
        elif current_command == "m":
            args[0] = args[0] + x
            args[1] = args[1] + y
            current_command = "M"
        #
        if current_command == "M":
            x, y = args
        elif current_command.casefold() == "h":
            x += args[0]
        elif current_command.casefold() == "v":
            y += args[0]
        elif current_command.casefold() == "z":
            if abs(x - savex) < 0.005:
                if abs(y - savey) > 0.005:
                    yield ("v", [savey - y])
            elif abs(y - savey) < 0.005:
                yield ("h", [savex - x])
            else:
                yield ("l", [savex - x, savey - y])
            x, y = savex, savey
        else:
            x += args[-2]
            y += args[-1]
        #
        if current_command == "M":
            savex = x
            savey = y
        yield (current_command, args)
        first = False

def _chunk(commands):
    chunk = []
    for command, args in commands:
        if command == "M" and chunk:
            yield chunk[:]
            del chunk[:]
        chunk.append((command, args))
    yield chunk[:]

def grok_d(d):
    masterx, mastery = 0, 0
    for chunk in _chunk(_grok_d(d)):
        assert chunk[0][0] == "M"
        express_closed = False
        # Don't need to fully process z here since _grok_d's already supplemented them with an l
        # However, presence of final z means re-ordering is possible
        if chunk[-1][0] == "z":
            chunk.pop()
            mletter, (xs, ys) = chunk.pop(0)
            x, y = xs, ys
            xa = []
            ya = []
            for command, args in chunk:
                xa.append(x)
                ya.append(y)
                if command == "h":
                    x += args[0]
                elif command == "v":
                    y += args[0]
                else:
                    x += args[-2]
                    y += args[-1]
            xm = sum(xa) / len(xa)
            ym = sum(ya) / len(ya)
            x, y = xs, ys
            lastn = 0
            lastr = (((x-xm)**2) + ((y-ym)**2)) ** 0.5
            lastc = (x, y)
            for n, (command, args) in enumerate(chunk):
                r = (((x-xm)**2) + ((y-ym)**2)) ** 0.5
                if r < lastr:
                    lastn = n
                    lastc = (x, y)
                if command == "h":
                    x += args[0]
                elif command == "v":
                    y += args[0]
                else:
                    x += args[-2]
                    y += args[-1]
            chunk = chunk[lastn:] + chunk[:lastn]
            if (masterx, mastery) == (0, 0):
                yield ("M", list(lastc))
            else:
                yield ("m", [lastc[0] - masterx, lastc[1] - mastery])
            yield from iter(chunk)
            yield ("z", [])
            masterx, mastery = lastc
        else:
            x, y = masterx, mastery
            for n, (command, args) in enumerate(chunk):
                if command == "M":
                    yield ("m", [args[0] - x, args[1] - y])
                    x, y = args
                elif command == "h":
                    yield (command, args)
                    x += args[0]
                elif command == "v":
                    yield (command, args)
                    y += args[0]
                elif command == "z":
                    yield (command, args)
                else:
                    yield (command, args)
                    x += args[-2]
                    y += args[-1]
            masterx, mastery = x, y

def process_scale(grokdout, divisor):
    first = True
    for command, args in grokdout:
        if first and (command in "Mm"):
            yield (command, args)
        elif command == "a":
            yield (command, [args[0] / divisor, args[1] / divisor,
                             args[2], args[3], args[4],
                             args[5] / divisor, args[6] / divisor])
        else:
            yield (command, [i / divisor for i in args])
        first = False

def reconstitute(commands):
    out = []
    for command, args in commands:
        out.append(command)
        out.extend("{:.2f}".format(i) if i != float(int(i)) else str(i) for i in args)
    return " ".join(out)

def skewer(document):
    for node in list(document.getElementsByTagName("path")):
        node.setAttribute("d", reconstitute(grok_d(node.getAttribute("d"))))

def equivalent_exchange(document):
    for node in list(document.getElementsByTagName("path")):
        if node.hasAttribute("fill") and node.getAttribute("fill") == "#ffb300":
            commands = list(grok_d(node.getAttribute("d")))
            characteristic = "".join(i[0] for i in commands).rstrip("z")
            if characteristic == masc_characteristic:
                scale = masc_scale
                partner = feminine
                ix, iy = masc_shift[0], masc_shift[1]
                ox, oy = 0, 0
            elif characteristic == fem_characteristic:
                scale = fem_scale
                partner = masculine
                ix, iy = 0, 0
                ox, oy = masc_shift[0], masc_shift[1]
            else:
                continue
            assert partner[0][0] == commands[0][0] == "M"
            myx, myy = commands[0][1]
            for command, args in commands:
                if command == "h":
                    char_length = args[0] / scale
                    break
            else: # for…else: finished without break
                raise AssertionError("matched characteristic but lacks an h command")
            new = list(process_scale(partner, 1 / char_length))
            new[0] = ("M", [myx + (ox - ix) * char_length, myy + (oy - iy) * char_length])
            node.setAttribute("d", reconstitute(new))
            # Move to bottom of stack
            title = document.getElementsByTagName("title")[0]
            if node.previousSibling == title.nextSibling:
                continue
            if node.previousSibling.nodeName == "#text":
                document.documentElement.insertBefore(node.previousSibling, title.nextSibling)
                title = title.nextSibling # i.e. what has just stopped being node.previousSibling
            document.documentElement.insertBefore(node, title.nextSibling)

if __name__ == "__main__":
    import xml.dom.minidom
    document = xml.dom.minidom.parse("../svg/1f46a.svg")
    skewer(document)
    document.writexml(open("temp.svg", "w"))



