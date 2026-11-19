"""slug.py - turns a car name into a safe id, e.g. 'Honda CR-V Hybrid' -> 'honda-cr-v-hybrid'."""
import re


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
