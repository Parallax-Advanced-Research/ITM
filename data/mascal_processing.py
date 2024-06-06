import pandas as pd
data_file = 'mascal/Non-CUI MASCAL Mock-up.xlsx'
def main():
    #injest data csv file
    data = None
    with open(data_file) as f:
        data = pd.read_excel(f)

    #clean data
    clean(data)

def clean(d):
    #normalize empty data entries to None
    possible_empty = ['', None, 'None', 'none']

if __name__ == '__main__':
    main()