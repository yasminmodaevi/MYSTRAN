from .converter import convert_inp_to_bdf
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Convert CalculiX .inp to Nastran .bdf")
    parser.add_argument("input", help="Input .inp file")
    parser.add_argument("output", help="Output .bdf file")
    parser.add_argument("--format", choices=['fixed', 'large', 'free'], default='fixed', help="BDF format")
    parser.add_argument("--inline", action="store_true", help="Inline include files")

    args = parser.parse_args()
    convert_inp_to_bdf(args.input, args.output, args.format, args.inline)

if __name__ == "__main__":
    main()
