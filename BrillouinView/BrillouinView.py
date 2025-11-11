# This will become the new point of entry for BrillouinView

if __name__ == "__main__":
    filename = "BrillouinView/src/BrillouinView-Sep6.py"

    with open(filename, "r") as f:
        code = f.read()
    exec(code)
