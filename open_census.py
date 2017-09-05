#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

__author__  = "Boris Sotomayor"
__email__   = "bsotomayor92@gmail.com"
__version__ = "05/09/17"

"""
Script que permite obtener una serie de consultas en lenguaje propio de Redatam 7 almacenándolo en un archivo *.txt.
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
    fo = open(FILE_PATH, "r")
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
def createSqliteScript(G, path):
    print "[INFO] Generación de script Sqlite en Proceso"
    str_sql = ".separator ;\n.mode csv\n\n"
    for E in G.entities:
        if E.selectable: 
            str_sql += "/* TABLE \"%s\" */\n" % (E.name)
            str_sql += "CREATE TABLE %s (REDCODE" % (E.name)
            for V in E.variables:
                str_sql += ", %s" % (V.name)
            str_sql += ");\n"
            str_sql += ".import %s%s.csv %s\n\n" % (path, E.name, E.name)
        else:
            for V in E.variables:
                if V.rangemax <= 255: # added AUG 21
                    if len(V.value_labels)!=0: # create tables with value labels (not empty tables..)
                        str_sql += "/* TABLE \"%s_%s\" */\n" % (E.name, V.name)
                        str_sql += "CREATE TABLE %s_%s (REDCODE, " % (E.name, V.name)

                        for i in range(V.rangemin, V.rangemax+1):
                            if i<0:
                                i = "_%i" % abs(i)
                            str_sql += "F_%s, " % i

                        str_sql += "F_T);\n"
                        str_sql += ".import %s%s_%s.csv %s_%s\n\n" % (path, E.name, V.name, E.name, V.name)
    print "[INFO] Generación de script Sqlite Terminado"
    return str_sql
 
"""
Método que permite obtener una serie de consultas para extraer datos de forma masiva de una base de datos Redatam.

Parámetros de entrada:
* G (List) : Lista de entidades.
* path (String) : Ruta en donde se almacenan los archivos *.csv tras consultar en Redatam. El script para sqlite3 buscará en esta ruta los archivos *.csv
* unit (String) : Unidad de área geográfica con la que se extraerán los datos. Ejemplos: REGION, PROVINCIA, ZONA, COMUNA, MANZENT, etc.

Retorna un string que contiene la serie de consultas escritas en lenguaje propio de Redatam.
"""
def dumpQueries(G, path, unit): 
    print "[INFO] Generación de consultas Redatam 7 en Proceso"
    script_str = "RUNDEF open_census\n\tSELECTION ALL\n\n"
    for E in G.entities:
        if E.selectable: 
            script_str += "// Codes of %s\n" % E.name
            script_str += str("TABLE %s\n\tAS AREALIST\n\tOF %s" % (E.name, E.name))
            for V in E.variables:
                script_str += str(", %s.%s 10.0" % (E.name, V.name))
            script_str += "\n\tOUTPUTFILE CSV \"%s%s.csv\"\n\tOVERWRITE\n\n" % (path, E.name)
        else:
            for V in E.variables:
                if V.rangemax <= 255: # added AUG 21
                    script_str += "// %s-Level Data (Variable %s.%s)\n" % (unit.upper(), E.name, V.name)
                    script_str += str("TABLE %s_%s\n\tAS AREALIST\n\tOF %s, %s.%s 10.0\n\tOUTPUTFILE CSV \"%s%s_%s.csv\"\n\tOVERWRITE\n\n" % (E.name, V.name, unit, E.name, V.name, path, E.name, V.name))
    
    print "[INFO] Generación de consultas Redatam 7 Terminada"
    return script_str

def replaceAcuteHTML(str_t):
    for c in str_t:
        if   (ord(c) == 225):
            str_t = str_t.replace(c,"&aacute")
        elif (ord(c) == 233):
            str_t = str_t.replace(c,"&eacute")
        elif (ord(c) == 237):
            str_t = str_t.replace(c,"&iacute")
        elif (ord(c) == 243):
            str_t = str_t.replace(c,"&oacute")
        elif (ord(c) == 250):
            str_t = str_t.replace(c,"&uacute")
        elif (ord(c) == 241):
            str_t = str_t.replace(c,"&ntilde")
        elif (ord(c) == 193):
            str_t = str_t.replace(c,"&Aacute")
        elif (ord(c) == 201):
            str_t = str_t.replace(c,"&Eacute")
        elif (ord(c) == 205):
            str_t = str_t.replace(c,"&Iacute")
        elif (ord(c) == 211):
            str_t = str_t.replace(c,"&Oacute")
        elif (ord(c) == 218):
            str_t = str_t.replace(c,"&Uacute")
        elif (ord(c) == 209):
            str_t = str_t.replace(c,"&Ntilde")
        elif (ord(c) == 220):
            str_t = str_t.replace(c,"&Uuml")
    return str_t


"""
### TEST ###

Método que genera un archivo HTML con la documentación de las entidades, variables y campos obtenidos de Redatam.
En éste se muestran las diferentes tablas obtenidas, los campos de cada variable/entidad y la descripción (etiquetas) de cada una de ellas ingresadas en Redatam.

Parámetros de entrada:
* G (List) : Lista de entidades.

Retorna un string con el HTML del documento.

"""
def createDocumentation(G):   
    str_style = "table {\n\tfont-family: arial, sans-serif;\n\tborder-collapse: collapse;\n\twidth: 60%;\n}\ntd, th {\n\tborder: 1px solid #dddddd;\n\ttext-align: left;\n\tpadding: 8px;\n}tr:nth-child(even) {\n\tbackground-color: #dddddd;\n}\n"
    str_bootstrap = "<link rel=\"stylesheet\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css\">"
    str_doc = "<!DOCTYPE html>\n<html>\n<head>\n%s\n<style>%s</style>\n <meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\" />\n</head>\n<body>\n" % (str_bootstrap, str_style)

    str_doc += "\t<h2 align=\"center\"> Diccionario de Base de datos (%s)</h2>\n\t<h3 align=\"center\">%s</h3>\n\t<br/>\n" % (replaceAcuteHTML(G.name), replaceAcuteHTML(G.label))
    for E in G.entities:

        if (not E.selectable):
            for i in range(len(E.variables)):
                V = E.variables[i]
                if V.rangemax <= 255:
                    str_doc += "\t<h3 align=\"center\">TABLA %s_%s</h3>\n" % (replaceAcuteHTML(E.name), replaceAcuteHTML(V.name))
                    str_doc += "\t<p align=\"center\"><i>%s</i></p>\n" % (replaceAcuteHTML(V.label))
                    
                    str_doc += "\t<div style=\"overflow-x:auto;\">\n"
                    str_doc += "\t<table align=\"center\">\n"
                    str_doc += "\t\t<tr>\n\t\t\t<th><b>Nombre del campo</b></th>\n\t\t<th><b>Descripci&oacuten</b></th>\n\t\t</tr>\n"
                    for vl in V.value_labels:
                        str_doc += "\t\t<tr>\n\t\t\t<th>%s</th>\n\t\t\t<th>%s</th>\n\t\t</tr>\n" % (vl.name.replace("VL","F_"), replaceAcuteHTML(vl.value))
                    if (len(V.value_labels))!=0:
                        str_doc += "\t\t<tr>\n\t\t\t<th>F_T</th>\n\t\t\t<th>TOTAL</th>\n\t\t</tr>\n"
                    
                    str_doc += "\t</table>\n"
                    str_doc += "\t</div>\n"
                    str_doc += "\t<br/>\n"
        else:
            str_doc += "\t<h3 align=\"center\">TABLA %s</h3>\n" % (replaceAcuteHTML(E.name))
            str_doc += "\t<p align=\"center\"><i>%s</i></p>\n" % (replaceAcuteHTML(E.label))
            
            str_doc += "\t<div style=\"overflow-x:auto;\">\n"
            str_doc += "\t<table align=\"center\">\n"
            for i in range(len(E.variables)):
                if (i == 0) :
                    str_doc += "\t\t<tr>\n\t\t\t<th><b>Nombre del campo</b></th>\n\t\t<th><b>Descripci&oacuten</b></th>\n\t\t</tr>\n"
                    for i in range(len(E.variables)):
                        V = E.variables[i]
                        str_doc += "\t\t<tr>\n\t\t\t<th>%s</th>\n\t\t\t<th>%s</th>\n\t\t</tr>\n" % (replaceAcuteHTML(V.name), replaceAcuteHTML(V.label))
            str_doc += "\t</table>\n"
            str_doc += "\t</div>\n"
            str_doc += "\t<br/>\n"
    str_doc += "\t<br/>\n"
    str_doc += "<p align=\"center\"> Diccionario de datos creado con Framework <i>Open Census</i>. Proyecto <i>Eigencities</i>. </p>\n<br/>\n"
    str_doc += "</body>\n</html>"
    return str_doc

"""
Método que procesa los argumentos escritos en consola al ejecutar el script.

Parámetros de entrada:
* argv (List) : Lista de argumentos escritos en consola.

Retorna la ruta del archivo, la ruta de la carpeta con archivos *.dbf, el nivel geográfico a utilizar y si generar el script sqlite3 o no (valor booleano)
"""
def readArgs(argv):
    PATH_FILE, PATH_CSV_FILES, LEVEL = "","",""

    if len(sys.argv) > 0:

        # valores por defecto:
        PATH_FILE = "./"
        PATH_CSV_FILES = "C:/"
        LEVEL = "MANZENT"

        str_out = ""

        # obtenemos opciones desde consola
        for i in range(len(argv)):
            flag = argv[i]

            if (flag == "--wxp_file"):
                PATH_FILE = argv[i+1]
                str_out +="[INFO] Archivo de entrada: '%s'\n" % PATH_FILE

            elif (flag == "--csv_folder"):
                PATH_CSV_FILES = argv[i+1]
                if (PATH_CSV_FILES[-1:]!="/"):
                    PATH_CSV_FILES += "/"

            elif (flag == "--level"):
                LEVEL = argv[i+1]
    
        # outputs obligatorios
        if PATH_CSV_FILES=="C:/":
            str_out +="[WARN] Carpeta para CSVs: '%s' (valor por defecto)\n" % PATH_CSV_FILES
        else:
            str_out +="[INFO] Carpeta para CSVs: '%s'\n" % PATH_CSV_FILES
        if LEVEL == "MANZENT":
            str_out +="[WARN] Nivel: '%s' (valor por defecto)\n" % LEVEL
        else:
            str_out +="[INFO] Nivel: '%s'" % LEVEL

    print str_out
    return PATH_FILE, PATH_CSV_FILES, LEVEL

# --

def main():
    # se capturan los diferentes parámetros ingresados por consola
    PATH_FILE, PATH_CSV_FILES, LEVEL = readArgs(sys.argv)

    # nombre por defecto de archivo de consultas Redatam 7
    fn_redatam_queries = "redatam_queries.txt"
    # nombre por defecto de archivo para importar archivos *.csv a Sqlite3
    fn_script_sqlite3  = "script.sql"

    # se procesa el archivo "*.wxp" para 
    if PATH_FILE!="" :
        G = readWXP(PATH_FILE)

        if LEVEL!="":
            # se genera archivo *.txt con queries Redatam
            f = open(fn_redatam_queries, "w")
            f.write(dumpQueries(G, PATH_CSV_FILES, LEVEL))
            f.close()
            print "[INFO] Archivo de consultas fue generado como \"%s\"\n" % fn_redatam_queries

            # se genera script *.sql que permite importar los archivos *.csv a una BD Sqlite3
            f = open(fn_script_sqlite3, "w")
            f.write(createSqliteScript(G, path=PATH_CSV_FILES))
            f.close()
            print "[INFO] Script Sqlite3 fue generado como \"%s\"" % fn_script_sqlite3

            # se genera documentación en html con la información
            f = open("documentation.html","w")
            f.write(createDocumentation(G))
            f.close()
            print "[TEST] documentacion generada como \"%s\"" % "documentation.html"

if __name__ == '__main__':
    main()


