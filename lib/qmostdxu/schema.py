from pathlib import Path
import sys
import yaml

from jsonschema import validate, Draft202012Validator

from .yaml_loader import IncludeLoader


class DXUSchema:
    schemafile = Path(__file__).parent / "schema" / "dxu_schema.yml"

    """Class to validate a DXU definition"""

    def __init__(self, fname=None):
        if fname is None:
            fname = DXUSchema.schemafile
        with open(fname) as fp:
            self.schema = yaml.load(fp, Loader=IncludeLoader)

    def validate(self, dxudef):
        """Validate a DXU definition against the schema

        Parameters
        ----------
        dxudef : :class:`dict`
            DXU definition read from a yaml file

        Raises
        ------
        :class:`jsonschema.exceptions.ValidationError`
            if the instance is invalid

        :class:`jsonschema.exceptions.SchemaError`
            if the schema itself is invalid

        """
        validate(
            dxudef,
            self.schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

    @staticmethod
    @Draft202012Validator.FORMAT_CHECKER.checks("fitsunit", ValueError)
    def _check_fitsunit(s):
        import astropy.units as u

        u.Unit(s, format=u.format.Fits)
        return True

    @staticmethod
    @Draft202012Validator.FORMAT_CHECKER.checks("vo_ucd", ValueError)
    def _check_ucd(s):
        from astropy.io.votable.ucd import parse_ucd

        parse_ucd(s, check_controlled_vocabulary=True)
        return True

    def to_rst(self, fp=sys.stdout):
        """Return an RestructuredText with the schema documentation"""
        schemaDoc(self.schema, fp)


def schemaDoc(doc, fp=sys.stdout, name=None, depth=0):
    """Simple JSON schema documentation function

    Note that this is incomplete and optimized to output the DXU schema.
    """
    if isinstance(doc, str):
        with open(doc) as in_fp:
            doc = yaml.load(in_fp, Loader=IncludeLoader)

    if name is not None:
        title = f"*{name}*: {doc['description']}"
        fp.write(f"{title}\n")
        fp.write("-*+.#"[depth] * len(title))
        fp.write("\n\n")

    if doc["type"] == "array":
        fp.write("Attributes of each item:\n\n")
        doc = doc["items"]
    else:
        fp.write("Attributes:\n\n")
    subsections = []
    for key, p in doc["properties"].items():
        req = "*required*, " if key in doc.get("required", []) else ""
        fp.write(f"**{key}**\n  {p['description']}")
        if p["type"] in ("object", "array"):
            if "properties" in p or "items" in p:
                fp.write(f" ({req}see below)\n\n")
                subsections.append((p, key))
            else:
                fp.write("\n\n")
        else:
            if isinstance(p["type"], list):
                fp.write(f" ({req}{' / '.join(p['type'])}")
            else:
                fp.write(f" ({req}{p['type']}")
            if "enum" in p:
                fp.write(f", one of ``{'`` / ``'.join(p['enum'])}``")
            if "default" in p:
                fp.write(f", {yaml.dump({'default': p['default']}).strip()}")
            print(")\n")

    for s, name in subsections:
        schemaDoc(s, fp, name, depth + 1)
