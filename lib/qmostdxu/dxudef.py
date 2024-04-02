import sys
import yaml

import numpy as np
import astropy.units as u
from astropy.io.fits import Header, PrimaryHDU, BinTableHDU, HDUList

from .yaml_loader import IncludeLoader
from .schema import DXUSchema
from .fitsrst import createFitsRST


class DXUDefinition:
    """Definition of a DXU by a yaml file

    The yaml file can include other files with the "!" directive.  The
    definition consists of some global properties, a primary extension
    listing the keywords of the primary FITS header, and data table
    extensions.

    Examples
    --------

    Print out the basic properties of a DXU definition::

        >>> with open('example/qxp.yml') as fp:
        ...     dxudef = DXUDefinition(fp)
        >>> dxudef.name
        'Example DXU'
        >>> dxudef.version
        '0.0'
        >>> dxudef.description
        'FITS output from the 4MOST extragalactic pipeline (4XP)'

    """

    schema = DXUSchema()

    def __init__(self, fp):
        self.definition = yaml.load(fp, Loader=IncludeLoader)
        self.primary = DXUPrimary(self.definition["extensions"][0])
        self.extensions = [
            DXUExtension(ext) for ext in self.definition["extensions"][1:]
        ]

    @property
    def name(self):
        """DXU name/title"""
        return self.definition["name"]

    @property
    def version(self):
        """Version number"""
        return self.definition["version"]

    @property
    def description(self):
        """Global description"""
        return self.definition["description"]

    def validate(self):
        """Validate the DXU definition against the schema.


        Raises
        ------

        :class:`jsonschema.exceptions.ValidationError`
            if the instance is invalid

        :class:`jsonschema.exceptions.SchemaError`
            if the schema itself is invalid

        Examples
        --------

        Validate a DXU definition::

            >>> with open('example/qxp.yml') as fp:
            ...     dxudef = DXUDefinition(fp)
            >>> dxudef.validate()

        """
        __class__.schema.validate(self.definition)

    @property
    def hdu_template(self):
        """Return an empty template as HDUList

        The list consists of a primary HDU and empty tables with the
        proper headers for each extension.

        """
        return HDUList(
            list(ext.hdu_template for ext in [self.primary] + self.extensions)
        )

    def to_rst(self, fp=sys.stdout):
        """Schema documentation as RestructuredText

        Write a human readable reference documentation to the given
        file handle. This includes global information, the primary
        header, and the column properties for all defined data tables.

        Examples
        --------

        Write out the documentation of a schema::

            >>> with open('example/qxp.yml') as fp:
            ...     dxudef = DXUDefinition(fp)
            >>> dxudef.to_rst(sys.stdout)  # doctest: +ELLIPSIS
            Example DXU
            ...

        """
        creators = ", ".join(
            "{first-name} {last-name}".format(**c) for c in self.definition["creators"]
        )
        fp.write(
            f"{self.name}\n{'='*len(self.name)}\n\n"
            f"**Author(s)**\n  {creators}\n\n"
            f"**Version**\n  {self.version}\n\n"
            f"{self.description}\n\n"
        )
        self.primary.to_rst(fp)
        for ext in self.extensions:
            ext.to_rst(fp)

    def to_fits_rst(self, fp=sys.stdout):
        """Documentation of the FITS tables

        Write a reference documentation of all FITS tables defined by
        this DXU to the given file handle. Note that the TCOMM\\ *n*
        keywords are not written, to save space in the table.

        Examples
        --------

        Write out the documentation of a schema::

            >>> with open('example/qxp.yml') as fp:
            ...     dxudef = DXUDefinition(fp)
            >>> dxudef.to_fits_rst(sys.stdout)  # doctest: +ELLIPSIS
            QXP-Z FITS extension
            ...

        """
        for ext in self.extensions:
            ext.to_fits_rst(fp)


class DXUPrimary:
    """Primary header of the DXU"""

    def __init__(self, definition):
        self.name = definition["name"]
        self.description = definition["description"]
        self.header = definition["header"]

    @property
    def hdu_template(self):
        """Return the primary header HDU as a template.

        The header contains the keywords defined in the primary
        section of the DXU, and the values that are declared
        static. Values that are set are left empty.

        Examples
        --------

        Print the FITS header of the primary extension::

            >>> with open('example/qxp.yml') as fp:
            ...     primary = DXUDefinition(fp).primary
            >>> primary.hdu_template.header  # doctest: +ELLIPSIS
            SIMPLE  =                    T / conforms to FITS standard
            BITPIX  =                    8 / array data type
            NAXIS   =                    0 / number of array dimensions
            PRODCATG= 'SCIENCE.CATALOG'    / Data product category
            ORIGIN  = 'ESO-PARANAL'        / Observatory or facility
            TELESCOP= 'ESO-VISTA'          / ESO telescope designation
            INSTRUME= 'QMOST   '           / Instrument name
            PROG_ID =  / Observing run identification code: TP.C-NNNN(R)
            ...
        """
        header = Header()
        for c in self.header:
            name = c["name"]
            if c.get("array"):
                name = f"{name}1"
            header[name] = c.get("value"), c.get("description")
        return PrimaryHDU(header=header)

    def to_rst(self, fp=sys.stdout):
        """Documentation of the primary header as RestructuredText

        Write a human readable reference documentation to the given
        file handle. This is a table showing keyword, value or data
        type, and description for each header item.

        Examples
        --------

        Print the documentation of the primary extension::

            >>> with open('example/qxp.yml') as fp:
            ...     primary = DXUDefinition(fp).primary
            >>> primary.to_rst(sys.stdout)
            Primary extension
            ...

        """
        fp.write(
            f"{self.name} extension\n"
            f"{'-'*len(self.name+' extension')}\n\n"
            f"{self.description}\n\n"
            ".. list-table::\n"
            "   :widths: 1 10 40 40\n"
            "   :header-rows: 1\n"
            "   :stub-columns: 1\n"
            "\n"
            "   * - Header keyword\n"
            "     - Value/*Type*\n"
            "     - Description\n"
            "     - Notes\n"
        )

        values = {}
        for c in self.header:
            name = c["name"]
            if c.get("array"):
                name = f"{name}\\ *n*"
            if "value" in c:
                value = c["value"]
                if isinstance(value, str) and len(value) > 0:
                    value = f"``{value}``"
            else:
                value = f"*{c.get('datatype')}*"
            notes = []
            if "notes" in c:
                notes.append(c["notes"])
            if "range" in c:
                if "min" in c["range"] and "max" in c["range"]:
                    notes.append(
                        f'Range: {c["range"]["min"]} ' f'to {c["range"]["max"]}'
                    )
                elif "min" in c["range"]:
                    notes.append(f'Range: ≥ {c["range"]["min"]}')
                elif "max" in c["range"]:
                    notes.append(f'Range: ≤ {c["range"]["max"]}')
            if "values" in c:
                sseq = []
                for opt, desc in c["values"].items():
                    s = str(opt)
                    if desc is not None:
                        s += f" ({desc})"
                    sseq.append(s)
                if len(sseq) <= 3:
                    notes.append("Possible values: " + ", ".join(sseq))
                else:
                    notes.append(
                        f"See :ref:`below <{name} values>`" " for possible values"
                    )
                    values[name] = sseq
            if c.get("array"):
                notes.append("*n* = 1…")
            if not c.get("required", True):
                notes.append("Optional")
            if "value" in c:
                notes.append("Static value")
            notes = ". ".join(notes)
            description = c.get("description", "")
            if c.get("unit"):
                unit = u.Unit(c.get("unit")).to_string("unicode")
                description += f" [{unit}]"
            fp.write(
                f"   * - {name}\n"
                f"     - {value}\n"
                f"     - {description}\n"
                f"     - {notes}\n"
            )

        fp.write("\n")


class DXUExtension:
    """Table definition of a DXU

    This describes the properties of all column for a DXU table
    definition.

    """

    def __init__(self, definition):
        self.name = definition["name"]
        self.description = definition["description"]
        self.columns = definition["columns"]

    # Convert DXU datatypes to FITS datatypes
    fits_datatypes = {
        "str": "A",
        "bool": "L",
        "int8": "B",
        "int16": "I",
        "int32": "J",
        "int64": "K",
        "uint8": "B",
        "uint16": "I",
        "uint32": "J",
        "uint64": "K",
        "float": "E",
        "double": "D",
    }

    np_dtypes = {
        "str": str,
        "bool": bool,
        "int8": np.int8,
        "int16": np.int16,
        "int32": np.int32,
        "int64": np.int64,
        "uint8": np.uint8,
        "uint16": np.uint16,
        "uint32": np.uint32,
        "uint64": np.uint64,
        "float": np.float32,
        "double": np.float64,
    }

    # Pre-defined zero values for some datatypes
    tzeros = {
        "int8": -(2**7),
        "uint16": 2**15,
        "unit32": 2**31,
        "uint64": 2**63,
    }

    @property
    def hdu_template(self):
        """Return the table extension HDU as a template.

        This is a :class:`astropy.io.fits.BinTableHDU`, with zero rows
        and all columns as defined in the DXU.

        Examples
        --------

        Print the FITS header of the primary extension::

            >>> with open('example/qxp.yml') as fp:
            ...     ext = DXUDefinition(fp).extensions[0]
            >>> ext.hdu_template.header  # doctest: +ELLIPSIS
            XTENSION= 'BINTABLE'           / binary table extension
            BITPIX  =                    8 / array data type
            NAXIS   =                    2 / number of array dimensions
            NAXIS1  =                  362 / length of dimension 1
            NAXIS2  =                    0 / length of dimension 2
            PCOUNT  =                    0 / number of group parameters
            GCOUNT  =                    1 / number of groups
            TFIELDS =                   40 / number of table fields
            TTYPE1  = 'OBJ_NME '
            TFORM1  = '24A     '
            ...

        """
        header = Header()
        dtypes = []
        for i, c in enumerate(self.columns, 1):
            ttype = c.get("name", f"col{i}")
            tcomm = c.get("description", "")[:68]
            tform = self.fits_datatypes[c.get("datatype", "str")]
            dtype = self.np_dtypes[c.get("datatype", "str")]
            ml = c.get("maxlength", 1)
            ml = max(ml, max(len(s) for s in c.get("values", [""])))
            sz = c.get("arraysize", 1)
            if ml * sz > 1:
                tform = f"{ml*sz}{tform}"
                dtypes.append((ttype, dtype, ml * sz))
            else:
                dtypes.append((ttype, dtype))
            if ml > 1 and sz > 1:
                tdim = f"({ml}, {sz})"
            else:
                tdim = None

            tzero = self.tzeros.get(c["datatype"])
            tunit = c.get("unit")
            tucd = c.get("ucd")
            tlmin = c.get("range", {}).get("min")
            tlmax = c.get("range", {}).get("max")

            header[f"TTYPE{i}"] = ttype
            if tcomm:
                header[f"TCOMM{i}"] = tcomm
            header[f"TFORM{i}"] = tform
            if tdim:
                header[f"TDIM{i}"] = tdim
            if tzero:
                header[f"TZERO{i}"] = tzero
            if tunit:
                header[f"TUNIT{i}"] = tunit
            if tucd:
                header[f"TUCD{i}"] = tucd
            if tlmin:
                header[f"TLMIN{i}"] = tlmin
            if tlmax:
                header[f"TLMAX{i}"] = tlmax
        hdu = BinTableHDU(np.recarray(shape=(0,), dtype=dtypes), name=self.name)
        del hdu.header["TDIM*"]  # will be re-filled below
        hdu.header.update(header)
        return hdu

    def to_rst(self, fp=sys.stdout):
        """Schema documentation as RestructuredText

        Write a human readable reference documentation of the
        extension to the given file handle. This is a table showing
        the name, data type, description and the other properties for
        each data column.

        """
        fp.write(
            f"{self.name} extension\n"
            f"{'-'*len(self.name+' extension')}\n\n"
            f"{self.description}\n\n"
            ".. list-table::\n"
            "   :widths: 1 10 40 40\n"
            "   :header-rows: 1\n"
            "   :stub-columns: 1\n"
            "\n"
            "   * - Column name\n"
            "     - Type\n"
            "     - Description\n"
            "     - Notes\n"
        )

        values = {}
        for c in self.columns:
            name = c["name"]
            datatype = c["datatype"]
            if "arraysize" in c:
                datatype = f"{datatype}[{c['arraysize']}]"
            notes = []
            if "notes" in c:
                notes.append(c["notes"])
            if "range" in c:
                if "min" in c["range"] and "max" in c["range"]:
                    notes.append(
                        f'Range: {c["range"]["min"]} ' f'to {c["range"]["max"]}'
                    )
                elif "min" in c["range"]:
                    notes.append(f'Range: ≥ {c["range"]["min"]}')
                elif "max" in c["range"]:
                    notes.append(f'Range: ≤ {c["range"]["max"]}')
            if "values" in c:
                sseq = []
                for opt, desc in c["values"].items():
                    s = str(opt)
                    if desc is not None:
                        s += f" ({desc})"
                    sseq.append(s)
                if len(sseq) <= 3:
                    notes.append("Possible values: " + ", ".join(sseq))
                else:
                    notes.append(
                        f"See :ref:`below <{name} values>`" " for possible values"
                    )
                    values[name] = sseq
            if c.get("maybenull"):
                notes.append(" May be empty")
            if "maxlength" in c:
                notes.append(f"Max length: {c['maxlength']}")
            notes = ". ".join(notes)
            description = c.get("description", "")
            if c.get("unit"):
                unit = u.Unit(c.get("unit")).to_string("unicode")
                description += f" [{unit}]"
            fp.write(
                f"   * - {name}\n"
                f"     - {datatype}\n"
                f"     - {description}\n"
                f"     - {notes}\n"
            )

        fp.write("\n")
        if len(values) > 0:
            fp.write("Notes\n" ".....\n")
            for name, seq in values.items():
                maxlen = max(len(val) for val in seq)
                ncols = min(int(60 / maxlen + 1), 4)
                fp.write(
                    f"\n.. _{name} values:\n\n"
                    f"List of values for column **{name}**:\n\n"
                    ".. hlist::\n"
                    f"   :columns: {ncols}\n\n"
                )
                for val in seq:
                    fp.write(f"   * {val}\n")
            fp.write("\n")

    def to_fits_rst(self, fp=sys.stdout):
        """Documentation of one FITS table extension

        Write a reference documentation of the FITS tables defined by
        this extension to the given file handle. Note that the
        TCOMM\\ *n* keywords are not documented here, to save space in the
        table.

        """
        fp.write(
            f"{self.name} FITS extension\n"
            f"{'-'*len(self.name+' FITS extension')}\n\n"
            f"{self.description}\n\n"
        )
        createFitsRST(self.hdu_template.header, fp)
