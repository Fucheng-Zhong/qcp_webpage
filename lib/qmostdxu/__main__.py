#!/usr/bin/env python3
"""Simple YAML schema validator"""

import argparse
import sys
import yaml

from qmostdxu import DXUSchema
from qmostdxu.yaml_loader import IncludeLoader


def getparser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-s",
        "--schema",
        help="yaml schema file",
        type=str,
        default=str(DXUSchema.schemafile),
    )
    parser.add_argument("files", help="input files", type=str, nargs="+")
    return parser


def main():
    args = getparser().parse_args()
    schema = DXUSchema(args.schema)

    failed = False
    for fname in args.files:
        print(f"processing {fname}...")
        try:
            with open(fname) as fp:
                y = yaml.load(fp, Loader=IncludeLoader)
                schema.validate(y)
        except Exception as ex:
            print(ex)
            failed = True

    sys.exit(failed)


if __name__ == "__main__":
    main()
