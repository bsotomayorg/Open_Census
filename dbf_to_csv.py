#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__  = "Boris Sotomayor"
__email__   = "bsotomayor92@gmail.com"
__version__ = "12 / 10 / 16"

import csv
import os
import sys
from dbfpy import dbf

"""
Método que transforma un archivo formato *.dbf a *.csv
Parámetros de entrada:
* dir_in: directorio en donde se encuentran los archivos *.dbf
* dir_out: directorio en donde se encuentran los archivos *.csv
* file_name: nombre del archivo.
"""
def createCSV(dir_in, dir_out, file_name):
	dbf_fn = dir_in+file_name
	csv_fn = dir_out+file_name[:-3]+"csv"

	in_db = dbf.Dbf(dbf_fn)
	out_csv = csv.writer(open(csv_fn, 'wb'))

	names = []
	for field in in_db.header.fields:
	    names.append(field.name)
	out_csv.writerow(names)

	for rec in in_db:
	    out_csv.writerow(rec.fieldData)

	in_db.close()

### MAIN ###

if len(sys.argv)<3:
	print "\nMissing arguments..!\nEnter: 'python dbf_to_csv.py <dbf_folder> <csv_folder>'\n"
else:
	dbf_dir = sys.argv[1]
	csv_dir = sys.argv[2]

	if dbf_dir[-1]!="/":
		dbf_dir+="/"
	if csv_dir[-1]!="/":
		csv_dir+="/"

	for i in os.listdir(dbf_dir):
		createCSV(dbf_dir, csv_dir, i)
		print "File '%s%s' created.." % (csv_dir,i)


