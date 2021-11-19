# -*- coding: utf-8 -*-
"""
@author: Renato Barresi
Contrib: Gabriel Alonzo

Version 1.1 07/04/2020

TODO: 
	  -Tuitear llamados que excedan mil millones de guaranies
	  -Si el proveedor tiene nombre de fantasia, utilizar ese nombre a la hora de tuitear los proveedores adjudicados
	  -Pasar codigo a OOP
"""

from bs4 import BeautifulSoup as bs
import requests
import pandas as pd
import tweepy
import time

"""
	Descripcion
    
    Funcion que espera como entrada un diccionario que contiene las licitaciones anteriores, un diccionario que contiene las licitaciones actualizadas, nombre (?)

	Parametros

	Retorna
"""
def detectChange(dicOld,dicNew, nombres):

	print("Detectando cambios...")

	flag = True
	lista_licitaciones = []
	lista_info = []

	for key in dicNew:
		licitaciones = ""
		if((key in dicOld) == False):
			flag = False
			#priprv_slug_int("########################")
			#print(("Se agrego el PAC con ID: %d, Nombre: %s") % (key, nombres[key]))
			#print("########################")
			#licitaciones += "Se agrego el PAC con ID:" + str(key) + ", Nombre: " + #nombres[key] + " "
		if((key in dicOld) == True):		
			#compara si es igual o no
			if(dicNew[key] != dicOld[key]):
				flag = False
				if dicNew[key] == "Adjudicada":
					try:
						monto, convoc = getPrice(key)
						monto_control = cleanMonto(monto)
						print(monto, convoc)
					except IndexError:
						monto = 'error :('
					if type(monto_control) != str:
						monto_control = "0"
					if(int(monto_control) >= 90000000):
						#print(("La licitacion con ID: %d, Nombre: %s, fue Adjudicada por: %s") % (key, nombres[key], monto))
						#licitaciones = "ID: " + str(key) + ", Nombre: " + nombres[key] + " Adjudicada, monto: " + monto
						if(detect_denuncias(key) == -1):
							prot = "NO"
						else:
							prot = "SI"
						licitaciones =  "Monto: " + monto + ", Protestas: " + prot + ", Nombre: " + nombres[key] + ", ID: " + str(key)
						prv, link, prv_slug = adjudicados(key)

						ent_adj = "Convocante: " + convoc + ", Proveedor/es: "
						prv_slug_i = 0
						for a in prv:
							ent_adj += a + "(" + str(Cont_Adj_Win(obtener_link_proveedor(prv_slug[prv_slug_i]), convoc)) + ")" 
							#agregar cantidad de veces el proveedor gano para el convocante
							prv_slug_i = prv_slug_i + 1
							ent_adj += ", "
						
						if len(licitaciones) <= 280:			
							lista_info.append(licitaciones)
						else:
							licitaciones =  "Monto: " + monto + ", Protestas: " + prot + ", ID: " + str(key)
							lista_info.append(licitaciones)

						if len(ent_adj) <= 280:		
							lista_info.append(ent_adj)
						else:
							ent_adj = "Convocante: " + convoc
							lista_info.append(ent_adj)

						if len(link) <= 280:
							lista_info.append(link)
						else:
							link = "www.contrataciones.gov.py"
							lista_info.append(link)

						lista_licitaciones.append(lista_info)

						lista_info = []
						
	return lista_licitaciones, flag

"""
	Descripcion

    Funcion que espera un link (que contenga un .csv) y lo transforma a formato 
    dataFrame

	Parametros

    Entrada: link, formato string

	Retorna

    Salida: dataFrame, formato DataFrame

"""    

def getCsv(url):
    #print("Entrado a getCsv")


    #Requests
    page = requests.get(url)


    #Beautiful soup 4
    soup = bs(page.content, "html.parser")
    container = soup.find_all("div", {"class":"downloadTool"})
    link = "https://www.contrataciones.gov.py" + container[0].a['href']


    #Pandas
    df= pd.read_csv(link, error_bad_lines= False, delimiter = ";")
    return df

"""
	Descripcion

	Funcion Utilizada para comparar si existen licitaciones nuevas (compara un csv nuevo con uno viejo)

	Parametros

	link -> string  que debe contener el link proveniente del filtro de la pagina de la dncp
	filtro -> string que se utliza para crear el dataframe

	Retorna

	var -> string que indica al bot que no hay nada nuevo que tuitear
	licPalBot -> lista que contiene los datos de las licitaciones a tuitear


"""

def actualizarLic(link, filtro):
	print("Detectando cambios...")

	try:
		oldDf = pd.read_csv("oldDf"+str(filtro)+".csv")	
	except FileNotFoundError:
		oldDf = pd.read_csv("all.csv")
	
	print("Creando nuevo dataFrame...")
	newDf = getCsv(link)
	print("Nuevo dataFrame creado!")
	
	estadosNew = dict(zip(newDf.nro_licitacion, newDf.etapa_licitacion))
	estadosOld = dict(zip(oldDf.nro_licitacion, oldDf.etapa_licitacion))
	nombres = dict(zip(newDf.nro_licitacion, newDf.nombre_licitacion))
	
	licPalBot, flag = detectChange(estadosOld, estadosNew, nombres)
	
	newDf.to_csv("oldDf"+str(filtro)+".csv")
	
	if flag == True:
		var = "NO"
		return var
	else:
		return licPalBot

"""
	Descripcion

	Funcion encargada de 'limpiar' el monto de la licitacion

	Parametro/s

	number -> monto sacado directo del codigo html de la pagina de contrataciones

	return

	newNum -> monto de la licitacion sin ningun caracter basura
"""

def cleanMonto(number):
    newNum = ''
    if(number[0] == 'U'):
        for i in range(0, len(number[4:])):
            if(number[4:][i] == ','):
                return int(newNum)*6100
            if (number[4:][i] != '.'):
                newNum += number[4:][i]
                
        return int(newNum)*6100
    if(number[0] == '₲'):
        for i in range(0, len(number[2:])):
            if (number[2:][i] != '.') and (number[2:][i] != ','):
                newNum += number[2:][i]
        return newNum

"""
	Descripcion

	Funcion utilizada para obtener el monto de la licitacion y el convocante (el CSV proveido por la dncp no incluye el monto de la licitacion)

	Parametro/s

	ID_Licitacion -> ID de la licitacion la cual se quiere obtener el monto

	Retorna

	num -> Monto de la licitacion
	convocante -> La entidad que llamo a licitacion
"""

def getPrice (ID_Licitacion):
   urlInicial = 'https://contrataciones.gov.py/buscador/general.html?filtro=' + str(ID_Licitacion) + '&page='
   page = requests.get(urlInicial)
   soup = bs(page.content, "html.parser")
   
   containers = soup.find_all("div", {"class":"inline-actions visible-xs visible-sm"})
   urlFinal = "https://www.contrataciones.gov.py" + str(list(containers)[0].a['href'])
   
   page = requests.get(urlFinal)
   soup = bs(page.content, "html.parser")
   containers = soup.find_all("div", {"class":"col-sm-12"})
   convocante = containers[2].get_text()
   num = containers[8].get_text() 
   return num, convocante

"""
	Descpricion

	Funcion utilizada para detectar si existieron protestas en la licitacion

	Parametros

	ID_licitacion -> ID de la licitacion

	Retorna

	flag -> -1 si no existieron protestas, ditinto si existieron protestas

"""

def detect_denuncias(ID_Licitacion):
	urlInicial = 'https://contrataciones.gov.py/buscador/general.html?filtro=' + str(ID_Licitacion) + '&page='
	page = requests.get(urlInicial)
	soup = bs(page.content, "html.parser")

	containers = soup.find_all("div", {"class":"inline-actions visible-xs visible-sm"})
	urlFinal = "https://www.contrataciones.gov.py" + str(list(containers)[0].a['href'])
	urlFinal = urlFinal[:47] + "convocatoria/" + urlFinal[60:len(urlFinal) -len("resumen-adjudicacion.html") -1] + ".html"
	#print(urlFinal)
	page = requests.get(urlFinal)
	soup2 = bs(page.content, "html.parser")
	ncontainer = soup2.find_all("ul", {"class":"nav nav-tabs ajax-tabs"})
	flag = str(ncontainer).find("Protestas/Denuncias")
	return flag

"""
	Descripcion
	
	Funcion utilizada para obtener los nombres de los oferentes adjudicados y el link de la licitacion

	Parametros

	ID_licitacion -> ID de la licitacion

	Retorna

	proveedor -> lista que contiene los nombres de los oferentes adjudicados
	return_url -> Link de la licitacion
"""

def adjudicados(id):

	ID_Licitacion = id
	urlInicial = 'https://contrataciones.gov.py/buscador/general.html?filtro=' + str(ID_Licitacion) + '&page='
	page = requests.get(urlInicial)
	soup = bs(page.content, "html.parser")

	containers = soup.find_all("div", {"class":"inline-actions visible-xs visible-sm"})
	urlFinal = "https://www.contrataciones.gov.py" + str(list(containers)[0].a['href'])
	return_url = urlFinal
	urlFinal = urlFinal[:len(urlFinal)-len("resumen-adjudicacion.html")] + "proveedores-adjudicados.csv"
	df = pd.read_csv(urlFinal, delimiter = ';')	
	proveedor = df.proveedor.values.tolist()
	proveedor_slug = df.proveedor_slug.tolist()

	return proveedor, return_url, proveedor_slug

"""

Descripcion

Funcion utilizada para obtener la cantidad de veces que el proveedor fue adjudicado con
licitaciones del convocante

Parametros

link_proveedor -> string que contiene link a pagina web donde esta toda la informacion proveedor
convocante -> string con el nombre del convocante

Retorna

int que contiene las veces que gano el proveedor para la entidad

"""

def Cont_Adj_Win (link_proveedor, convocante):
	url = link_proveedor[:-5] + "/adjudicaciones.csv"
	df = pd.read_csv(url, delimiter = ";")
	return (df.convocante == convocante).sum()
"""
Descripcrion

Funcion utilizada para obtener el link correspondiente al proveedor indicado

Parametros

slug_proveedor -> string que contiene el slug (parametro del csv de proveedores adjudicados)

Retorna

string que contiene el link a la pagina de informacion de los proveedores

"""
def obtener_link_proveedor(slug_proveedor):
	link = 'https://contrataciones.gov.py/proveedor/' + slug_proveedor + ".html"
	return link
	
"""
	Descripcion

	Parametros

	Retorna

"""

def OAuth():
	try:
		auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
		auth.set_access_token(access_token, access_token_secret)
		return auth
	except Exception as e:
		return None

"""
	Descripcion

	Funcion encargada de tuitear, espera una string y el id del tuit, retorna el id del ultimo tuit 

	Parametro/s

	msg -> Mensaje a tuitear
	id_rsp -> el id del tuit al cual se va a responder, si id_rsp = 0 este es el primer tuit

	Return

	id_rsp -> id del ultimo tuit tuiteado
"""

def bot_tweet(msg, id_rsp):
	try:
		if id_rsp == 0:
			id_rsp = api.update_status(status = msg).id
			print("Tuiteado!")
		else:
			api.update_status(status = msg, in_reply_to_status_id = id_rsp)
			print("Tuiteado!")
	except tweepy.TweepError as error:
		if error.api_code == 187:
			print("Duplicate message")
		if error.api_code == 135:
			print("Timestamp out of bounds")
		else:
			print("There was an exception")
	return id_rsp


if __name__ == "__main__":

	#Aca va el key, secret y token de tu bot
	consumer_key = "XXXXXXX"
	consumer_secret = "XXXXXXXXXX"
	access_token = "XXXXXXXXXXXXXXXX"
	access_token_secret = "XXXXXXXXXXXXx"

	#El link contiene los parametros de filtrado de las licitaciones 
	#link = "https://contrataciones.gov.py/buscador/licitaciones.html?nro_nombre_licitacion=&categorias%5B%5D=18&categorias%5B%5D=23&categorias%5B%5D=38&categorias%5B%5D=40&tipos_procedimiento%5B%5D=CD&tipos_procedimiento%5B%5D=CO&tipos_procedimiento%5B%5D=LPI&tipos_procedimiento%5B%5D=LPN&fecha_desde=01-01-2019&fecha_hasta=&tipo_fecha=EST&convocante_tipo=&convocante_nombre_codigo=&codigo_contratacion=&catalogo%5Bcodigos_catalogo_n4%5D=&page=1&order=&convocante_codigos=&convocante_tipo_codigo=&unidad_contratacion_codigo=&catalogo%5Bcodigos_catalogo_n4_label%5D="
	link = "https://contrataciones.gov.py/buscador/licitaciones.html?nro_nombre_licitacion=&categorias%5B%5D=17&categorias%5B%5D=18&categorias%5B%5D=19&categorias%5B%5D=20&categorias%5B%5D=21&categorias%5B%5D=22&categorias%5B%5D=23&categorias%5B%5D=24&categorias%5B%5D=25&categorias%5B%5D=26&categorias%5B%5D=27&categorias%5B%5D=28&categorias%5B%5D=29&categorias%5B%5D=30&categorias%5B%5D=31&categorias%5B%5D=32&categorias%5B%5D=33&categorias%5B%5D=34&categorias%5B%5D=35&categorias%5B%5D=36&categorias%5B%5D=37&categorias%5B%5D=38&categorias%5B%5D=39&categorias%5B%5D=40&categorias%5B%5D=41&tipos_procedimiento%5B%5D=CD&tipos_procedimiento%5B%5D=CO&tipos_procedimiento%5B%5D=LPI&tipos_procedimiento%5B%5D=LPN&fecha_desde=01-01-2019&fecha_hasta=&tipo_fecha=EST&convocante_tipo=&convocante_nombre_codigo=&codigo_contratacion=&catalogo%5Bcodigos_catalogo_n4%5D=&page=1&order=&convocante_codigos=&convocante_tipo_codigo=&unidad_contratacion_codigo=&catalogo%5Bcodigos_catalogo_n4_label%5D="
	old_df_name = "todas_categorias"

	oauth = OAuth()
	api = tweepy.API(oauth)


	lista = actualizarLic(link, old_df_name)    

	if lista != "NO":
		print("Preparando bot para tuitear")
		for items in lista:
			id = 0
			for item in items:
				if id == 0:
					id = bot_tweet(item, 0)
				else:
					bot_tweet(item, id)
			time.sleep(450)
	else:
		print("No hay nada para tuitear")
