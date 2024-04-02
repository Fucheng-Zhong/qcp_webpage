import sys


def createFitsRST(header, fp=sys.stdout):
    keys = [
        "TTYPE",
        "TFORM",
        "TDIM",
        "TZERO",
        "TUNIT",
        "TUCD",
        "TLMIN",
        "TLMAX",
    ]
    breaks = {
        "TUCD": ";",
        "TUNIT": ".",
    }
    fp.write(
        ".. list-table::\n"
        "   :header-rows: 1\n"
        "   :stub-columns: 2\n"
        "\n"
        "   * - *n*\n"
    )
    for key in keys:
        fp.write(f"     - {key}\\ *n*\n")
    for i in range(1, header["TFIELDS"] + 1):
        fp.write(f"   * - {i}\n")
        for key in keys:
            value = header.get(f"{key}{i}", "")
            for b in breaks.get(key, ""):
                value = value.replace(b, f"{b}​")  # Add a soft break
            fp.write(f"     - {value}\n")
    fp.write("\n")
