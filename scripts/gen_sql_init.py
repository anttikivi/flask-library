#!/usr/bin/env python3

# A helper script for generating the database init for the library
# classification. It prints the SQL output to stdout so you can redirect
# it as you wish.

from dataclasses import dataclass
from collections.abc import Sequence
import os
import sys
import xml.etree.ElementTree as ET


# The XML namespace (entries that this script needs) of the data.
NS: dict[str, str] = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
RDF_ABOUT = f"{{{NS['rdf']}}}about"
RDF_RESOURCE = f"{{{NS['rdf']}}}resource"


# Prefix of the "Concept" resources this script is interested in.
RESOURCE_PREFIX = "http://urn.fi/URN:NBN:fi:au:ykl:"


@dataclass
class YKLClass:
    """
    YKLClass represents single class in the YKL class hierarchy. Each of
    the classes, regardless of level, is parsed into YKLClass.

    `key` is the numeric notation for the class, for example "00.109".

    `subclasses` contain the subclasses for this class.

    `label` is the human-readable label for this class, for example
    "KIRJA-ALA".

    `alts` contains the additional index words for this class as
    specified in the data.
    """

    key: str
    subclasses: Sequence["YKLClass"]
    label: str
    alts: Sequence[str]


if __name__ == "__main__":
    tree: ET.ElementTree

    try:
        file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "ykl-skos.rdf.xmp"
        )
        tree = ET.parse(file)
    except ET.ParseError as e:
        print(f"failed to parse ykl-skos.rdf.xmp: {e}", file=sys.stderr)
        # Use early exits throughout the script. That makes the code
        # easier to follow.
        exit(1)

    root = tree.getroot()

    # Find all of the "ConceptSchemes" first. They contain the top-level
    # resources for finding the top-level YKL classes.
    concept_scheme = root.find("skos:ConceptScheme", NS)
    if concept_scheme is None:
        print("didn't find the concept scheme tag", file=sys.stderr)
        exit(1)

    top_concepts: list[str] = []

    for elem in concept_scheme.findall("skos:hasTopConcept", NS):
        top_concepts.append(elem.attrib[RDF_RESOURCE])

    # Collect the classes into a list. They can then be searched by
    # using the attributes of the dataclasses.
    root_classes: list[YKLClass] = []

    def parse(element: ET.Element) -> YKLClass:
        key = element.attrib[RDF_ABOUT].removeprefix(RESOURCE_PREFIX)
        pref_label = element.find("skos:prefLabel[@xml:lang='fi']", NS)
        if pref_label is None or pref_label.text is None:
            print("did not find a valid prefLabel for", key, file=sys.stderr)
            exit(1)
        label = pref_label.text
        alts: list[str] = []
        for elem in element.findall("skos:altLabel[@xml:lang='fi']", NS):
            if elem.text is not None:
                alts.append(elem.text)
        subclasses: list[YKLClass] = []
        for elem in element.findall("skos:narrower", NS):
            child = elem.attrib[RDF_RESOURCE]
            child_selector = f"skos:Concept[@{RDF_ABOUT}='{child}']"
            # The elements with this selector should be unique, so it is
            # safe to use only "find" instead of "findall".
            child_elem = root.find(child_selector, NS)
            if child_elem is None:
                print(
                    "did not find a child with selector",
                    child_selector,
                    file=sys.stderr,
                )
                exit(1)
            child_class = parse(child_elem)
            subclasses.append(child_class)
            subclasses.sort(key=lambda c: c.key)

        ykl_class = YKLClass(
            key=key, subclasses=subclasses, label=label, alts=alts
        )

        return ykl_class

    for elem in root.findall("skos:Concept", NS):
        if RDF_ABOUT in elem.attrib and elem.attrib[RDF_ABOUT] in top_concepts:
            ykl_class = parse(elem)
            root_classes.append(ykl_class)

    lines: list[str] = []

    # Align the boundaries for the database.

    def populate_output(node: YKLClass, current_lft: int) -> int:
        lft = current_lft
        current_lft += 1

        for child in node.subclasses:
            current_lft = populate_output(child, current_lft)

        rgt = current_lft
        current_lft += 1

        sql: str = f"INSERT INTO classification (key, label, lft, rgt) VALUES ('{node.key}', '{node.label}', {lft}, {rgt});"
        lines.append(sql)

        return current_lft

    current_lft = 1
    for ykl_class in root_classes:
        current_lft = populate_output(ykl_class, current_lft)

    lines.sort()

    output: str = "DELETE FROM classification;\n\n"
    sql = "\n".join(lines) + "\n"
    output = f"{output}{sql}"

    print(output)
