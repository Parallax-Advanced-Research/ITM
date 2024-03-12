import argparse
import glob
from components.decision_selector.kdma_estimation import read_case_base, write_case_base

    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_filenames", metavar="CASEBASE", type=str, nargs = '+',
                        help="List of csv files with case data"
                       )
    parser.add_argument("--output_file", type=str, default="full_casebase.csv",
                        help="Output file to store the combined case base"
                       )

    args = parser.parse_args()
    combine_case_bases(args.input_filenames, args.output_file)
                       
def combine_case_bases(input_filenames, output_file):
    inputs = []
    for fname in input_filenames:
        inputs += glob.glob(fname)
    cb = []
    for fname in inputs:
        print("Reading in " + fname)
        cb += read_case_base(fname)
    write_case_base(output_file, cb)
    

if __name__ == '__main__':
    main()
