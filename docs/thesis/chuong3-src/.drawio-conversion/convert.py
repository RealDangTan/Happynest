from base64 import b64encode
from dataclasses import dataclass
from math import ceil
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET
import zlib


SOURCE = Path("docs/thesis/chuong3-src/uml")
RENDERS = SOURCE.parent / ".drawio-conversion"
DESTINATION = SOURCE / "HappyNest_Chuong3.drawio"
NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
TOKENS = re.compile(r"[MLCAZ]|" + NUM)
SCALE = .65
MARGIN = 14


def number(value):
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def style(**values):
    return "".join(f"{k}={number(v) if isinstance(v, float) else v};" for k, v in values.items())


def point_attrs(x, y):
    return {"x": number(x), "y": number(y)}


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @classmethod
    def covering(cls, boxes):
        left = min(box.x for box in boxes)
        top = min(box.y for box in boxes)
        right = max(box.x + box.w for box in boxes)
        bottom = max(box.y + box.h for box in boxes)
        return cls(left, top, max(1, right - left), max(1, bottom - top))

    @classmethod
    def around(cls, points):
        return cls.covering([cls(x, y, 0, 0) for x, y in points])

    def contains_label(self, label):
        return (
            label.x >= self.x - 2
            and label.x + label.w <= self.x + self.w + 2
            and self.y <= label.y + label.h / 2 <= self.y + self.h
        )


@dataclass
class Item:
    kind: str
    box: Box
    data: dict


def tag(element):
    return element.tag.rsplit("}", 1)[-1]


def f(element, key, default=0):
    return float(element.get(key, default))


def paints(element, default_fill="none"):
    properties = dict(
        pair.split(":", 1)
        for pair in element.get("style", "").split(";")
        if ":" in pair
    )
    appearance = {
        "fillColor": element.get("fill", properties.get("fill", default_fill)),
        "strokeColor": properties.get("stroke", element.get("stroke", "none")),
        "strokeWidth": float(properties.get("stroke-width", "1")) * SCALE,
    }
    if "stroke-dasharray" in properties:
        appearance.update(dashed=1, fixDash=1, dashPattern=" ".join(
            number(float(dash) * SCALE) for dash in re.findall(NUM, properties["stroke-dasharray"])
        ))
    return appearance


def path_segments(element):
    tokens = TOKENS.findall(element.get("d"))
    counts = {"M": 2, "L": 2, "A": 7, "C": 6, "Z": 0}
    cursor = 0
    while cursor < len(tokens):
        command = tokens[cursor]
        count = counts[command]
        yield command, tuple(float(v) for v in tokens[cursor + 1:cursor + 1 + count])
        cursor += count + 1


def path_points(segments):
    for command, coordinates in segments:
        if command == "A":
            yield coordinates[-2:]
        else:
            yield from zip(coordinates[::2], coordinates[1::2])


def read_item(element):
    kind = tag(element)
    if kind == "defs":
        return []
    if kind == "g":
        children = combine([item for child in element for item in read_item(child)])
        if not element.get("id") or not children:
            return children
        return [group(children)]
    if kind == "text":
        size = f(element, "font-size")
        label = "".join(element.itertext())
        return [Item("text", Box(f(element, "x"), f(element, "y") - .88 * size,
                                 f(element, "textLength", max(1, len(label)) * size * .5),
                                 1.16 * size), {
            "label": label,
            "look": style(fontFamily=element.get("font-family", "Times New Roman"),
                          fontSize=size * SCALE, fontColor=element.get("fill", "#111111"),
                          fontStyle=int(element.get("font-weight") == "bold")
                          + 2 * int(element.get("font-style") == "italic")),
        })]
    appearance = paints(element)
    if appearance["fillColor"] == "none" and appearance["strokeColor"] == "none":
        return []
    if kind == "rect":
        return [Item(kind, Box(f(element, "x"), f(element, "y"), f(element, "width"), f(element, "height")),
                     {"paint": appearance, "radius": f(element, "rx")})]
    if kind == "ellipse":
        rx, ry = f(element, "rx"), f(element, "ry")
        return [Item(kind, Box(f(element, "cx") - rx, f(element, "cy") - ry, rx * 2, ry * 2),
                     {"paint": appearance})]
    if kind == "line":
        points = [(f(element, "x1"), f(element, "y1")), (f(element, "x2"), f(element, "y2"))]
        return [Item("line", Box.around(points), {"paint": appearance, "points": points})]
    if kind == "polygon":
        coordinates = list(map(float, re.findall(NUM, element.get("points"))))
        points = list(zip(coordinates[::2], coordinates[1::2]))
        segments = [("M", points[0])] + [("L", point) for point in points[1:]] + [("Z", ())]
        return [Item("path", Box.around(points), {"paint": appearance, "segments": segments})]
    if kind == "path":
        segments = list(path_segments(element))
        points = list(path_points(segments))
        if appearance["fillColor"] == "none" and [command for command, _ in segments] == ["M", "L"]:
            return [Item("line", Box.around(points), {"paint": appearance, "points": points})]
        return [Item(kind, Box.around(points), {"paint": appearance, "segments": segments})]
    raise ValueError(f"Unsupported SVG element: {kind}")


def group(children):
    return Item("group", Box.covering([item.box for item in children]), {"children": children})


def combine(items):
    # PlantUML emits individual text runs for wrapped sequence messages.
    runs = []
    for item in items:
        if runs and item.kind == runs[-1].kind == "text":
            preceding = runs[-1]
            if (
                item.data["look"] == preceding.data["look"]
                and abs(item.box.y - preceding.box.y) < .02
                and abs(item.box.x - preceding.box.x - preceding.box.w) < 1
            ):
                preceding.data["label"] += item.data["label"]
                preceding.box = Box.covering([preceding.box, item.box])
                continue
        runs.append(item)

    combined = []
    cursor = 0
    while cursor < len(runs):
        item = runs[cursor]
        tail = cursor + 1
        if item.kind in ("rect", "ellipse", "path") and item.data["paint"]["fillColor"] != "none":
            while tail < len(runs) and runs[tail].kind == "text" and item.box.contains_label(runs[tail].box):
                tail += 1
        combined.append(group(runs[cursor:tail]) if tail - cursor > 1 else item)
        cursor = tail
    return combined


def inline_stencil(item):
    box = item.box
    shape = ET.Element("shape", name="PlantUML", w=number(box.w * SCALE), h=number(box.h * SCALE),
                       aspect="variable", strokewidth="inherit")
    background = ET.SubElement(shape, "background")
    path = ET.SubElement(background, "path")

    def x(value):
        return number((value - box.x) * SCALE)

    def y(value):
        return number((value - box.y) * SCALE)

    for command, coordinates in item.data["segments"]:
        if command in ("M", "L"):
            ET.SubElement(path, "move" if command == "M" else "line",
                          x=x(coordinates[0]), y=y(coordinates[1]))
        elif command == "C":
            ET.SubElement(path, "curve", x1=x(coordinates[0]), y1=y(coordinates[1]),
                          x2=x(coordinates[2]), y2=y(coordinates[3]),
                          x3=x(coordinates[4]), y3=y(coordinates[5]))
        elif command == "A":
            rx, ry, rotation, large, sweep, end_x, end_y = coordinates
            ET.SubElement(path, "arc", rx=number(rx * SCALE), ry=number(ry * SCALE),
                          **{"x-axis-rotation": number(rotation), "large-arc-flag": number(large),
                          "sweep-flag": number(sweep)}, x=x(end_x), y=y(end_y))
        elif command == "Z":
            ET.SubElement(path, "close")
    fg = ET.SubElement(shape, "foreground")
    paint = item.data["paint"]
    fill, stroke = paint["fillColor"] != "none", paint["strokeColor"] != "none"
    ET.SubElement(fg, "fillstroke" if fill and stroke else "fill" if fill else "stroke")
    encoded = quote(ET.tostring(shape, encoding="unicode"), safe="~!*'()").encode("ascii")
    deflater = zlib.compressobj(level=9, wbits=-15)
    return b64encode(deflater.compress(encoded) + deflater.flush()).decode("ascii")


class DrawioPage:
    def __init__(self, container, source, svg):
        self.next_id = 2
        _, _, width, height = map(float, svg.get("viewBox").split())
        page = ET.SubElement(container, "diagram", id=source.stem, name=source.stem)
        model = ET.SubElement(page, "mxGraphModel", dx="1200", dy="900", grid="0", gridSize="10",
                              guides="1", tooltips="1", connect="1", arrows="1", fold="1",
                              page="1", pageScale="1", pageWidth=str(ceil(width * SCALE + 2 * MARGIN)),
                              pageHeight=str(ceil(height * SCALE + 2 * MARGIN)), math="0",
                              shadow="0", background="#FFFFFF")
        self.root = ET.SubElement(model, "root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")

    def cell(self, item, parent="1", origin=(-MARGIN / SCALE, -MARGIN / SCALE)):
        cell_id = str(self.next_id)
        self.next_id += 1
        box = item.box
        base = "whiteSpace=nowrap;html=0;shadow=0;"
        if item.kind == "group":
            cell_style = "group;verticalAlign=middle;html=0;"
        elif item.kind == "text":
            cell_style = ("text;html=0;align=left;verticalAlign=middle;whiteSpace=nowrap;"
                          "strokeColor=none;fillColor=none;spacing=0;overflow=visible;"
                          + item.data["look"])
        elif item.kind == "line":
            cell_style = "edgeStyle=none;startArrow=none;endArrow=none;html=0;" + style(**item.data["paint"])
        elif item.kind == "rect":
            radius = item.data["radius"]
            cell_style = base + style(shape="rectangle", rounded=int(radius > 0),
                                      absoluteArcSize=1, arcSize=radius * 2 * SCALE,
                                      **item.data["paint"])
        elif item.kind == "ellipse":
            cell_style = "ellipse;" + base + style(**item.data["paint"])
        else:
            cell_style = base + style(shape=f"stencil({inline_stencil(item)})", **item.data["paint"])
        attributes = {
            "id": cell_id,
            "value": item.data.get("label", ""),
            "style": cell_style,
            "parent": parent,
        }
        if item.kind == "line":
            attributes["edge"] = "1"
            cell = ET.SubElement(self.root, "mxCell", attributes)
            geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
            for (x, y), role in zip(item.data["points"], ("sourcePoint", "targetPoint")):
                ET.SubElement(geometry, "mxPoint", {**point_attrs((x - origin[0]) * SCALE,
                                                                (y - origin[1]) * SCALE),
                                                      "as": role})
            return
        attributes["vertex"] = "1"
        cell = ET.SubElement(self.root, "mxCell", attributes)
        ET.SubElement(cell, "mxGeometry", {
            **point_attrs((box.x - origin[0]) * SCALE, (box.y - origin[1]) * SCALE),
            "width": number((box.w + (4 if item.kind == "text" else 0)) * SCALE),
            "height": number(box.h * SCALE),
            "as": "geometry",
        })
        for child in item.data.get("children", ()):
            self.cell(child, cell_id, (box.x, box.y))


def main():
    sources = sorted(SOURCE.glob("*.puml"))
    document = ET.Element("mxfile", host="app.diagrams.net", compressed="false", pages=str(len(sources)))
    for source in sources:
        svg = ET.parse(RENDERS / f"{source.stem}.svg").getroot()
        page = DrawioPage(document, source, svg)
        for item in combine([item for child in svg for item in read_item(child)]):
            page.cell(item)
    ET.indent(document, space="  ")
    incomplete = RENDERS / DESTINATION.name
    ET.ElementTree(document).write(incomplete, encoding="utf-8", xml_declaration=True)
    incomplete.replace(DESTINATION)
    print(f"Converted {len(sources)} PlantUML files to {DESTINATION}")


if __name__ == "__main__":
    main()

