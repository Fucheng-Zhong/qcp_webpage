from astropy.io import fits
import os
import yaml
import logging
import pandas as pd
import hashlib
import numpy as np
import datetime

# see "dxudef.py"
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

invert_fits_datatypes = {v:k for k,v in fits_datatypes.items()}

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

def isnull(val):
    if type(val)==str:
        if len(val) == 0:
            return True
    
    if type(val)==int or type(val)==float:
        if np.isnan(val):
            return True
    '''
    if type(val) == datetime.datetime:
        return False
    '''


def data_transform(row):
    """
    KEY -> name
    VALUE -> value
    COMMENT -> description
    ORIGIN -> notes

    TTYPE -> name
    TUNIT -> unit
    TFORM -> datatype
    TCOMM -> description
    TUCD -> ucd
    TLMIN, TLMAX, TNULL -> range
    NOTES -> notes
    maxlength: 24
    """
    data = {}
    rang = {}
    for key, val in row.items():
        if isnull(val):
            continue
        #== header
        if key == 'KEY':
            data['name'] = val
        elif key == 'VALUE':
            data['value'] = val
        elif key == 'COMMENT':
            data['description'] = val
        elif key == 'ORIGIN':
            data['notes'] = val
        # col
        elif key == 'TTYPE':
            data['name'] = val
        elif key == 'TUNIT':
            data['unit'] = val
        elif key == 'TFORM':
            data['datatype'] = invert_fits_datatypes[val]
        elif key == 'TCOMM':
            data['description'] = val
        elif key == 'TUCD':
            data['ucd'] = val
        elif key == 'TLMIN' :
            rang['min'] = val
        elif key == 'TLMAX':
            rang['max'] = val
        elif key == 'TNULL':
            rang_null = val
        elif key == 'NOTES':
            data['notes'] = val
        if len(rang) != 0:
            data['range'] = rang
        		

    return data


class yamlCreation:

    """
    Creating a yaml file from excel file
    """

    def __init__(self, folder='./yaml'):
        # create a folder
        self.yaml_folder = folder
        self.sheet_names = []
        self.sheet_data = []
        self.sheet_readme = []
        self.DXU = {}

        if not os.path.exists(self.yaml_folder ):
            os.mkdir(self.yaml_folder )
        

    def create_from_excel(self, excel_file):

        """
        Creating a yaml file from excel file
        """

        # read Excel file
        header_idx = 6
        self.sheet_data = pd.read_excel(excel_file, sheet_name=None, header=header_idx)
        # get the sheet names
        self.sheet_names = list(self.sheet_data.keys())

        print(f"Sheet Names: {self.sheet_names}")
        if 'README' in self.sheet_names:
            self.sheet_readme = self.sheet_names['README']
            self.sheet_names.remove('README')

        # create yaml files from the sheets list
        for sheet_name in self.sheet_names:
            # read the info of table 0-6 row
            info = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=6, header=None)
            description = info.loc[1][1]
            responsable = info.loc[2][1]

            print('sheet name: ', sheet_name)
            print('description: \n', description)
            print('responsable: \n', responsable)
            self.yaml_from_sheet(sheet_name, self.sheet_data[sheet_name], description, responsable)




    def yaml_from_sheet(self, sheet_name, sheet_data, description, responsable):

        # read each row of sheet
        formatted_rows = []
        for index, row in sheet_data.iterrows():
            # discirtion strat with '#'
            if type(row[0]) != str or row[0].startswith('#'):
                continue
            formatted_rows.append(data_transform(row))

        if sheet_name == 'primary':
            data = {    'name': sheet_name,
                        'description': description,
                        'responsable': responsable,
                        'header': formatted_rows,
                        }

        else: 
            data = {    'name': sheet_name,
                        'description': description,
                        'responsable': responsable,
                        'columns': formatted_rows,
                        }

        fname = os.path.join(self.yaml_folder, f'{sheet_name}.yml')
        with open(fname, 'w') as outfile:

            for key, vals in data.items():

                if key == 'header' or key == 'columns':
                    outfile.write(key+':\n')
                    for col in vals:
                        outfile.write(
                                yaml.dump([col],
                                            sort_keys=False,
                                            indent=2,
                                            default_flow_style=False)
                                )
                        outfile.write('\n')

                else:
                    outfile.write(
                            yaml.dump({key: vals},
                                        sort_keys=False,
                                        indent=2,
                                        default_flow_style=False)
                            )
                    outfile.write('\n')
      
        
        # Calculate SHA-256 checksum:
        fname = os.path.join(self.yaml_folder, f'{sheet_name}.yml')
        checksum = hashlib.sha256(open(fname, 'rb').read())
        checksum_id = f"{checksum.hexdigest()}  {sheet_name}.yml"
        print(checksum_id + "\n")
        with open(os.path.join(self.yaml_folder, f'{sheet_name}.sha256'), 'w') as chksum_file:
            chksum_file.write(checksum_id)

    def make_primary_header(self):
        """
        Create the Primary Header based on the YAML formatted DXU specification
        Returns
        -------
        :class:`astropy.io.fits.Header`
            The Primary Header with prefilled values and comments

        keys_to_update : list[str]
            A list of all header keywords that should be updated afterwards,
            i.e., their `origin` is not *static* nor *set* by another source.
        """
        #load yaml files
        self.headers, self.keys_to_update = {}, {}
        for fname in self.sheet_names:
            dxu_fname = f'yaml/{fname}.yml'
            with open(dxu_fname) as dxu_file:
                self.DXU[fname] = yaml.full_load(dxu_file)

            header = fits.Header()
            keys_to_update = []

            # read yaml
            if 'header' in self.DXU[fname].keys():
                for card in self.DXU[fname]['header']:
                    key = card['name']
                    if 'value' in card.keys():
                        value = card['value']
                    else:
                        value = ''
                
                    if 'description' in card.keys():
                        description = card['description']
                    else:
                        description = ''
                    header[key] = (value, description)

            elif 'columns' in self.DXU[fname].keys():
                i = 1
                for card in self.DXU[fname]['columns']:
                    key = 'Col'+str(i)
                    i = i +1
                    value = card['name']
                    
                    if 'description' in card.keys():
                        description = card['description']
                    else:
                        description = ''
                    header[key] = (value, description)

            self.headers[fname], self.keys_to_update = header, keys_to_update

    

