from .parser import InpParser
from .writer import BdfWriter
from .models import FEModel

def convert_inp_to_bdf(inp_file, bdf_file, format_type='fixed', inline_includes=False):
    model = FEModel()
    parser = InpParser(model, inline_includes=inline_includes)
    parser.parse(inp_file)

    writer = BdfWriter(model)
    writer.set_format(format_type)
    writer.write(bdf_file)
    return model

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Convert CalculiX .inp to Nastran .bdf")
    parser.add_argument("input", help="Input .inp file")
    parser.add_argument("output", help="Output .bdf file")
    parser.add_argument("--format", choices=['fixed', 'large', 'free'], default='fixed', help="BDF format")
    parser.add_argument("--inline", action="store_true", help="Inline include files")

    args = parser.parse_args()
    convert_inp_to_bdf(args.input, args.output, args.format, args.inline)
