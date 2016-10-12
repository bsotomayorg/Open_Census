#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

__author__  = "Boris Sotomayor"
__email__   = "bsotomayor92@gmail.com"
__version__ = "26/08/16"

"""
Script que permite obtener una serie de consultas en lenguaje de consultas de Redatam almacenándolo en un archivo *.txt.
También es posible generar un script que, dada una serie de archivos *.csv, puede incoporar los datos a una base de datos Sqlite3.
"""

### --- clases básicas --- ###

class General(): 
    def __init__(self):
        self.name = "" 
        self.label = "" 
        self.entities = []
class Variable:
    def __init__(self): 
        self.name = "" 
        self.type = "STRING"
        self.label = "" 
        self.path_file = ""
        self.field_size = 0
        self.rangemin = -1
        self.rangemax = -1
        self.value_labels = []
class Entity:
    def __init__(self): 
        self.name = "" 
        self.label = ""
        self.child = ""
        self.selectable = False
        self.filename = ""
        self.variables = []
class ValueLabel:
    def __init__(self):
        self.name = ""
        self.number = ""
        self.value = ""


### --- métodos --- ###

"""
Realiza una lectura de un archivo *.wxp para crear instancias de Entidades y Variables con la información que contiene.

Parmátro de entrada:
* FILE_PATH: String que corresponde a la ruta del archivo con formato "*.wxp".
"""
def readWXP(FILE_PATH):
    fo = open(FILE_PATH)
    current_str = ""

    CENSO = General()
    E = Entity()
    V = Variable()

    for line in fo:
        if line[0]=="[":
            if "General" in line:
                current_str = "general"
            elif "Entity" in line:
                if current_str !="" and E.name !="" :
                    CENSO.entities.append(E)
                current_str = "entity"
                E = Entity() 
            elif "Variable" in line:
                V = Variable()
                current_str = "variable"
        else:
            if "ValueLabels" in line:
                current_str = "value_labels"
        if current_str=="entity":
            if line[0]=="N" and "Name" in line:
                E.name = line[5:-1]
            elif line[0]=="L" and "Label" in line:
                E.label = line[6:-1] 
            elif line[0]=="S" and "Selectable" in line:
                E.selectable = (line[11:-1].lower() == "yes")
        elif current_str=="variable":
            if line[0]=="N" and "Name" in line:
                V.name = line[5:-1]
                E.variables.append(V)
            elif line[0]=="L" and "Label" in line:
                V.label = line[6:-1] 
            elif line[0]=="F":
                if "FileName" in line:
                    V.filename = line[9:-1]
                elif "FieldSize" in line:
                    V.field_size = int(line[10:-1])
            elif line[0]=="T" and "Type" in line:
                V.type = line[5:-1]
            elif line[0]=="R":
                if "RangeMin" in line:
                    V.rangemin = int(line[9:-1])
                elif "RangeMax" in line:
                    V.rangemax = int(line[9:-1])
        elif current_str=="value_labels":
            if line[0]=="V" and line[1]=="L":
                VL = ValueLabel()
                VL.name   = line[0:line.find("=")]
                VL.number = line[line.find("=")+1:line.find(" ")]
                VL.value = line[line.find(" ")+1:-1]
                V.value_labels.append(VL)
        elif current_str=="general":
            if line[0]=="L" and "Label" in line:
                CENSO.label = line[6:-1]
            elif line[0]=="N" and "Name" in line:
                CENSO.name = line[5:-1]

    fo.close()

    if E.name != "":
        CENSO.entities.append(E)
    return CENSO

"""
Método que genera un script sqlite3 que permite crear la base de datos importando la información contenida en archivos *.csv

Parámetro de entrada:
* G (List) : Lista de entidades.

Retorna un string que corresponde al script sqlite.
"""
def createSqliteScript(G):
    str_sql = ".separator ,\n.mode column\n\n"
    for E in G.entities:
        for V in E.variables:
            if len(V.value_labels)!=0: # create tables with value labels (not empty tables..)
                str_sql += "-- TABLE \"%s_%s\"\n" % (E.name, V.name)
                str_sql += "CREATE TABLE %s_%s (REDCODE, " % (E.name, V.name)

                for i in range(V.rangemin, V.rangemax+1):
                    str_sql += "F_%i, " % i

                str_sql += "F_T);\n"
                str_sql += ".import CSV/%s_%s.csv %s_%s\n\n" % (E.name, V.name, E.name, V.name)
            elif E.selectable:
                str_sql += "-- TABLE \"%s_%s\"\n " % (E.name, V.name)
                str_sql += "CREATE TABLE %s_%s (REDCODE, %s);\n" % (E.name, V.name, V.name)
                str_sql += ".import CSV/%s_%s.csv %s_%s\n\n" % (E.name, V.name, E.name, V.name)
    return str_sql
 
"""
Método que permite obtener una serie de consultas para extraer datos de forma masiva de una base de datos Redatam.

Parámetros de entrada:
* G (List) : Lista de entidades.
* path (String) : Ruta en donde se almacenarán los archivos *.dbf tras consultar en Redatam.
* unit (String) : Unidad de área geográfica con la que se extraerán los datos. Ejemplos: REGION, PROVINCIA, ZONA, COMUNA, MANZENT, etc.

Retorna un string que contiene la serie de consultas escritas en lenguaje propio de Redatam.
"""
def dumpQueries(G, path, unit): 
    script_str = "RUNDEF Job\n\tSELECTION ALL\n\n"
    for E in G.entities:
        for V in E.variables:
            if E.selectable: 
                script_str += "// Codes of %s\n" % E.name
                script_str += str("TABLE %s_%s\n\tAS AREALIST\n\tOF %s, %s.%s 10.0\n\tOUTPUTFILE DBF \"%s%s_%s.dbf\"\n\tOVERWRITE\n\n" % (E.name, V.name, E.name, E.name, V.name, path, E.name, V.name))
            else: 
                script_str += "// %s-Level Data (Variable %s.%s)\n" % (unit.upper(), E.name, V.name)
                script_str += str("TABLE %s_%s\n\tAS AREALIST\n\tOF %s, %s.%s 10.0\n\tOUTPUTFILE DBF \"%s%s_%s.dbf\"\n\tOVERWRITE\n\n" % (E.name, V.name, unit, E.name, V.name, path, E.name, V.name))
    return script_str


"""
Método que procesa los argumentos escritos en consola al ejecutar el script.

Parámetros de entrada:
* argv (List) : Lista de argumentos escritos en consola.

Retorna la ruta del archivo, la ruta de la carpeta con archivos *.dbf, el nivel geográfico a utilizar y si generar el script sqlite3 o no (valor booleano)
"""
def readArgs(argv):

    PATH_FILE, PATH_DBF_FILES, LEVEL = "","",""

    B_SCRIPT_SQLITE = ("--sqlite" in argv) or ("--script" in argv)

    if len(sys.argv) > 0:
        PATH_FILE = "./"
        PATH_DBF_FILES = "C:/"
        LEVEL = "MANZENT"

        for arg in sys.argv[1:]:
            if ".wxp" in arg:
                PATH_FILE = arg
            elif "/" in arg and PATH_FILE != arg:
                if arg[-1]!="/":
                    arg+="/"
                PATH_DBF_FILES = arg
            elif not "-" in arg:
                LEVEL = arg 

    print "File *.wxp: '%s'\nDBFs Folder: '%s'\nLevel: '%s'\n" % (PATH_FILE, PATH_DBF_FILES, LEVEL)
    return PATH_FILE, PATH_DBF_FILES, LEVEL, B_SCRIPT_SQLITE


### MAIN ###

# se capturan los diferentes parámetros ingresados por consola
PATH_FILE, PATH_DBF_FILES, LEVEL, B_SCRIPT_SQLITE = readArgs(sys.argv)

# se procesa el archivo "*.wxp" para 
if PATH_FILE!="":
    G = readWXP(PATH_FILE)

    if PATH_DBF_FILES!="" and LEVEL!="":
        # se genera archivo *.txt con queries Redatam
        f = open("Redatam_Queries.txt", "w")
        f.write(dumpQueries(G, PATH_DBF_FILES, LEVEL))
        f.close()
        print "Redatam Queries file generated as \"Redatam_Queries.txt\"."

if B_SCRIPT_SQLITE:
    # se genera script *.sql que permite importar los archivos *.csv a una BD Sqlite3
    f = open("script.sql", "w")
    f.write(createSqliteScript(G))
    f.close()
    print "Script Sqlite generated as \"script.sql\"."



