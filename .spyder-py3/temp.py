#%%
f = open('C:/Users/Lucas/Desktop/ejercicios_python/Data/precios.csv','rt')
espacio = ""
for line in f:
    	row = line.split(',')
    	if row[0] == "Naranja":
        	espacio += row[1]
f.close()
print(espacio)

#%%
numero_valido=False
while not numero_valido:
    try:
        a = input('Ingresá un número entero: ')
        n = int(a)
        numero_valido = True
        print("El numero es válido")
    except:
        print('No es válido. Intentá de nuevo.')
print(f'Ingresaste {n}.')

#%%

def costo_total (archivo):
	with open(archivo, "rt") as f:
         costo = 0
         headers = next(f)
         for line in f:
             datos  = line.split(",")
             costo += int(datos[1]) * float(datos[2])
	return costo
   

costo = costo_total("C:/Users/Lucas/Desktop/ejercicios_python/Data/camion.csv")   	 
print(f"El costo total es {costo}.")

#%%
#2.3
f = open('C:/Users/Lucas/Desktop/ejercicios_python/Data/precios.csv','rt')
espacio = ""
for line in f:
    	row = line.split(',')
    	if row[0] == "Naranja":
        	espacio += row[1]
f.close()
print(espacio)

#%%

archivo = 'C:/Users/Lucas/Desktop/ejercicios_python/Data/precios.csv'
def buscar_precio(frutas, encontrado=True):
    precio = None
    with open(archivo,'rt') as f:
        for line in f:
            row = line.split(",")
            if row[0] == frutas:
                    precio = float(row[1])
                    break      
            
    if encontrado:
        if precio != None:
            print(f'El precio de un cajon de {frutas} es {precio}')
        else: 
            print(f'{frutas} no figura en el listado')
        #return precio  Lo comento para que no haya un out


#%%
def preguntar_edad(nombre):
    edad = int(input(f'ingresá tu edad {nombre}: '))
    if edad<0:
        raise ValueError('La edad no puede ser negativa.')
    return edad
for nombre in ['Pedro','Juan','Caballero']:
    try:
        edad = preguntar_edad(nombre)
        print(f'{nombre} tiene {edad} años.')
    except ValueError:
        print(f'{nombre} no ingresó una edad válida.')

#%%

import csv
f = open('C:/Users/Lucas/Desktop/ejercicios_python/Data/camion.csv')
rows = csv.reader(f)
headers = next(rows)
headers
['nombre', 'cajones', 'precio']
for row in rows:
        print(row)

#%%

import csv
f = open('../Data/camion.csv')
def costo_camion (f):
    costo = 0
    headers = next(f)
    for line in f:
        costo += int(line[1]) * float(line[2])
        
        return costo
   
   	 
print(f"El costo total es {costo}.")


#%%
#TUPLAS
s = ("Manzana", 100, 408.9)
Producto = s[0]
cantidad = s[1]
precio = s[2]

fruta, cajones, precio = s
print("costo:", cajones * precio)

#%%
#DICCIONARIOS

a = {
     "Fruta": "Manzana",
     "cajones": 100,
     "precio": 490.1
     }

print(a['Fruta'], a['cajones'])

#%%

import csv
with open("C:/Users/Lucas/Desktop/ejercicios_python/Data/camion.csv") as f:
       filas = csv.reader(f)
       next(filas)
       fila = next(filas)
       t = (fila[0], int(fila[1]), float(fila[2]))
       
       #costo = t[1] * t[2]
       #print(f"{costo:0.2f}")
       
       #almacena valores
       nombre, cajones, precio = t
       #print(cajones)
       
       d = {
           "nombre": fila[0],
           "cajones": int(fila[1]),
           "precio": float(fila[2])
           }
       
       d["fecha"] = (14, 8, 2020)
       d["cuenta"] = 12345
       
       #for k in d:
           #print(k, "=", d[k])
           
       
       items = d.items()
       #print(items)
       #for k, v in d.items():
           #print(k, "=", v)
           
       d = dict(d)
       print(d)
       
#%%
#def agregar_silabas_geringoso(palabra):
#	vocales = 'aeiou'
#	silabas = ['pa', 'pe', 'pi', 'po', 'pu']
#	resultado = ''
    #for letra in palabra:
 #       resultado += letra
 #       if letra in vocales:
  #      	resultado += silabas[vocales.index(letra)]

   # return resultado

#def traductor_geringoso(lista):
#	diccionario = {}
 #   for palabra in lista:
  #      traduccion = agregar_silabas_geringoso(palabra)
   #     diccionario[palabra] = traduccion
    #
    #return diccionario

#lista = ['banana', 'manzana', 'mandarina']

#diccionario_geringoso = traductor_geringoso(lista)

#for palabra, traduccion in diccionario_geringoso.items():
#	print(f'{palabra}: {traduccion}')
       
#%%
def leer_camion(nombre_archivo):
    camion_list = []
    with open(nombre_archivo, 'rt') as foo:
        headers = next(foo)
        for line in foo:
            row = line.split(",")
            camion = {"Nombre": row[0],
                      "cajones": int(row[1]),
                      "precio": float(row[2])
                      }
            camion_list.append(camion)
    return camion_list

camion = leer_camion('../Data/camion.csv')

def costo(camion_list):
        costo_del_camion = 0.0
        for camion in camion_list:
            costo_del_camion += camion["cajones"] * camion["precio"]          
        return costo_del_camion
costo_camion = costo(camion)
print("Costo del camión:", costo_camion)



def leer_precios(nombre_archivo):
    precios_cajon = {}
    with open(nombre_archivo, "rt") as f:
        for line in f:
            row = line.split(",")            
            try:
                precios_cajon[row[0]] = float(row[1])                    
            except IndexError:
                pass
        
                return precios_cajon    

lista_ventas = leer_precios("../Data/precios.csv")

 
def ventas(camion_list, lista_ventas):
    ventas_totales = 0.0
    for camion in camion_list:
        nombre_producto = camion["Nombre"]
        if nombre_producto in lista_ventas:
            precio_venta = float(lista_ventas[nombre_producto])
            ventas_totales += precio_venta * camion["cajones"]
    return ventas_totales

ventas_totales = ventas(camion, lista_ventas)

print("Ventas totales:", ventas_totales)
print("Ganancia:", round(ventas_totales - costo_camion))
ventas = ventas(camion, lista_ventas)
       

#%%
#SOLUCION DE ERROES

#Ejercicio 3.5
def tiene_a(expresion):
    n = len(expresion)
    i = 0
    while i<n:
        if expresion[i] == 'a' or 'A':   #El error era porque solo detectaba la a minuscula y no la mayuscula, lo corregí agregando el or
            return True
        else:
            return False
        i += 1

tiene_a('UNSAM 2020')
tiene_a('abracadabra')
tiene_a('La novela 1984 de George Orwell')
    
#Ejercicio 3.6
def tiene_a(expresion):   #Faltaban los :
    n = len(expresion)
    i = 0
    while i<n:   #Faltaban los :
        if expresion[i] == 'a' or 'A':   #Faltaban los :, el = es una asignacion, por lo que tendría que decir == y tambien el "or"
            return True
        i += 1
    return False   #Falso no estaba definido

tiene_a('UNSAM 2020')
tiene_a('La novela 1984 de George Orwell')

#Ejercicio 3.7
def tiene_uno(expresion):  #El error es que "1984" es un valor entero, y solo detecta strings, lo solucioné con las comillas
    n = len(expresion)
    i = 0
    tiene = False
    while (i<n) and not tiene:
        if expresion[i] == '1':
            tiene = True
        i += 1
    return tiene


tiene_uno('UNSAM 2020')
tiene_uno('La novela 1984 de George Orwell')
tiene_uno("1984")

#Ejercicio 3.8
def suma(a, b):
    c = a + b
    return c  #Basicamente el problema es que la función no devolvia el valor de c, por lo que agregue el return y asigne las variables por fuera de la funcion

a = 2
b = 3
c = suma(a, b)
print(f"La suma da {a} + {b} = {c}")

#Ejercicio 3.9
import csv
from pprint import pprint

def leer_camion(nombre_archivo):
    camion=[]
    with open(nombre_archivo,"rt") as f:
        filas = csv.reader(f)
        encabezado = next(filas)
        for fila in filas:
            registro = {
                "Nombre": fila[0],
                "Cajones": int(fila[1]),
                "Precio": float(fila[2])
                } #El problema es que se sobreescribe la informacion dentro del diccionario, y lo que hice, fue crear el diccionario adentro del for y las asignaciones las mantuve
            camion.append(registro)
    return camion

camion = leer_camion('../Data/camion.csv')
pprint(camion)

#%%
import csv
import sys

def costo_camion(nombre_archivo):
    with open(nombre_archivo, "rt") as f:
        costo = 0
        headers = next(f)
        for line in f:
             datos  = line.split(",")
             try:
                 costo += int(datos[1]) * float(datos[2])
             except ValueError:
                 pass

    return costo

if len(sys.argv) == 2:
    nombre_archivo = sys.argv[1]
else:
    nombre_archivo = '../Data/camion.csv'

costo = costo_camion(nombre_archivo)
print('Costo total:', costo)

#%%

import csv
def costo_camion(archivo):
    with open(archivo, "rt") as f:
        rows = csv.reader(f)
        costo_total = 0
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start=1):
            record = dict(zip(headers, fila))
            try:
                ncajones = int(record['cajones'])
                precio = float(record['precio'])
                costo_total += ncajones * precio

            except ValueError:
            	print(f"Fila {n_fila}: No puede interpretar {fila}")       	 
    return costo_total

costo1=costo_camion("../Data/fecha_camion.csv")
print(costo1)

#%%
import csv
def leer_camion(nombre_archivo):
    costo_del_camion = 0.0
    camion_list = []
    with open(nombre_archivo, 'rt') as foo:
        rows = csv.reader(foo)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start = 1):
            camion_dict = dict(zip(headers, fila))
            try:
                nombre = camion_dict["nombre"]
                cajones = int(camion_dict["cajones"])
                precio = float(camion_dict["precio"])
                #costo_del_camion += cajones * precio
                camion_list.append(camion_dict)
            except ValueError:
                print(f"Fila {n_fila}: No puede interpretar {fila}")
                
            
        print(camion_list)
            
    return camion_list

camion = leer_camion('../Data/camion.csv')



#%%
import csv
def leer_camion(nombre_archivo):
    costo_del_camion = 0.0
    camion_list = []
    with open(nombre_archivo, 'rt') as foo:
        rows = csv.reader(foo)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start = 1):
            camion_dict = dict(zip(headers, fila))
            try:
                nombre = camion_dict["nombre"]
                cajones = int(camion_dict["cajones"])
                precio = float(camion_dict["precio"])
                camion_list.append(camion_dict)
            except ValueError:
                print(f"Fila {n_fila}: No puede interpretar {fila}")
                
            
        #print(camion_list)
            
    return camion_list

camion = leer_camion('../Data/fecha_camion.csv')

def costo(camion_list):
        costo_del_camion = 0.0
        for camion in camion_list:
            costo_del_camion += int(camion["cajones"]) * float(camion["precio"])          
        return costo_del_camion
costo_camion = costo(camion)
print("Costo del camión:", costo_camion)


def leer_precios(nombre_archivo):
    precios_cajon = {}
    with open(nombre_archivo, "rt") as f:  #Como no tengo headers, no podría usar la funcion zip
        for line in f:
            row = line.split(",")            
            try:
                precios_cajon[row[0]] = float(row[1])                    
            except IndexError:
                pass
        
                return precios_cajon    

lista_ventas = leer_precios("../Data/precios.csv")

 
def ventas(camion_list, lista_ventas):
    ventas_totales = 0.0
    for camion in camion_list:
        nombre_producto = camion["nombre"]
        if nombre_producto in lista_ventas:
            precio_venta = float(lista_ventas[nombre_producto])
            ventas_totales += precio_venta * int(camion["cajones"])
    return ventas_totales

ventas_totales = ventas(camion, lista_ventas)

print("Ventas totales:", ventas_totales)
print("Ganancia:", round(ventas_totales - costo_camion))
ventas = ventas(camion, lista_ventas)


#%%

lista_precios = list(zip(lista_ventas.values(),lista_ventas.keys())) #DEVUELVE PARES VALOR CLAVE
lista_ventas.items()  #DEVUELVE LOS ITEMS DE LA LISTA

#CON EL DE LISTA_PRECIOS, PODES APLICAR FUNCIONES COMO : MIN(LISTA_PRECIOS), MAX(LISTA_PRECIOS), SORTED(LISTA_PRECIOS) ESTE ULTIMO PARA SEPARAR POR COMAS

#%%

import csv
def leer_camion(nombre_archivo):
    costo_del_camion = 0.0
    camion_list = []
    with open(nombre_archivo, 'rt') as foo:
        rows = csv.reader(foo)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start = 1):
            camion_dict = dict(zip(headers, fila))
            try:
                nombre = camion_dict["nombre"]
                cajones = int(camion_dict["cajones"])
                precio = float(camion_dict["precio"])
                camion_list.append(camion_dict)
            except ValueError:
                print(f"Fila {n_fila}: No puede interpretar {fila}")
                    
        #print(camion_list)
            
    return camion_list

camion = leer_camion('../Data/camion.csv')
from collections import Counter

tenencias = Counter()
for s in camion:
    tenencias[s["nombre"]] += int(s["cajones"])

tenencias.most_common(3)


from collections import Counter
camion2 = leer_camion("../Data/camion2.csv")
tenencias2 = Counter()
for s in camion2:
          tenencias2[s['nombre']] += int(s['cajones'])
          
          
combinada = tenencias + tenencias2

#%%

nombre = 'Naranja'
cajones = 100
precio = 91.1
print(f'{nombre:>10s} {cajones:>10d} {precio:>10.2f}')

s = {
    'nombre': 'Naranja',
    'cajones': 100,
    'precio': 91.1
}
'{nombre:>10s} {cajones:10d} {precio:10.2f}'.format_map(s)

value = 42863.1
print(value)
print(f'{value:0.4f}')
print(f'{value:>16.2f}')
print(f'{value:<16.2f}')
print(f'{value:*>16,.2f}')

#%%

import csv
def leer_camion(nombre_archivo):
    costo_del_camion = 0.0
    camion_list = []
    with open(nombre_archivo, 'rt') as foo:
        rows = csv.reader(foo)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start = 1):
            camion_dict = dict(zip(headers, fila))
            try:
                nombre = camion_dict["nombre"]
                cajones = int(camion_dict["cajones"])
                precio = float(camion_dict["precio"])
                camion_list.append(camion_dict)
            except ValueError:
                print(f"Fila {n_fila}: No puede interpretar {fila}")
                
            
        #print(camion_list)
            
    return camion_list

camion = leer_camion('../Data/camion.csv')

def costo(camion_list):
        costo_del_camion = 0.0
        for camion in camion_list:
            costo_del_camion += int(camion["cajones"]) * float(camion["precio"])          
        return costo_del_camion
costo_camion = costo(camion)
#print("Costo del camión:", costo_camion)


def leer_precios(nombre_archivo):
    precios_cajon = {}
    with open(nombre_archivo, "rt") as f:  #Como no tengo headers, no podría usar la funcion zip
        for line in f:
            row = line.split(",")            
            try:
                precios_cajon[row[0]] = float(row[1])                    
            except IndexError:
                pass
        
                return precios_cajon    

lista_ventas = leer_precios("../Data/precios.csv")

 
def ventas(camion_list, lista_ventas):
    ventas_totales = 0.0
    for camion in camion_list:
        nombre_producto = camion["nombre"]
        if nombre_producto in lista_ventas:
            precio_venta = float(lista_ventas[nombre_producto])
            ventas_totales += precio_venta * int(camion["cajones"])
    return ventas_totales

ventas_totales = ventas(camion, lista_ventas)

#print("Ventas totales:", ventas_totales)
#print("Ganancia:", round(ventas_totales - costo_camion))
ventas = ventas(camion, lista_ventas)

def hacer_informe(camion, lista_ventas):
    tabla = []
    for producto in camion:
        nombre_producto = producto["nombre"]
        if nombre_producto in lista_ventas:
            cambio = float(lista_ventas[nombre_producto]) - float(producto["precio"])
            lote = (nombre_producto, producto["cajones"], lista_ventas[nombre_producto], cambio)
            tabla.append(lote)
            
    return tabla

informe = hacer_informe(camion, lista_ventas)

headers = ('Nombre', 'Cajones', 'Precio', 'Cambio')
print(f"{headers[0]:>10s} {headers[1]:>10s} {headers[2]:>10s} {headers[3]:>10s}")
linea = ("----------", "----------", "----------", "----------")
print(f"{linea[0]:>10s} {linea[1]:>10s} {linea[2]:>10s} {linea[3]:>10s}")
for producto in informe:
    precio_con_signo = f"${ventas:.2f}"
    nombre_producto, cajones, precio_venta, cambio = producto
    print(f'{nombre_producto:>10s} {int(cajones):>10d} {precio_con_signo:>10s} {cambio:>10.2f}')

#%%
headers = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
linea = ("--------------------------------------------")

print(f"{headers[0]:>6s} {headers[1]:>3s} {headers[2]:>3s} {headers[3]:>3s} {headers[4]:>3s} {headers[5]:>3s} {headers[6]:>3s} {headers[7]:>3s} {headers[8]:>3s} {headers[9]:>3s}")
print(f"{linea}")

for numero in range(0, 10):
    tabla = f"{numero}:"   #Esta parte escribe lo de la izquierda del todo
    for segundo_numero in range(10):
        resultado = numero * segundo_numero
        tabla += f" {resultado:>3d}"
    print(tabla)


#%%
import csv
def leer_parque(nombre_archivo, parque):
    arboles_list = []
    with open(nombre_archivo, "rt", encoding='utf-8') as f:
        rows = csv.reader(f)
        headers = next(rows)
        #print(headers)
        for n_fila, fila in enumerate(rows, start=1):
            espacio_ve = fila[10]
            if espacio_ve == parque:
                arboles_dict = dict(zip(headers, fila))
                arboles_list.append(arboles_dict)
                
        #print(arboles_list)        
        
    return arboles_list

especie_a_cambiar = "Plátano"  #ESTE VALOR ES LA ESPECIE QUE CAMBIAS PARA AVERIGUAR LOS DATOS DE LA MISMA
parque = "CENTENARIO"   #ACA SE CAMBIA PARA SABER QUE PARQUE QUERES AVERIGUAR
arboles = leer_parque('../Data/arbolado-en-espacios-verdes.csv', parque)
    
#Ejercicio 4.14
def especies(arboles):
    especie = set()
    for arbol in arboles:
        especie.add(arbol["nombre_com"])
    return especie

especie = especies(arboles)

#Ejercicio 4.15 
from collections import Counter
def contar_ejemplares(arboles):
    arboles_totales = Counter()
    for fila in arboles:
        nombre_com = fila["nombre_com"]
        arboles_totales[nombre_com] += 1
    return arboles_totales

arboles_totales = contar_ejemplares(arboles)
#print(arboles_totales)

arboles_totales.most_common(5)

#Ejercicio 4.16
def obtener_alturas(arboles, especie):
    lista = []
    for fila in arboles:
        if fila["nombre_com"] == especie:
            lista.append(float(fila["altura_tot"]))
        
    return lista
lista_alturas = obtener_alturas(arboles, especie_a_cambiar)
#print(lista_alturas)      

def altura_maxima(lista_alturas):
    altura_maxima = 0.0
    for arbol in arboles:
        altura_maxima_actual = float(arbol["altura_tot"])
        if altura_maxima_actual > altura_maxima:
            altura_maxima = altura_maxima_actual
            
    return altura_maxima

alturas_maxima = altura_maxima(arboles)
    

def promedio(lista_alturas):
    alturas = 0
    contador = 0
    for numero in lista_alturas:
        alturas += float(numero)
        contador += 1
    
    
    promedio = alturas/contador
    return promedio
promedios_altura = promedio(lista_alturas)


#Ejercicio 4.17
def obtener_inclinaciones(arboles, especie):
    lista_inclinaciones = []
    for fila in arboles:
        if fila["nombre_com"] == especie_a_cambiar:
            lista_inclinaciones.append(float(fila["inclinacio"]))
            
    return lista_inclinaciones
lista_inclinaciones = obtener_inclinaciones(arboles, especie_a_cambiar)

#Ejercicio 4.18
def especimen_mas_inclinado(arboles):
    inclinacion_maxima = 0.0
    for arbol in arboles:
        inclinacion_actual = float(arbol["inclinacio"])
        if inclinacion_actual > inclinacion_maxima:
            inclinacion_maxima = inclinacion_actual
        
    
    return inclinacion_maxima
inclinacion_maxima = especimen_mas_inclinado(arboles)

#Ejercicio 4.19
def especie_promedio_mas_inclinada(arboles):
    promedio_inclinaciones = 0
    contador = 0
    for numero in lista_inclinaciones:
        promedio_inclinaciones += float(numero)
        contador += 1
        
        
    promedio = promedio_inclinaciones/contador
    return promedio
promedio_de_inclinaciones = especie_promedio_mas_inclinada(arboles)
        

    
#%%
import csv
from collections import Counter

def leer_parque(nombre_archivo, parque):
    arboles_list = []
    with open(nombre_archivo, "rt", encoding='utf-8') as f:
        rows = csv.reader(f)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start=1):
            espacio_ve = fila[10]
            if espacio_ve == parque:
                arboles_dict = dict(zip(headers, fila))
                arboles_list.append(arboles_dict)
    return arboles_list

especie_a_cambiar = "Jacarandá"
parque = "CENTENARIO"
arboles = leer_parque('../Data/arbolado-en-espacios-verdes.csv', parque)

def especies(arboles):
    especie_set = set()
    for arbol in arboles:
        especie_set.add(arbol["nombre_com"])
    return especie_set

especie = especies(arboles)

def contar_ejemplares(arboles):
    arboles_totales = Counter()
    for fila in arboles:
        nombre_com = fila["nombre_com"]
        arboles_totales[nombre_com] += 1
    return arboles_totales

arboles_totales = contar_ejemplares(arboles)
print(arboles_totales.most_common(5))

def obtener_alturas(arboles, especie):
    lista = []
    for fila in arboles:
        if fila["nombre_com"] == especie:
            lista.append(float(fila["altura_tot"]))
    return lista

lista_alturas = obtener_alturas(arboles, especie_a_cambiar)

def altura_maxima(lista_alturas):
    altura_maxima = 0.0
    for altura_actual in lista_alturas:
        if altura_actual > altura_maxima:
            altura_maxima = altura_actual
    return altura_maxima

altura_maxima = altura_maxima(lista_alturas)
print(f"Altura máxima de {especie_a_cambiar}: {altura_maxima}")

def promedio(lista_alturas):
    alturas = 0
    contador = 0
    for numero in lista_alturas:
        alturas += float(numero)
        contador += 1
    promedio = alturas / contador
    return promedio

promedios_altura = promedio(lista_alturas)

def obtener_inclinaciones(arboles, especie):
    lista_inclinaciones = []
    for fila in arboles:
        if fila["nombre_com"] == especie:
            lista_inclinaciones.append(float(fila["inclinacio"]))
    return lista_inclinaciones

lista_inclinaciones = obtener_inclinaciones(arboles, especie_a_cambiar)

def especimen_mas_inclinado(arboles):
    inclinacion_maxima = 0.0
    for arbol in arboles:
        inclinacion_actual = float(arbol["inclinacio"])
        if inclinacion_actual > inclinacion_maxima:
            inclinacion_maxima = inclinacion_actual
    return inclinacion_maxima

inclinacion_maxima = especimen_mas_inclinado(arboles)

def especie_promedio_mas_inclinada(arboles):
    promedio_inclinaciones = 0
    contador = 0
    for numero in lista_inclinaciones:
        promedio_inclinaciones += float(numero)
        contador += 1
    promedio = promedio_inclinaciones / contador
    return promedio

promedio_de_inclinaciones = especie_promedio_mas_inclinada(arboles)

#%%

def tiene_a(expresion):
    n = len(expresion)
    i = 0
    for letra in expresion:    #SOLUCIONADO
        i += 1
        if i <= n:
            if letra == 'a':
                return True
            
    return False
            

rt = tiene_a('plbra')
print(rt)

#%%
def maximo(lista): 
    m = lista[0]     #Encontre la solucion asignandole como valor a m el primer elemento de la lista, lo cual permite iterar sobre todo el diccionario y no hayar problema con None por ejemplo   
    for e in lista:
        if e > m:
            m = e
    return m

def minimo(lista):
    m = lista[0]
    for e in lista:
        if e < m:
            m = e
    return m

#%%
    #Ejercicio 5.5
def invertir_lista(lista):
    invertida = []
    for e in lista:
        invertida.insert(0, e)
    return invertida

#%%
#Ejercicio 5.6
def propagar(lista):
    lista_propagada = lista.copy()
    for numero in range(len(lista)):
        if numero == 1 and lista[numero + 1] == 0:
            lista[numero + 1] == 1
    
    return lista_propagada
       
#%%
#Ejercicio 5.6
def propagar(lista):
    lista_propagada = lista.copy()
    for numero in range(len(lista_propagada)):
        if lista_propagada[numero] == 1:
            for elemento in range(numero + 1, len(lista_propagada)):
                if lista_propagada[elemento] == 0:
                    lista_propagada[elemento] = 1
                else:
                    break

    return lista_propagada

#%%
def leer_camion(nombre_archivo):
    camion_list = []
    with open(nombre_archivo, 'rt') as foo:
        headers = next(foo)
        for line in foo:
            row = line.split(",")
            camion = {"Nombre": row[0],
                      "cajones": int(row[1]),
                      "precio": float(row[2])
                      }
            camion_list.append(camion)
    return camion_list

camion = leer_camion('../Data/camion.csv')

def costo(camion_list):
        costo_del_camion = 0.0
        for camion in camion_list:
            costo_del_camion += camion["cajones"] * camion["precio"]          
        return costo_del_camion
costo_camion = costo(camion)
print("Costo del camión:", costo_camion)



def leer_precios(nombre_archivo):
    precios_cajon = {}
    with open(nombre_archivo, "rt") as f:
        for line in f:
            row = line.split(",")            
            try:
                precios_cajon[row[0]] = float(row[1])                    
            except IndexError:
                pass
        
                return precios_cajon    

lista_ventas = leer_precios("../Data/precios.csv")

 
def ventas(camion_list, lista_ventas):
    ventas_totales = 0.0
    for camion in camion_list:
        nombre_producto = camion["Nombre"]
        if nombre_producto in lista_ventas:
            precio_venta = float(lista_ventas[nombre_producto])
            ventas_totales += precio_venta * camion["cajones"]
    return ventas_totales

ventas_totales = ventas(camion, lista_ventas)

print("Ventas totales:", ventas_totales)
print("Ganancia:", round(ventas_totales - costo_camion))
ventas = ventas(camion, lista_ventas)

#%%
numes = [1,2,4,7]
cuadrados = [x * x for x in numes]
dobles = [x*2 for x in numes]
#%%

costo = sum([s["cajones"] * s["precio"] for s in camion] )

precio2 = sum([s["cajones"] * lista_ventas[s["Nombre"]] for s in camion])

#%%
mas100 = [s for s in camion if s["cajones"] > 100]

manynar = [s for s in camion if s["Nombre"] in {"Naranja", "Mandarina"}]

costo10k = [s for s in camion if s["cajones"] * s["precio"] > 10000]

#%%
nombre_cajones = [(s["Nombre"], s["cajones"]) for s in camion]

nombres = {s["Nombre"] for s in camion}

stock = {s["Nombre"]: 0 for s in camion}
for s in camion:
    stock[s["Nombre"]] += s["cajones"]
    
camion_precios = {nombre: precio[nombre] for nombre in nombres}

#%%
import csv
f = open('../Data/camion.csv')
rows = csv.reader(f)
headers = next(rows)

select = ['nombre', 'cajones', 'precio']
indices_columnas = [headers.index(ncolumna) for ncolumna in select]

row = next(rows)
record = {ncolumna : row[index] for ncolumna, index in zip(select, indices_columnas)}

camion = [{ ncolumna: row[index] for ncolumna, index in zip(select, indices_columnas)} for row in rows]


types = [str, int, float]
converted = [func(val) for func, val in zip(types, row)]

dict(zip(select, converted))    
                                            #HACEN LO MISMO
{ name: func(val) for name, func, val in zip(select, types, row) }

#%%
import csv
f = open('../Data/dowstocks.csv')
rows = csv.reader(f)
headers = next(rows)
row = next(rows)
#CONVERSION DE LOS DATOS
types = [str, float, str, str, float, float, float, float, int]

converted = [func(val) for func, val in zip(types, row)]
record = dict(zip(headers, converted))

#%%
import csv
def leer_parque(nombre_archivo, parque):
    arboles_list = []
    with open(nombre_archivo, "rt", encoding='utf-8') as f:
        rows = csv.reader(f)
        headers = next(rows)
        #print(headers)
        for n_fila, fila in enumerate(rows, start=1):
            espacio_ve = fila[10]
            if espacio_ve == parque:
                arboles_dict = dict(zip(headers, fila))
                arboles_list.append(arboles_dict)
                
        #print(arboles_list)        
        
    return arboles_list
arboles = leer_parque('../Data/arbolado-en-espacios-verdes.csv', 'CENTENARIO')

def leer_arboles(nombre_archivo):
    arboles_lista = []
    with open(nombre_archivo, 'rt', encoding='utf-8') as f:
        rows = csv.reader(f)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start=1):
            arboles_dict = dict(zip(headers, fila))
            arboles_lista.append(arboles_dict)
            
        return arboles_lista
arboleda = leer_arboles('../Data/arbolado-en-espacios-verdes.csv')

H = [float(arbol['altura_tot']) for arbol in arboleda if arbol['nombre_com'] == 'Jacarandá']        

Lista_altura_diametro = [ (arbol['altura_tot'], arbol['diametro']) for arbol in arboleda if arbol['nombre_com'] == 'Jacarandá']

#Ejercicio 5.18
especies = ['Eucalipto', 'Palo borracho rosado', 'Jacarandá']

def medidas_de_especies(especies, arboleda):
    medidas_por_especie = {}
    for especie in especies:
        Lista_altura_diametro_MODIFICADA = [ (arbol['altura_tot'], arbol['diametro']) for arbol in arboleda if arbol['nombre_com'] == especie]
        for arbol in arboleda:
            if arbol['nombre_com'] == especie:
                medidas_por_especie[especie] = Lista_altura_diametro_MODIFICADA
                
    return medidas_por_especie
medidas_por_especie = medidas_de_especies(especies, arboleda)
           
#%%

import random

tirada = []
for i in range(5):
    tirada.append(random.randint(1,6))
    
print(tirada)

#%%
import random
from collections import Counter
def tirar():
    tirada = []
    for i in range(5):
        tirada.append(random.randint(1,6))
    return tirada

tirada = tirar()

def es_generala(tirada):
    if tirada[0] == tirada[1] and tirada[1] == tirada[2] and tirada[2] == tirada[3] and tirada[3] == tirada[4]:
        return True
    else:
        return False
servida = es_generala(tirada)

def prob_generala(N):
    G = 0.0
    for i in range(N):
        tiradas = 0
        dado_valor = None
        dado_rep = 0
        while tiradas < 3:
            resultado_tirada = tirar()
            tiradas += 1
            if es_generala(resultado_tirada):
                G += 1
                break
        
            cant_repeticiones = Counter(resultado_tirada)  #cuanto se repitieron los valores
            valor_mas_repetido = cant_repeticiones.most_common(1)[0][0] #el valor mas repetiedo(most_common), el (1) es porque es el numero que mas veces se repite, el primer [0] para indicar que es la primer tupla, y el segundo [0] para el valor de esa tupla
        
            dado_valor = resultado_tirada.index(valor_mas_repetido) + 1 #Encuentra la primera posicion en la que aparece el valor_mas_repetido en resultado_tirada, y el +1 es porque el indice del numero mas repetido va a ser 0, y los dados empiezan a contar en 1
            resultado_tirada = [random.randint(1,6) if dado != dado_valor else dado for dado in resultado_tirada] #La nueva tirada solo toma dados que no se repitieron en dado_valor(mas repetidos)
    prob = G/N
    return prob

N = 10000
probabilidad = prob_generala(N)
print(probabilidad)

#%%
#Ejercicio 6.3
def cocoumpleaños(N):
    Dias = 365
    mismo_dia = 0
    lista = []
    for persona in range(N):
        lista.append(random.randint(1, 365))
    for e in lista:
        cumpleaños = random.randint(1, 365)
        if cumpleaños in lista:
            mismo_dia += 1 
            
    prob = mismo_dia/Dias
    return prob

N = 300
probabilidad = cocoumpleaños(N)
print(probabilidad)

#%%
#Ejercicio 6.4
import random

def envido(N):
    envido_mayor_31 = 0
    envido_mayor_32 = 0
    envido_mayor_33 = 0
    valores = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]
    palos = ['oro', 'copa', 'espada', 'basto']
    naipes = [(valor,palo) for valor in valores for palo in palos]
    for i in range(N):
        envido = 0
        mano = random.sample(naipes,k=3)
        if mano[0][1] == mano[1][1] or mano[0][1] == mano[2][1] or mano[1][1] == mano[2][1]:
           if mano [0][1] == mano[1][1]:
               envido = mano[0][0] + mano[1][0] + 20
           elif mano[0][1] == mano[2][1]:
               envido = mano[0][0] + mano[2][0] + 20
           elif mano[1][1] == mano[2][1]:
               envido = mano[1][0] + mano[2][0] + 20
    
        else:
            if mano[0][0] > mano[1][0] and mano[0][0] > mano[2][0]:
                envido = mano[0][0]
            elif mano[1][0] > mano[2][0] and mano[1][0] > mano[0][0]:
                envido = mano[1][0]
            elif mano[2][0] > mano[0][0] and mano[2][0] > mano[1][0]:
                envido = mano[2][0]
        
        if envido == 31:
            envido_mayor_31 += 1
        elif envido == 32:
            envido_mayor_32 += 1
        elif envido == 33:
            envido_mayor_33 += 1
            
    return envido_mayor_31, envido_mayor_32, envido_mayor_33
                
N = 100000
resultados = envido(N)
print(f'En {N} simulaciones:')
print(f'Envido mayor a 31: {resultados[0]} veces, la probabilidad de que salga este numero de envido es:', resultados[0]/N)
print(f'Envido mayor a 32: {resultados[1]} veces, la probabilidad de que salga este numero de envido es:', resultados[1]/N)
print(f'Envido mayor a 33: {resultados[2]} veces, la probabilidad de que salga este numero de envido es:', resultados[2]/N)          
        
#%%
#Ejercicio 6.6
import random
import numpy as np
        
def medir_temp(N):
    lista_temperaturas = []
    for i in range(N):
        lista_temperaturas.append(random.normalvariate(0,0.2))
        
    return lista_temperaturas
lista_temperaturas = medir_temp(N)

def resumen_temp(N):
    valores = []
    contador = 0
    lista_para_mediana = np.array(lista_temperaturas)
    valores.append(max(lista_temperaturas))
    valores.append(min(lista_temperaturas))
    valores.append(sum(lista_temperaturas)/N)
    valores.append(np.percentile(lista_para_mediana, 50))
        
    return valores
N = 1000
lista_resumida = resumen_temp(N)

#%%
import numpy as np
a = np.array([1, 2, 3])
np.zeros(2)  #0
np.ones(2)   #1
np.empty(2)  #valores guardados en la memoria
np.arange(2)#vectores que llegan hasta 2 sin incluir
np.arange(2, 9, 2)#vectores espaciados, del 2 al 9 sin incluir de 2 en 2
np.linspace(0, 10, num=5) #donde empieza, donde termina y cantidad de numeros totales
#%%
#Ejercicio 6.7
np.arange(1, 20, 2)
np.linspace(1, 19, num=10, dtype=np.int64) #vienen como float, por eso los cambio a int con dtype
#%%
import numpy as np
arr = np.array([2, 1, 5, 3, 7, 4, 6, 8]) 
np.sort(arr)  #ORDENA
a = np.array([1, 2, 3, 4])
b = np.array([5, 6, 7, 8])
np.concatenate((a, b))

x = np.array([[1, 2], [3, 4]])
y = np.array([[5, 6], [7, 8]])

a = np.concatenate((x, y), axis=1)

array_ejemplo = np.array([[[0, 1, 2, 3],
                           [4, 5, 6, 7]],

                           [[0, 1, 2, 3],
                            [4, 5, 6, 7]],

                           [[0 ,1 ,2, 3],
                            [4, 5, 6, 7]]])

array_ejemplo.ndim #numero dimensiones
array_ejemplo.shape #cant elementos en cada eje
array_ejemplo.size #tptal elementos (3*2*4)

a = np.arange(6)

b = a.reshape(3, 2) #reshape reordena el vector CON LA MISMA CANTIDAD DE ELEMENTOS

c = np.array([1, 2, 3, 4, 5, 6])
c.shape

vec_fila = c[np.newaxis, :] #AGREGA NUEVO EJE FILA
vec_fila.shape

vec_col = c[:, np.newaxis]
vec_col.shape               #AGREGA NUEVO EJE COLUMNA

data = np.array([1, 2, 3])
data[1]
data[0:2]
data[1:]

a = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])

print(a[a < 5]) #valores menores que 5 del array

five_up = (a >= 5)
print(a[five_up])

pares = a[a%2==0] #LOS PARES
print(pares)

c = a[(a > 2) & (a < 11)]
print(c)

mayores_cinco = (a > 5) | (a == 5)
print(mayores_cinco)

d = np.nonzero(a < 5)  #imprime los indices de los elementos menores que 5
print(d)

lista_coordenadas = list(zip(d[0], d[1])) #genera las coordenadas

for coord in lista_coordenadas:
    print(coord)

print(a[d])

e = np.array([1,  2,  3,  4,  5,  6,  7,  8,  9, 10])
arr1 = e[3:8]


a = np.array([[0.45053314, 0.17296777, 0.34376245, 0.5510652],
             [0.54627315, 0.05093587, 0.40067661, 0.55645993],
             [0.12697628, 0.82485143, 0.26590556, 0.56917101]])

a.min()
a.max()
a.min(axis=0)

np.random.random(3)  #genera el array de 3 numeros aleatorios
np.random.random((3, 2)) #genera la matriz

#%%
import random
import numpy as np
N = 999
def medir_temp(N):
    lista_temperaturas = []
    for i in range(N):
        lista_temperaturas.append(random.normalvariate(0,0.2))
        
    return lista_temperaturas
lista_temperaturas = medir_temp(N)

def resumen_temp(N):
    valores = []
    contador = 0
    lista_para_mediana = np.array(lista_temperaturas)
    valores.append(max(lista_temperaturas))
    valores.append(min(lista_temperaturas))
    valores.append(sum(lista_temperaturas)/N)
    valores.append(np.percentile(lista_para_mediana, 50))
        
    return valores

lista_resumida = resumen_temp(N)

np.save('temperaturas.npy', lista_temperaturas)

import matplotlib.pyplot as plt

def plotear_temperaturas():
    lista_temperaturas = np.load('temperaturas.npy')
    plt.hist(lista_temperaturas,bins=100)
    plt.show()
    
plotear_temperaturas()

#%%
import csv
import os
import matplotlib.pyplot as plt
def leer_arboles(nombre_archivo):
    arboles_lista = []
    with open(nombre_archivo, 'rt', encoding='utf-8') as f:
        rows = csv.reader(f)
        headers = next(rows)
        for n_fila, fila in enumerate(rows, start=1):
            arboles_dict = dict(zip(headers, fila))
            arboles_lista.append(arboles_dict)
            
        return arboles_lista
arboleda = leer_arboles('../Data/arbolado-en-espacios-verdes.csv')

#os.path.join('..', 'Data', 'arbolado-en-espacios-verdes.csv')
#altos = [float(arbol['altura_tot']) for arbol in arboleda if arbol['nombre_com'] == 'Jacarandá']
#plt.hist(altos,bins=10)



Lista_de_pares = [ (arbol['altura_tot'], arbol['diametro']) for arbol in arboleda if arbol['nombre_com'] == 'Jacarandá']
def scatter_hd(Lista_de_pares):
    d = sorted([diametro[0] for diametro in Lista_de_pares])
    h = sorted([altura[1] for altura in Lista_de_pares])
    
    plt.scatter(d, h)
    plt.xlabel("diametro (cm)")
    plt.ylabel("alto (m)")
    plt.title("Relación diámetro-alto para Jacarandás")
    plt.show() 
    return d, h

especies = ['Eucalipto', 'Palo borracho rosado', 'Jacarandá']

def medidas_de_especies(especies, arboleda):
    medidas_por_especie = {}
    for especie in especies:
        Lista_altura_diametro_MODIFICADA = [ (arbol['altura_tot'], arbol['diametro']) for arbol in arboleda if arbol['nombre_com'] == especie]
        for arbol in arboleda:
            if arbol['nombre_com'] == especie:
                medidas_por_especie[especie] = Lista_altura_diametro_MODIFICADA
                
    return medidas_por_especie
medidas_por_especie = medidas_de_especies(especies, arboleda)
import os
import matplotlib.pyplot as plt

os.path.join('..', 'Data', 'arbolado-en-espacios-verdes.csv')
arboleda = leer_arboles('../Data/arbolado-en-espacios-verdes.csv')
medidas = medidas_de_especies(especies, arboleda)

d_eucalipto = sorted([d[0] for d in medidas['Eucalipto']])
h_eucalipto = sorted([d[1] for d in medidas['Eucalipto']])
plt.scatter(d_eucalipto, h_eucalipto)
plt.xlabel('Diámetro')
plt.ylabel('Altura')
#plt.title('Scatter Plot de Diámetro vs. Altura para Eucalipto')

d_Jacarandá = sorted([d[0] for d in medidas['Jacarandá']])
h_Jacarandá = sorted([d[1] for d in medidas['Jacarandá']])
plt.scatter(d_Jacarandá, h_Jacarandá)
plt.xlabel('Diámetro')
plt.ylabel('Altura')
#plt.title('Scatter Plot de Diámetro vs. Altura para Jacarandá')

d_palo_borracho_rosado = sorted([d[0] for d in medidas['Palo borracho rosado']])
h_palo_borracho_rosado = sorted([d[1] for d in medidas['Palo borracho rosado']])
plt.scatter(d_palo_borracho_rosado, h_palo_borracho_rosado)
plt.xlabel('Diámetro')
plt.ylabel('Altura')
plt.title('Scatter Plot de Diámetro vs. Altura')

#%%
import random
import numpy as np
figus_total = 6
def crear_album(figus_total):
    album = [0 for figus in range(figus_total)]
    return album

A = crear_album(figus_total)

def album_incompleto(A):
    if 0 in A:
        return True
    else:
        return False


def comprar_figu(figus_total):
    figu = random.randint(1, figus_total)
    return figu


def cuantas_figus(figus_total):
        album = A
        cant_figus = 0
        while album_incompleto(album):
            figu = comprar_figu(figus_total)
            if album[figu - 1] == 0:  #el -1 porque en python las listas empiezan en 0
                album[figu - 1] = 1
            cant_figus += 1
        return cant_figus


#EJERCICIO 6.17
def cuantas_figus_promedio(figus_total):
        n_repeticiones = 1000
        lista_resultados = []
        while n_repeticiones > 0:
            album = crear_album(figus_total)
            cant_figus = 0
            while album_incompleto(album):
                figu = comprar_figu(figus_total)
                if album[figu - 1] == 0:  #el -1 porque en python las listas empiezan en 0
                    album[figu - 1] = 1
                cant_figus += 1
            n_repeticiones -= 1
            lista_resultados.append(cant_figus)
        return lista_resultados
#lista = cuantas_figus_promedio(figus_total)
#promedio = np.mean(lista)


#Ejercicio 6.18
def experimento_figus(n_repeticiones, figus_total):
    lista_resultados = []
    cantidad_figus = 0
    while n_repeticiones > 0:
        album = crear_album(figus_total)
        cant_figus = cuantas_figus(figus_total)
        while album_incompleto(album):
            figu = comprar_figu(figus_total)
            if album[figu - 1] == 0:
                album[figu - 1] = 1
            cantidad_figus +=1
        n_repeticiones -= 1
        lista_resultados.append(cantidad_figus)
    return lista_resultados
n_repeticiones = 100
lst = experimento_figus(n_repeticiones, figus_total)
promedio = np.mean(lst)


def cuantas_figus(figus_total):
    album = A
    cant_figus = 0
    while album_incompleto(A):
        figu = comprar_figu(figus_total)
        if album[figu - 1] == 0:  #el -1 porque en python las listas empiezan en 0
            album[figu - 1] == 1
            album.append(figu)
        cant_figus += 1
    return cant_figus
cant_figus = cuantas_figus(figus_total)

#%%
import csv
import numpy as np
from collections import Counter
def leer_parque(nombre_archivo, parque):
    lista = []
    with open(nombre_archivo, 'rt', encoding='utf-8') as f:
        rows = csv.reader(f)
        headers = next(rows)
        for fila in rows:
            espacio_ve = fila[10]
            if espacio_ve == parque:
                dct = dict(zip(headers, fila))
                lista.append(dct)
        return lista
lista_arboles = leer_parque('../Data/arbolado-en-espacios-verdes.csv', 'ANDES, LOS')

def especies(lista_arboles):
    especies = set()
    for arbol in lista_arboles:
        especies.add(arbol['nombre_com'])
    return especies
especies = especies(lista_arboles)

def contar_ejemplares(lista_arboles):
    contador = Counter()
    for fila in lista_arboles:
        contador[fila['nombre_com']] += 1
    return contador
cant_ejemplares = contar_ejemplares(lista_arboles)
mas_comunes = cant_ejemplares.most_common(5)  

def obtener_alturas(lista_arboles, especie):
    lista_alturas = []
    for arbol in lista_arboles:
        if arbol['nombre_com'] == especie:
            lista_alturas.append(float(arbol['altura_tot']))
    return lista_alturas
promedio_alturas = np.mean(obtener_alturas(lista_arboles, 'Jacarandá'))
altura_maxima = max(obtener_alturas(lista_arboles, 'Jacarandá'))
#%%
def contar_pares_impares(numeros):
    pares = []
    impares = []
    for numero in numeros:
        if numero % 2 == 0:  #Falta un igual
            pares.append(numero)
        else:
            impares.append(numero)
    return impares, pares

str_numeros = input("Ingrese una lista de números separados por comas: ")
numeros = [int(n) for n in str_numeros.split(",")]

impares, pares = contar_pares_impares(numeros)  #La funcion devuelve una tupla de la siguiente forma(impares, pares) y aca se decia (pares, impares)
print("Cantidad de números pares:", len(pares))
print("Cantidad de números impares:", len(impares))

#%%
import csv
def leer_estudiantes(archivo):
    lista = []
    with open(archivo, 'rt') as f:
        rows = csv.reader(f)
        headers = next(rows)
        for n_fila, fila in enumerate(rows):
            dct = dict(zip(headers, fila))
            lista.append(dct)
    return lista
lista_estudiantes = leer_estudiantes('../Data/alumnos.csv')

def promediar_regulares(lista_estudiantes):
    lista_regulares = []
    for estudiante in lista_estudiantes:
        if estudiante['condicion'] == 'REGULAR':
            prom = round((float(estudiante['nota_1']) + float(estudiante['nota_2']) + float(estudiante['nota_3'])) / 3, 2)
            estudiante['promedio'] = prom
            lista_regulares.append(estudiante)
    return lista_regulares
lista_regulares = promediar_regulares(lista_estudiantes)

def imprimir_notas(lista_estudiantes):
    for estudiante in lista_estudiantes:
        print(f'La primer nota del alumno: {estudiante["apellido"]} {estudiante["nombre"]} es: {estudiante["nota_1"]}')
        print(f'La segunda nota del alumno es: {estudiante["nota_2"]}')
        print(f'La tercer nota del alumno es: {estudiante["nota_3"]}')

#%%

import csv
def leer_estudiantes(archivo):
    lista = []
    with open(archivo, 'rt') as f:
        rows = csv.reader(f)
        headers = next(rows)
        for n_fila, fila in enumerate(rows):
            dct = dict(zip(headers, fila))
            lista.append(dct)
    return lista
#lista_estudiantes = leer_estudiantes('../Data/alumnos.csv')

def promediar_regulares(lista_estudiantes):
    lista_regulares = []
    for estudiante in lista_estudiantes:
        if estudiante['condicion'] == 'REGULAR':
            prom = round((float(estudiante['nota_1']) + float(estudiante['nota_2']) + float(estudiante['nota_3'])) / 3, 2)
            estudiante['promedio'] = prom
            lista_regulares.append(estudiante)
    return lista_regulares
#lista_regulares = promediar_regulares(lista_estudiantes)

def imprimir_notas(lista_estudiantes):
    for estudiante in lista_estudiantes:
        print(f'La primer nota del alumno: {estudiante["apellido"]} {estudiante["nombre"]} es: {estudiante["nota_1"]}')
        print(f'La segunda nota del alumno es: {estudiante["nota_2"]}')
        print(f'La tercer nota del alumno es: {estudiante["nota_3"]}')

if len(sys.argv) == 2:
    archivo = sys.argv[1]
else:
    archivo = '../Data/alumnos.csv'
#%%
import csv
def leer_estudiantes(archivo):
    with open(archivo, 'rt') as f:
        rows = csv.reader(f)
        headers = next(rows)
        lista_estudiantes = [dict(zip(headers, fila)) for fila in rows]
    return lista_estudiantes
lista_estudiantes = leer_estudiantes('../Data/alumnos.csv')

#%%
import csv
def parse_csv(nombre_archivo, select=None, types=None, has_headers=False):
    '''
    Parsea un archivo CSV en una lista de registros.
    '''
    lista = []
    with open(nombre_archivo) as f:
        rows = csv.reader(f)
        
        if has_headers:
            headers = next(rows)
            lista_ = [dict(zip(headers, fila)) for fila in rows]
            lista.append(lista_)
        else:
            for fila in rows:
                if types:
                    fila = tuple(func(valor) for func, valor in zip(types, fila))
                lista.append(fila)  #No se porque devuelve un () vacío
    
    return lista

#precios = parse_csv('../Data/precios.csv', types=[str, float], has_headers=False)

#%%
import csv
#%%
def leer_camion(nombre_archivo):
    '''Computa el precio total del camion (cajones * precio) de un archivo'''
    camion = []

    with open(nombre_archivo, 'rt') as f:
        filas = csv.reader(f)
        encabezados = next(filas)
        
        for n_fila, fila in enumerate(filas, start = 1):
            record = dict(zip(encabezados, fila))
            try:
                record['cajones'] = int(record['cajones'])
                record['precio'] = float(record['precio'])
                camion.append(record)
            except ValueError:
                print('Faltan datos en la línea', n_fila, 'del archivo.')

    return camion
#%%
import csv

def leer_camion(archivo_camion):
    '''Computa el precio total del camion (cajones * precio) de un archivo'''
    camion = []

    with open(nombre_archivo, 'rt') as f:
        filas = csv.reader(f)
        encabezados = next(filas)
        
        for n_fila, fila in enumerate(filas, start=1):
            record = dict(zip(encabezados, fila))
            try:
                record['cajones'] = int(record['cajones'])
                record['precio'] = float(record['precio'])
                camion.append(record)
            except ValueError:
                print('Faltan datos en la línea', n_fila, 'del archivo.')

    return camion

def leer_precios(archivo_precios):
    precios = {}
    with open(nombre_archivo, 'rt') as f:
        rows = csv.reader(f)
        for i, row in enumerate(rows):
            if row:
                precios[row[0]] = float(row[1])
    return precios

def parse_csv(archivo_camion, archivo_precios):
    camion = leer_camion(archivo_camion)
    precios = leer_precios(archivo_precios)
    
    lista = []
    for lote in camion:
        precio_venta = precios[lote['nombre']]
        cambio = precio_venta - lote['precio']
        t = (lote['nombre'], lote['cajones'], lote['precio'], cambio)
        lista.append(t)
    
    # Imprimir la tabla final
    print('    Nombre    Cajones     Precio     Cambio')
    print('---------- ---------- ---------- ----------')
    for nombre, cajones, precio, cambio in lista:
        precio = f'${precio}'
        print(f'{nombre:>10s} {cajones:>10d} {precio:>10s} {cambio:>10.2f}')


#%%
import informe_funciones
import csv
def leer_camion(nombre_archivo):
    camion_list = informe_funciones.leer_camion(nombre_archivo)            
    return camion_list   #Si no me equivoco pedía algo así, no terminé de entender el punto

camion = leer_camion('../Data/fecha_camion.csv')

def costo(camion_list):
        costo_del_camion = 0.0
        for camion in camion_list:
            costo_del_camion += int(camion["cajones"]) * float(camion["precio"])          
        return costo_del_camion
costo_camion = costo(camion)
print("Costo del camión:", costo_camion)


def leer_precios(nombre_archivo):
    precios_cajon = {}
    with open(nombre_archivo, "rt") as f:  #Como no tengo headers, no podría usar la funcion zip
        for line in f:
            row = line.split(",")            
            try:
                precios_cajon[row[0]] = float(row[1])                    
            except IndexError:
                pass
        
                return precios_cajon    

lista_ventas = leer_precios("../Data/precios.csv")

 
def ventas(camion_list, lista_ventas):
    ventas_totales = 0.0
    for camion in camion_list:
        nombre_producto = camion["nombre"]
        if nombre_producto in lista_ventas:
            precio_venta = float(lista_ventas[nombre_producto])
            ventas_totales += precio_venta * int(camion["cajones"])
    return ventas_totales

ventas_totales = ventas(camion, lista_ventas)

print("Ventas totales:", ventas_totales)
print("Ganancia:", round(ventas_totales - costo_camion))
ventas = ventas(camion, lista_ventas)



#%%
def busqueda_secuencial_comps(lista, x):
    '''Si x está en la lista devuelve el índice de su primera aparición, 
    de lo contrario devuelve -1. Además devuelve la cantidad de comparaciones
    que hace la función.
    '''
    comps = 0 # inicializo en cero la cantidad de comparaciones
    pos = -1
    for i,z in enumerate(lista):
        comps += 1 # sumo la comparación que estoy por hacer
        if z == x:
            pos = i
            break
    return pos, comps

#%%
def busqueda_lineal_ordenada(lista, e):
    '''Busca un elemento e en la lista.

    Si e está en lista devuelve el índice,
    de lo contrario devuelve -1.
    '''
    pos = -1
    for i in lista:
        if i > e:
            break
        elif i == e:
            pos = lista.index(i)
        
    return pos
            
#%%
def busqueda_binaria(lista, x):
    '''Búsqueda binaria
    Precondición: la lista está ordenada
    Devuelve -1 si x no está en lista;
    Devuelve p tal que lista[p] == x, si x está en lista
    '''
    pos = -1 # Inicializo respuesta, el valor no fue encontrado
    izq = 0
    der = len(lista) - 1
    while izq <= der:
        medio = (izq + der) // 2
        if lista[medio] == x:
            pos = medio     # elemento encontrado!
        if lista[medio] > x:
            der = medio - 1 # descarto mitad derecha
        else:               # if lista[medio] < x:
            izq = medio + 1 # descarto mitad izquierda
    if pos == -1:
        for i, valor in enumerate(lista):
            if x <= valor:
                lista.insert(i, x)
                return i
            else:
                return len(lista)
        

#%%
def insertar(lista, x):
    '''SI EL ELEMENTO SE ENCUENTRA EN LA LISTA,
    DEVUELVE LA POSICION, DE LO CONTRARIO DEVOLVERÁ
    LA LISTA CON EL ELEMENTO INSERTADO '''
    izq = 0
    der = len(lista) - 1

    while izq <= der:
        medio = (izq + der) // 2

        if lista[medio] == x:
            # Elemento encontrado, se puede insertar en la posición anterior a la repetición
            lista.insert(medio, x)
            return medio
        elif lista[medio] > x:
            der = medio - 1
        else:
            izq = medio + 1

    # Elemento no encontrado, se puede insertar en la posición izquierda
    lista.insert(izq, x)
    return izq

#%%
def incrementar(s):
    carry = 1
    l = len(s)
    
    for i in range(l-1,-1,-1):
        if (s[i] == 1 and carry == 1):
            s[i] = 0
            carry = 1
        else:
            s[i] = s[i] + carry
            carry = 0
    return s

#%%
def incrementar(s):
    carry = 1
    l = len(s)
    
    for i in range(l-1, -1, -1):
        if s[i] == 1 and carry == 1:
            s[i] = 0
            carry = 1
        else:
            s[i] = s[i] + carry
            carry = 0
    return s

def listar_secuencias(n):
    lista = []
    secuencias = [0] * n
    for secuencia in secuencias:
        secuencia = incrementar(secuencia)
        lista.append(secuencia)
    return lista
#%%
def incrementar(s):
    carry = 1
    l = len(s)
    
    for i in range(l-1, -1, -1):
        if s[i] == 1 and carry == 1:
            s[i] = 0
            carry = 1
        else:
            s[i] = s[i] + carry
            carry = 0
    return s

def listar_secuencias(n):
    lista = []
    secuencia = [0] * n
    
    while secuencia != [1] * n:
        lista.append(list(secuencia))
        incrementar(secuencia)
    lista.append([1] * n)
        
    return lista
#%%
def busqueda_binaria_comps(lista, x, verbose = False):
    if verbose:
        print(f'[DEBUG] izq |der |medio')
    pos = -1 # Inicializo respuesta, el valor no fue encontrado
    izq = 0
    der = len(lista) - 1
    comps = 0
    while izq <= der:
        comps +=1
        medio = (izq + der) // 2
        if verbose:
            print(f'[DEBUG] {izq:3d} |{der:>3d} |{medio:3d}')
        if lista[medio] == x:
            pos = medio     # elemento encontrado!
        if lista[medio] > x:
            der = medio - 1 # descarto mitad derecha
        else:               # if lista[medio] < x:
            izq = medio + 1 # descarto mitad izquierda
    return pos, comps


def busqueda_secuencial_comps(lista, x):
    comps = 0 # inicializo en cero la cantidad de comparaciones
    pos = -1
    for i,z in enumerate(lista):
        comps += 1 # sumo la comparación que estoy por hacer
        if z == x:
            pos = i
            break
    return pos, comps

import random

def generar_lista(n, m):
    l = random.sample(range(m), k = n)
    l.sort()
    return l

def generar_elemento(m):
    return random.randint(0, m-1)


def experimento_secuencial_promedio(lista, m, k):
    comps_tot = 0
    for i in range(k):
        x = generar_elemento(m)
        comps_tot += busqueda_secuencial_comps(lista,x)[1]

    comps_prom = comps_tot / k
    return comps_prom

def experimento_binario_promedio(lista, m, k):
    comps_totales = 0
    for i in range(k):
        x = generar_elemento(m)
        comps_totales += busqueda_binaria_comps(lista, x, verbose = False)[1]
        
    comparaciones_prom_binaria = comps_totales / k
    return comparaciones_prom_binaria
        

import matplotlib.pyplot as plt
import numpy as np

largos = np.arange(256) + 1 # estos son los largos de listas que voy a usar
comps_promedio = np.zeros(256) # aca guardo el promedio de comparaciones sobre una lista de largo i, para i entre 1 y 256.

for i, n in enumerate(largos):
    lista = generar_lista(n, m) # genero lista de largo n
    comps_promedio[i] = experimento_secuencial_promedio(lista, m, k)

# ahora grafico largos de listas contra operaciones promedio de búsqueda.
#plt.plot(largos,comps_promedio,label = 'Búsqueda Secuencial')
#plt.xlabel("Largo de la lista")
#plt.ylabel("Cantidad de comparaciones")
#plt.title("Complejidad de la Búsqueda")
#plt.legend()
#plt.show()


comps_promedio_binario = np.zeros(256)
for i, n in enumerate(largos):
    lista = generar_lista(n, m)
    comps_promedio_binario[i] = experimento_binario_promedio(lista, m, k)
plt.plot(largos, comps_promedio, label='Búsqueda Secuencial')
plt.plot(largos,comps_promedio_binario,label = 'Búsqueda Binaria')
plt.xlabel("Largo de la lista")
plt.ylabel("Cantidad de comparaciones")
plt.title("Complejidad de la Búsqueda")
plt.legend()
plt.xlim(0, 10)
plt.ylim(0, 10)
plt.show()
#%%
import matplotlib.pyplot as plt
import numpy as np
import random
m = 10000
k = 1000
n = 100
def generar_lista(n, m):
    l = random.sample(range(m), k = n)
    l.sort()
    return l


def generar_elemento(m):
    return random.randint(0, m-1)


def busqueda_secuencial_comps(lista, x):
    comps = 0 # inicializo en cero la cantidad de comparaciones
    pos = -1
    for i,z in enumerate(lista):
        comps += 1 # sumo la comparación que estoy por hacer
        if z == x:
            pos = i
            break
    return pos, comps


def busqueda_binaria_comps(lista, x, verbose = False):
    if verbose:
        print(f'[DEBUG] izq |der |medio')
    pos = -1 # Inicializo respuesta, el valor no fue encontrado
    izq = 0
    der = len(lista) - 1
    comps = 0
    while izq <= der:
        comps +=1
        medio = (izq + der) // 2
        if verbose:
            print(f'[DEBUG] {izq:3d} |{der:>3d} |{medio:3d}')
        if lista[medio] == x:
            pos = medio     # elemento encontrado!
        if lista[medio] > x:
            der = medio - 1 # descarto mitad derecha
        else:               # if lista[medio] < x:
            izq = medio + 1 # descarto mitad izquierda
    return pos, comps


def experimento_secuencial_promedio(lista, m, k):
    comps_tot = 0
    for i in range(k):
        x = generar_elemento(m)
        comps_tot += busqueda_secuencial_comps(lista,x)[1]

    comps_prom = comps_tot / k
    return comps_prom


def experimento_binario_promedio(lista, m, k):
    comps_totales = 0
    for i in range(k):
        x = generar_elemento(m)
        comps_totales += busqueda_binaria_comps(lista, x, verbose = False)[1]
        
    comparaciones_prom_binaria = comps_totales / k
    return comparaciones_prom_binaria


def graficar_bbin_vs_bseq(m, k):
    largos = np.arange(256) + 1
    comps_promedio = np.zeros(256)
    comps_promedio_binario = np.zeros(256)
    for i, n in enumerate(largos):
        lista = generar_lista(n, m) # genero lista de largo n
        comps_promedio[i] = experimento_secuencial_promedio(lista, m, k)
    for i, n in enumerate(largos):
        lista = generar_lista(n, m)
        comps_promedio_binario[i] = experimento_binario_promedio(lista, m, k)
    
    plt.plot(largos, comps_promedio, label='Búsqueda Secuencial')
    plt.plot(largos,comps_promedio_binario,label = 'Búsqueda Binaria')
    plt.xlabel("Largo de la lista")
    plt.ylabel("Cantidad de comparaciones")
    plt.title("Complejidad de la Búsqueda")
    plt.legend()
    plt.xlim(0, 10)
    plt.ylim(0, 10)
    plt.show()

#%%
import csv

def parse_csv(nombre_archivo, select = None, types = None, has_headers = False, silence_errors = True):
    encabezados = []
    with open(nombre_archivo) as f:
        filas = csv.reader(f)
        if select and not has_headers:
            raise RuntimeError("Para seleccionar, necesito encabezados.")
        if has_headers:
            if select != None:
                encabezados = select
            else:
                encabezados = next(filas)
            
            indices = [encabezados.index(nombre_columna) for nombre_columna in encabezados]
        else:
            indices = []

        registros = []
        for n_fila, fila in enumerate(filas):
            try:
                if not fila:
                    continue    
                if indices:
                    fila = [fila[index] for index in indices]
                    registro = dict(zip(encabezados, fila))
                if types and not has_headers:
                    registro = tuple(func(val) for func, val in zip(types, fila))
    
                registros.append(registro)
            except ValueError:
                if silence_errors:
                    print(f'fila numero: {n_fila}, no la pude convertir porque faltan datos')

    return registros


#%%
import csv

def parse_csv(nombre_archivo, select=None, types=None, has_headers=False, silence_errors=False):
    encabezados = []

    with open(nombre_archivo) as f:
        filas = csv.reader(f)

        if has_headers:
            if select is not None:
                encabezados = select
            else:
                encabezados = next(filas)

        indices = [encabezados.index(nombre_columna) for nombre_columna in encabezados] if encabezados else []

        registros = []
        for n_fila, fila in enumerate(filas):
            try:
                if not fila:
                    continue

                if indices:
                    fila = [fila[index] for index in indices]
                    registro = dict(zip(encabezados, fila))
                else:
                    registro = tuple(fila)

                if types:
                    registro = {key: func(val) for key, val, func in zip(encabezados, fila, types)}

                registros.append(registro)
            except ValueError:
                if not silence_errors:
                    print(f'fila numero: {n_fila}, no la pude convertir porque faltan datos')

    return registros
#%%
import sys

print (sys.argv)

altura= 100
rebote = 3/5
cantidad_rebotes = 0

if len(sys.argv) == 2:
    altura = int(sys.argv[1])

while cantidad_rebotes < 10:
        altura = altura * rebote
        cantidad_rebotes += 1
        print(round(altura, 4))
  
#%%        
def rebotes(altura, cant_rebotes):
    rebote_red = 3/5
    while cant_rebotes > 0:
        altura *= rebote_red
        print(f"{cant_rebotes}: {altura:.2f}")
        cant_rebotes -= 1

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python rebotes.py <altura> <rebotes>")
        sys.exit(1)

    
    altura = float(sys.argv[1])
    num_rebotes = int(sys.argv[2])

    
    rebotes(altura, num_rebotes)
    
#%%
import csv

def leer_camion(nombre_archivo):
    '''Computa el precio total del camion (cajones * precio) de un archivo'''
    camion = []

    with open(nombre_archivo, 'rt') as f:
        filas = csv.reader(f)
        encabezados = next(filas)
        
        for n_fila, fila in enumerate(filas, start=1):
            record = dict(zip(encabezados, fila))
            try:
                record['cajones'] = int(record['cajones'])
                record['precio'] = float(record['precio'])
                camion.append(record)
            except ValueError:
                print('Faltan datos en la línea', n_fila, 'del archivo.')

    return camion

def leer_precios(nombre_archivo):
    precios = {}
    with open(nombre_archivo, 'rt') as f:
        rows = csv.reader(f)
        for i, row in enumerate(rows):
            if row:
                precios[row[0]] = float(row[1])
    return precios

def parse_csv(archivo_camion, archivo_precios):
    camion = leer_camion(archivo_camion)
    precios = leer_precios(archivo_precios)
    
    lista = []
    for lote in camion:
        precio_venta = precios[lote['nombre']]
        cambio = precio_venta - lote['precio']
        t = (lote['nombre'], lote['cajones'], lote['precio'], cambio)
        lista.append(t)
    
    # Imprimir la tabla final
    print('    Nombre    Cajones     Precio     Cambio')
    print('---------- ---------- ---------- ----------')
    for nombre, cajones, precio, cambio in lista:
        precio = f'${precio}'
        print(f'{nombre:>10s} {cajones:>10d} {precio:>10s} {cambio:>10.2f}')

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python informe_final.py <archivo_camion> <archivo_precios>")
        sys.exit(1)

    
    archivo_camion = sys.argv[1]
    archivo_precios = sys.argv[2]

    
    parse_csv(archivo_camion, archivo_precios)
    
#%%
import informe_final
import csv
def leer_camion(nombre_archivo):
    camion_list = informe_final.leer_camion(nombre_archivo)            
    return camion_list   #Si no me equivoco pedía algo así, no terminé de entender el punto

#camion = leer_camion('../Data/fecha_camion.csv')

def costo(camion_list):
        costo_del_camion = 0.0
        for camion in camion_list:
            costo_del_camion += int(camion["cajones"]) * float(camion["precio"])          
        return costo_del_camion
#costo_camion = costo(camion)
#print("Costo del camión:", costo_camion)


def leer_precios(nombre_archivo):
    precios_cajon = {}
    with open(nombre_archivo, "rt") as f:  #Como no tengo headers, no podría usar la funcion zip
        for line in f:
            row = line.split(",")            
            try:
                precios_cajon[row[0]] = float(row[1])                    
            except IndexError:
                pass
        
                return precios_cajon    

#lista_ventas = leer_precios("../Data/precios.csv")

 
def ventas(camion_list, lista_ventas):
    ventas_totales = 0.0
    for camion in camion_list:
        nombre_producto = camion["nombre"]
        if nombre_producto in lista_ventas:
            precio_venta = float(lista_ventas[nombre_producto])
            ventas_totales += precio_venta * int(camion["cajones"])
    return ventas_totales

def f_principal(argv):
    if len(argv) != 2:
        print("Uso: python costo_camion.py <archivo_camion>")
        return

    archivo_camion = argv[1]

    camion = leer_camion(archivo_camion)
    costo_camion = costo(camion)
    print("Costo del camión:", costo_camion)

if __name__ == "__main__":
    import sys
    f_principal(sys.argv)
    
#%%
import csv

def parse_csv(file, select=None, types=None, has_headers=False, silence_errors=False):
    indices = []
    encabezados = []

    filas = csv.reader(file)

    if has_headers:
        encabezados = next(filas)
        if select:
            encabezados = select
        indices = [encabezados.index(nombre_columna) for nombre_columna in encabezados]
    else:
        indices = []

    registros = []
    for n_fila, fila in enumerate(filas):
        try:
            if not fila:
                continue

            if indices: #Se ejecuta si hay headers
                if types:
                    registro = {key: func(val) for key, val, func in zip(encabezados, fila, types)}
                else:
                    fila = [fila[index] for index in indices]
                    registro = dict(zip(encabezados, fila))
                    print(registro)
            else:
                if types:
                    registro = tuple(func(val) for func, val in zip(types, fila))
                else:
                    registro = tuple(fila)
            registros.append(registro)
        except (ValueError, IndexError):
            if not silence_errors:
                print(f'fila numero: {n_fila}, no la pude convertir porque faltan datos')

    return registros

with open('../Data/precios.csv', 'rt') as file:
    data = parse_csv(file, types=[str, float])

#%%
import csv
import fileparse_final

def leer_camion(nombre_archivo):
    with open(nombre_archivo, 'rt') as f:
        camion = fileparse_final.parse_csv(f, types=[str, int, float], has_headers = True)
    return camion

def leer_precios(nombre_archivo):
    with open(nombre_archivo, 'rt') as f:
        precios = fileparse_final.parse_csv(f, types=[str, float])
    return precios

def f_principal(archivo_camion, archivo_precios):
    camion = leer_camion(archivo_camion)
    precios = leer_precios(archivo_precios)
    #print(camion)
    #print(precios)
    lista = []
    for lote in camion:
        nombre_producto = lote['nombre']
        precio_producto = lote['precio']
        precio_venta = next(precio for nombre, precio in precios if nombre == nombre_producto)
        cambio = next(precio for nombre, precio in precios if nombre == nombre_producto) - precio_producto
        t = (nombre_producto, lote['cajones'], precio_venta, cambio)
        lista.append(t)
    
    # Imprimir la tabla final
    print('    Nombre    Cajones     Precio     Cambio')
    print('---------- ---------- ---------- ----------')
    for nombre, cajones, precio, cambio in lista:
        precio = f'${precio}'
        print(f'{nombre:>10s} {cajones:>10d} {precio:>10s} {cambio:>10.2f}')

#%%
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python informe_final.py <archivo_camion> <archivo_precios>")
        sys.exit(1)

    archivo_camion = sys.argv[1]
    archivo_precios = sys.argv[2]

    f_principal(archivo_camion, archivo_precios)
    
#%%
def sumar_enteros(desde, hasta):
    '''Calcula la sumatoria de los números entre desde y hasta.
       Si hasta < desde, entonces devuelve cero.

    Pre: desde y hasta son números enteros
    Pos: Se devuelve el valor de sumar todos los números del intervalo
        [desde, hasta]. Si el intervalo es vacío se devuelve 0
    '''
    total = 0
    if hasta < desde:
        return 0
    while desde <= hasta:
        total += desde
        desde += 1
    return total

#%%
def valor_absoluto(n):
    '''
    Calcula el valor absoluto de cualquier número real
    '''
    if n >= 0:
        return n
    else:
        return -n
    
def suma_pares(l):
    '''
    Suma los valores pares de una lista
    '''
    res = 0
    for e in l:
        if e % 2 ==0:
            res += e
        else:
            res += 0

    return res
#La invariante de ciclo sería res
def veces(a, b):
    '''
    Suma a, b veces, siendo a y b numero enteros
    '''
    res = 0
    nb = b
    while nb != 0:
        #print(nb * a + res)
        res += a
        nb -= 1
    return res

def collatz(n):
    """
    Implementa la Conjetura de Collatz.

    Pre: n es un numero entero positivo

    Pos: retorna la cantidad de pasos necesarios para que la secuencia alcance 1.
    """
    res = 1

    while n!=1:
        if n % 2 == 0:
            n = n//2
        else:
            n = 3 * n + 1
        res += 1

    return res
#La invariante de ciclo sería n?

#%%
import csv

def parse_csv(file, select=None, types=None, has_headers=False, silence_errors=False):
    encabezados = []

    filas = csv.reader(file)

    if has_headers:
        first_row = next(filas)
        if select is not None:
            encabezados = select
        else:
            encabezados = first_row

    indices = [encabezados.index(nombre_columna) for nombre_columna in encabezados] if encabezados else []

    registros = []
    for n_fila, fila in enumerate(filas):
        try:
            if not fila:
                continue

            if indices:
                fila = [fila[index] for index in indices]
                registro = dict(zip(encabezados, fila))
            else:
                registro = tuple(fila)

            if types:
                registro = {key: func(val) for key, val, func in zip(encabezados, fila, types)}

            registros.append(registro)
        except ValueError:
            if not silence_errors:
                print(f'fila numero: {n_fila}, no la pude convertir porque faltan datos')

    return registros


#%%
import fileparse_final

with open('../Data/camion.csv', 'rt') as file:
    camion = fileparse_final.parse_csv(file, types=[str, int, float], has_headers = True)
    
#%%
import numpy as np
import matplotlib.pyplot as plt

X = np.linspace(-np.pi, np.pi, 256) #ME genera el array de 256 componentes donde se van a dibujar las lineas
C, S = np.cos(X), np.sin(X)

plt.plot(X, C)
plt.plot(X, S)

plt.show()

#%%
import numpy as np
import matplotlib.pyplot as plt

# Crea una figura nueva, de 8x6 pulgadas, con 80 puntos por pulgada y afecta a la resolucion
plt.figure(figsize=(8, 6), dpi=80)

# Crea un nuevo subplot, en una grilla de 1x1
plt.subplot(1, 1, 1)

X = np.linspace(-np.pi, np.pi, 256)
C, S = np.cos(X), np.sin(X)


plt.plot(X, C, color="blue", linewidth=2.5, linestyle="-", label="coseno")
plt.plot(X, S, color="red",  linewidth=2.5, linestyle="-", label="seno")

plt.legend(loc='upper left')

# Rango del eje x
plt.xlim(-4.0, 4.0)

# Ponemos marcas (ticks) en el eje x
plt.xticks(np.linspace(-4, 4, 9)) #max, min, cant.valores en el medio de esos

# Rango del eje y
plt.ylim(-1.0, 1.0)

# Ponemos marcas (ticks) en el eje y
plt.yticks(np.linspace(-1, 1, 5))

# Podemos grabar el gráfico (con 72 dpi)
# plt.savefig("ejercicio_2.png)", dpi=72)

# Mostramos el resultado en pantalla
plt.show()

#%%
import matplotlib.pyplot as plt

fig = plt.figure()
plt.subplot(2, 1, 1) # define la figura de arriba
plt.plot([0,1,2],[0,1,0]) # dibuja la curva
plt.xticks([]), plt.yticks([]) # saca las marcas

plt.subplot(2, 3, 4)
plt.plot([0,1],[0,1])
plt.xticks([]), plt.yticks([])

plt.subplot(2, 3, 5)
plt.plot([0,1],[1/2,1/2])
plt.xticks([]), plt.yticks([])

plt.subplot(2, 3, 6) 
plt.plot([0,1],[1,0])
plt.xticks([]), plt.yticks([])

plt.show()

#%%
import matplotlib.pyplot as plt

fig = plt.figure()
plt.subplot(2, 1, 1) # define la figura de arriba
plt.plot([0,1,2],[0,1,0]) # dibuja la curva
plt.xticks([]), plt.yticks([]) # saca las marcas

plt.subplot(2, 2, 3) # define la primera de abajo, que sería la tercera si fuera una grilla regular de 2x2
plt.plot([0,1],[0,1])
plt.xticks([]), plt.yticks([])

plt.subplot(2, 2, 4) # define la segunda de abajo, que sería la cuarta figura si fuera una grilla regular de 2x2
plt.plot([0,1],[1,0])
plt.xticks([]), plt.yticks([])

plt.show()
#%%
import numpy as np
import matplotlib.pyplot as plt

def randomwalk(largo):
    pasos = np.random.randint(-1, 2, largo)    
    return pasos.cumsum()

N = 100000

def caminatas(num_caminatas):
    lista = []
    for i in range(12):
        camin = randomwalk(N)
        lista.append(camin)
    return lista

def maximos(caminatas):
    lista = []
    for caminata in caminatas:
        maximo = np.max(np.abs(caminata))
        lista.append(maximo)
    return np.array(lista)

caminatas_totales = caminatas(12)
maximos_totales = maximos(caminatas_totales)

indice_min = np.argmin(maximos_totales)
indice_max = np.argmax(maximos_totales)

plt.figure(figsize=(8, 6), dpi=80)            
plt.subplot(2, 1, 1)
for caminata in caminatas_totales:
    plt.plot(caminata, alpha=0.5)
plt.title('12 caminatas al azar')

plt.subplot(2, 2, 3)
plt.plot(caminatas_totales[indice_max])
plt.title('La caminata que más se aleja')

plt.subplot(2, 2, 4)
plt.plot(caminatas_totales[indice_min])
plt.title('La caminata que menos se aleja')
    
plt.show()

#%%
import numpy as np
import matplotlib.pyplot as plt

n = 12
X = np.arange(n)
f = 0.1
Y1 = (1 - X / float(n)) * np.random.uniform(0.5, 1.0, n)
Y2 = (1 - X / float(n)) * np.random.uniform(0.5, 1.0, n)

plt.bar(X, +Y1, facecolor='#9999ff', edgecolor='white')
plt.bar(X, -Y2, facecolor='#ff9999', edgecolor='white')

for x, y in zip(X, Y1):
    plt.text(x + 0.4, y + 0.1, '%.2f' % y, ha='right', va='bottom')

for x, y in zip(X, Y2):
    plt.text(x + 0.4, -y - 0.1, '%.2f' % y, ha='right', va='top')

plt.ylim(-1.25, +1.25)

plt.xticks([]), plt.yticks([])
plt.show()


#%%
plt.axes([0, 0, 1, 1], projection = 'polar')

N = 20
theta = np.arange(0., 2 * np.pi, 2 * np.pi / N)
radii = 10 * np.random.rand(N)
width = np.pi / 4 * np.random.rand(N)
bars = plt.bar(theta, radii, width=width, bottom=0.0)

for r, bar in zip(radii, bars):
    bar.set_facecolor(plt.cm.jet(r / 10.))
    bar.set_alpha(0.5)

plt.xticks([])

#%%
import numpy as np
import matplotlib.pyplot as plt

n = 1024
X = np.random.normal(0, 1, n)
Y = np.random.normal(0, 1, n)

# Así calculo el ángulo
angles = np.arctan2(Y, X)

# Así calculo los 4 cuadrantes
quadrant = np.floor((angles % (2 * np.pi)) / (np.pi / 2)) + 1

# Asignamos colores según el cuadrante
colors = ['red' if q == 1 else 'green' if q == 2 else 'blue' if q == 3 else 'yellow' for q in quadrant]

plt.xlim(-2, 2)
plt.ylim(-2, 2)


plt.scatter(X, Y, c=colors, alpha = 0.4)

plt.show()

#%%
import pandas as pd
import os

directorio = '../Data'
archivo = 'arbolado-en-espacios-verdes.csv'
fname = os.path.join(directorio,archivo)
df = pd.read_csv(fname)

df.head(2)
df.tail(2)
df.columns
df.index
df[['long', 'lat', 'id_arbol']].describe()
df['nombre_com'].unique()
(df['nombre_com']=='Ombú').sum() #Suma los true
cant_ejemplares = df['nombre_com'].value_counts() #Suma los true de cada nombre_com
df_jacarandas = df[df['nombre_com'] == 'Jacarandá'] #Dataset solo arboles jacaranda

cols = ['altura_tot', 'diametro', 'inclinacio']
df_jacarandas = df_jacarandas[cols]
df_jacarandas.tail()
df_jacarandas.describe()
df_jacarandas = df[df['nombre_com'] == 'Jacarandá'][cols].copy() #Para crear una copia aparte y no modificar el dataset original

df_jacarandas.plot.scatter(x = 'diametro', y = 'altura_tot')

# "usar pandas para manejar los datos y seaborn para visualizarlos, es la posta"

import seaborn as sns

sns.scatterplot(data = df_jacarandas, x = 'diametro', y = 'altura_tot')

df.loc[165] #Para ver observacion 165 que seria la 0 del df original
df_jacarandas.iloc[0]

df_jacarandas_diam = df_jacarandas['diametro'] #Solo una columna
type(df_jacarandas)
type(df_jacarandas_diam)

pd.date_range('20200923', periods = 7) #Crear espacios de tiempo, frequency diary
pd.date_range('20200923 14:00', periods = 6, freq = 'H') #Frecuencia 1 hora

pd.Series([1, 2, 3, 4, 5, 6], index = pd.date_range('20200923 14:00', periods = 6, freq = 'H')) #Series temporales

#%%
import numpy as np
import pandas as pd

idx = pd.date_range('20200923 14:00', periods = 120, freq = 'min')
s1 = pd.Series(np.random.randint(-1,2,120), index = idx)
s2 = s1.cumsum()

s2.plot()
w = 5 
s3 = s2.rolling(w).mean() #CREAR UNA MEDIA MOVIL
s3.plot()

df_series_23 = pd.DataFrame([s2, s3]).T  # armo un dataframe con ambas series
df_series_23.plot()

horas = 8
idx = pd.date_range('20200923 14:00', periods = horas*60, freq = 'min')
nombres = ['Pedro', 'Santiago', 'Juan', 'Andrés','Bartolomé','Tiago','Isca','Tadeo','Mateo','Felipe','Simón','Tomás']

df_walks = pd.DataFrame(np.random.randint(-1,2,[horas*60,12]).cumsum(axis=0), index = idx, columns = nombres) #CREA EL DATASET!!!!!
#df_walks.plot()

w = 45
df_walk_suav = df_walks.rolling(w, min_periods = 1).mean() # datos suavizados para no perder datos extremos
nsuav = ['S_' + n for n in nombres]
df_walk_suav.columns = nsuav #cambia los datos de los nombres

df_walk_suav.plot()

df_walk_suav.to_csv('caminata_apostolica.csv') #GUARDA EL DATASET

#%%
import pandas as pd
import os
import seaborn as sns

directorio = '../Data'
archivo = 'arbolado-publico-lineal-2017-2018.csv'
fname = os.path.join(directorio,archivo)
df = pd.read_csv(fname)

cols_sel = ['nombre_cientifico', 'ancho_acera', 'diametro_altura_pecho', 'altura_arbol']

df_lineal = df[cols_sel]

especies_mas_selec = df_lineal['nombre_cientifico'].value_counts()
especies_mas_selec.head(5)

especies_seleccionadas = ['Tilia x moltkei', 'Jacaranda mimosifolia', 'Tipuana tipu']

df_lineal_seleccion = df_lineal[df_lineal['nombre_cientifico'].isin(especies_seleccionadas)] #Se queda solo con las especies seleccionadas

df_lineal_seleccion.boxplot('altura_arbol', by = 'nombre_cientifico')
sns.pairplot(data = df_lineal_seleccion[cols_sel], hue = 'nombre_cientifico')

#%%
import pandas as pd
import os
import seaborn as sns

directorio = '../Data'
archivo = 'arbolado-publico-lineal-2017-2018.csv'
fname = os.path.join(directorio,archivo)
df_veredas = pd.read_csv(fname)

archivo2 = 'arbolado-en-espacios-verdes.csv'
fname2 = os.path.join(directorio,archivo2)
df_parques = pd.read_csv(fname2)

cols = ['altura_tot', 'diametro', 'nombre_cie']
cols2 = ['altura_arbol', 'diametro_altura_pecho', 'nombre_cientifico']

df_tipas_parques = df_parques[cols].copy()
df_tipas_veredas = df_veredas[cols2].copy()

df_tipas_parques = df_tipas_parques.rename(columns = {'altura_tot': 'altura'})
df_tipas_veredas = df_tipas_veredas.rename(columns={'altura_arbol': 'altura', 'diametro_altura_pecho': 'diametro'})

df_tipas_parques['ambiente'] = 'parque'
df_tipas_veredas['ambiente'] = 'vereda'

df_tipas = pd.concat([df_tipas_veredas, df_tipas_parques])

df_tipas.boxplot('diametro', by = 'ambiente')

df_tipas.boxplot('altura', by = 'ambiente')
#Pensaba que para repetir el análisis con distintas especies podría crear una nueva variable por cada especie o filtrar el dataframe
#por cada especie aunque fuese muy laborioso. Por mi lado sí, definiría una función porque brindaria mucha comodidad para ejecutar el código y podría ayudar al análisis por especie.

#%%
import os
import datetime
def crear_destino(dirdestino):
    if 'imgprocesadas' not in os.listdir(dirdestino):
        os.chdir(dirdestino)
        os.mkdir('imgsprocesadas')

def procesar_nombres(nombre):
    nombre_corregido = nombre[0:-13] + nombre[-4:]
    fecha = nombre[-12:-4]
    fecha_corregida = datetime.strptime[fecha, '%Y%m%d']
    nombre = os.path.split(nombre_corregido)
    nombre_corregido = nombre[-1]
    return nombre_corregido, fecha_corregida

def procesar(dir_origen, dir_destino):
    for root, dirs, files in os.walk(dir_origen):
        os.chdir(root)
        for name in files:
            if name[-3:] == 'png':
                fecha_modifi = procesar,nombre(name)[1]
                tsmodi=fecha_modifi.timestamp()
                nombre_procesado = procesar_nombres(name)[0]
                os.utime(name, (tsmodi, tsmodi))
                os.rename(name, nombre_procesado)
                os.rename(os.path.join(root, nombre_procesado), os.path.join(dir_destino, 'imgs_procesadas', nombre_procesado))

def eliminar_vacios(dir_origen):
    for root, dirs, files in os.walk(dir_origen, topdown = False):
        try:
            os.rmdir(root)
        except:
            continue

def ordenarimgs(dir_origen, dir_destino):
    crear_destino(dir_destino)
    procesar(dir_origen, dir_destino)
    eliminar_vacios(dir_origen)
    
#%%
import csv
import fileparse

def leer_camion(nombre_archivo):
    with open(nombre_archivo, 'rt') as f:
        camion = fileparse.parse_csv(f, types=[str, int, float], has_headers = True)
    return camion

def leer_precios(nombre_archivo):
    with open(nombre_archivo, 'rt') as f:
        precios = fileparse.parse_csv(f, types=[str, float])
    return precios

def f_principal(archivo_camion, archivo_precios):
    camion = leer_camion(archivo_camion)
    precios = leer_precios(archivo_precios)
    #print(camion)
    #print(precios)
    lista = []
    for lote in camion:
        nombre_producto = lote['nombre']
        precio_producto = lote['precio']
        precio_venta = next(precio for nombre, precio in precios if nombre == nombre_producto)
        cambio = next(precio for nombre, precio in precios if nombre == nombre_producto) - precio_producto
        t = (nombre_producto, lote['cajones'], precio_venta, cambio)
        lista.append(t)
    
    # Imprimir la tabla final
    print('    Nombre    Cajones     Precio     Cambio')
    print('---------- ---------- ---------- ----------')
    for nombre, cajones, precio, cambio in lista:
        precio = f'${precio}'
        print(f'{nombre:>10s} {cajones:>10d} {precio:>10s} {cambio:>10.2f}')

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python informe_final.py <archivo_camion> <archivo_precios>")
        sys.exit(1)

    archivo_camion = sys.argv[1]
    archivo_precios = sys.argv[2]

    f_principal(archivo_camion, archivo_precios)
    
#%%
class Lote:
    def __init__(self, nombre, cajones, precio):
        self.nombre = nombre
        self.cajones = cajones
        self.precio = precio

    def palabra(self):
        return self.nombre
    
    def cant_cajones(self):
        return self.cajones
    
    def total_precio(self):
        return self.precio
    
    def calcular_costo(self):
        costo = self.cajones * self.precio
        return costo
        
    def vender(self, num):
        cajones = self.cajones - num
        return cajones

#%%
import lote

lote = lote.lote('Pera', 100, 490.10)

#%%
class Lote:
    def __init__(self, nombre, cajones, precio):
        self.nombre = nombre
        self.cajones = cajones
        self.precio = precio

    def costo(self):
        return self.cajones * self.precio

    def vender(self, ncajones):
        self.cajones -= ncajones

class MiLote(Lote):
    def rematar(self):
        self.vender(self.cajones)
    
    def costo(self):
        costo_orig =super().costo()
        return 1.25 * costo_orig
    
#%%
class Lote:
    def __init__(self, nombre, cajones, precio):
        self.nombre = nombre
        self.cajones = cajones
        self.precio = precio


class MiLote(Lote):
    def __init__(self, nombre, cajones, precio, factor):
        # Fijate como es el llamado a `super().__init__()`
        super().__init__(nombre, cajones, precio)
        self.factor = factor #Si redefinis el metodo init se hace asi

    def costo(self):
        return self.factor * super().costo()
    
#%%
import csv
import fileparse
from lote import Lote


def leer_precios(nombre_archivo):
    with open(nombre_archivo, 'rt') as file:
        precios_informe = fileparse.parse_csv(file, has_headers=False)
        #precios = [(nombre, float(precio)) for nombre, precio in precios_informe]
    print(precios_informe)
    return precios_informe

def leer_camion(nombre_archivo):
    with open(nombre_archivo, 'rt') as file:
        camion_ar = fileparse.parse_csv(file, types=[str, int, float], has_headers = True)
    camion = [Lote(d['nombre'], d['cajones'], d['precio']) for d in camion_ar]
    return camion

def f_principal(archivo_camion, archivo_precios):
    camion = leer_camion(archivo_camion)
    precios = leer_precios(archivo_precios)
    #print(camion)
    #print(precios)
    lista = []
    for lote in camion:
        nombre_producto = lote.nombre
        precio_producto = lote.precio
        precio_venta = precios[nombre_producto]
        cambio = precios[nombre_producto] - precio_producto
        t = (nombre_producto, lote.cajones, precio_venta, cambio)
        lista.append(t)
    return lista


def imprimir_informe(archivo_camion, archivo_precios):
    lista = f_principal(archivo_camion, archivo_precios)
    print('    Nombre    Cajones     Precio     Cambio')
    print('---------- ---------- ---------- ----------')
    for nombre, cajones, precio, cambio in lista:
        precio = f'${precio}'
        print(f'{nombre:>10s} {cajones:>10d} {precio:>10s} {cambio:>10.2f}')
    
#%%
import csv
import fileparse
from lote import Lote
import formato_tabla


def leer_precios(nombre_archivo) -> dict:
    with open(nombre_archivo, 'rt') as file:
        precios_informe = fileparse.parse_csv(file, has_headers=False)
    precios = {nombre: float(precio) for nombre, precio in precios_informe}
    return precios

def leer_camion(nombre_archivo) -> list[dict]:
    with open(nombre_archivo, 'rt') as file:
        camion_ar = fileparse.parse_csv(file, types=[str, int, float], has_headers = True)
    camion = [Lote(d['nombre'], d['cajones'], d['precio']) for d in camion_ar]
    return camion

def f_principal(archivo_camion, archivo_precios, fmt = 'txt'):
    '''
    Crea un informe con la carga de un camión
    a partir de archivos camion y precio.
    El formato predeterminado de la salida es txt
    Alternativas: csv o html
    '''
    camion = leer_camion(archivo_camion)
    precios = dict(leer_precios(archivo_precios))
    #print(camion)
    #print(precios)
    lista = []
    for lote in camion:
        nombre_producto = lote.nombre
        precio_producto = lote.precio
        precio_venta = precios[nombre_producto]
        cambio = precios[nombre_producto] - precio_producto
        t = (nombre_producto, lote.cajones, precio_venta, cambio)
        lista.append(t)
    data_informe = lista
    formateador = formato_tabla.crear_formateador(fmt)
    imprimir_informe(data_informe, formateador)

    
def imprimir_informe(lista, formateador):
    formateador.encabezado(['Nombre', 'Cantidad', 'Precio', 'Cambio'])
    #print('---------- ---------- ---------- ----------')
    for nombre, cajones, precio, cambio in lista:
        #precio = f'${precio}'
        rowdata = [nombre, str(cajones), f'{precio:0.2f}', f'{cambio:0.2f}']
        formateador.fila(rowdata)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Uso: python informe_final.py <archivo_camion> <archivo_precios>")
        sys.exit(1)

    archivo_camion = sys.argv[1]
    archivo_precios = sys.argv[2]
    fmt = sys.argv[3]

    f_principal(archivo_camion, archivo_precios, fmt)

#%%
class FormatoTabla:
    def encabezado(self, headers):
        '''
        Crea el encabezado de la tabla.
        '''
        raise NotImplementedError()
    
    def fila(self, rowdata):
        '''
        Crea una única fila de datos de la tabla.
        '''
        raise NotImplementedError()
        
class crear_formateador(FormatoTabla):
    def __init__(self, nombre):
        super().__init__()
        self.nombre = nombre
        
    def encabezado(self, headers):
        if self.nombre == 'txt':
            for h in headers:
                print(f'{h:>10s}', end=' ')
            print()
            print(('-'*10 + ' ')*len(headers))
        elif self.nombre == 'csv':
            print(','.join(headers))
        elif self.nombre == 'html':
            print('<tr>', end='')
            for h in headers:
                print(f'<th>{h}</th>', end='')
            print('</tr>')
    
    def fila(self, data_fila):
        if self.nombre == 'txt':
            for d in data_fila:
                print(f'{d:>10s}', end=' ')
            print()
        elif self.nombre == 'csv':
            print(','.join(data_fila))
        elif self.nombre == 'html':
            print('<tr>', end='')
            for d in data_fila:
                print(f'<td>{d}</td>', end='')
            print('</tr>')
            
#%%
class Lote:
    def __init__(self, nombre, cajones, precio):
        self.nombre = nombre
        self.cajones = cajones
        self.precio = precio

    def obtener_nombre(self):
        return self.nombre
    
    def obtener_cajones(self):
        return self.cajones
    
    def obtener_precio(self):
        return self.precio
    
    def calcular_costo(self):
        costo = self.cajones * self.precio
        return costo
        
    def vender(self, num):
        return self.cajones - num
    
    def __repr__(self):
        return f"Lote('{self.nombre}', {self.cajones}, {self.precio})"
    
#%%
class Canguro:
    """Un Canguro es un marsupial."""
    
    def __init__(self, nombre, contenido=None):
        """Inicializar los contenidos del marsupio.

        nombre: string
        contenido: contenido inicial del marsupio, lista (opcional).
        """
        self.nombre = nombre
        self.contenido_marsupio = contenido if contenido is not None else []

    def __str__(self):
        """devuelve una representación como cadena de este Canguro.
        """
        t = [self.nombre + ' tiene en su marsupio:']
        for obj in self.contenido_marsupio:
            s = '    ' + object.__str__(obj)
            t.append(s)
        return '\n'.join(t)

    def meter_en_marsupio(self, item):
        """Agrega un nuevo item al marsupio.

        item: objeto a ser agregado
        """
        self.contenido_marsupio.append(item)

#%%
madre_canguro = Canguro('Madre')
cangurito = Canguro('gurito')
madre_canguro.meter_en_marsupio('billetera')
madre_canguro.meter_en_marsupio('llaves del auto')
madre_canguro.meter_en_marsupio(cangurito)

print(madre_canguro)
print(cangurito)
#Lo que sucede es que todas las instancias compartes una misma lista, por eso, aparecía 
#como que cangurito tambíen metía las mismas cosas en su marsupio, inclusive a si mismo,
#Por ende, con este codigo y al ser opcional la lista, cada canguro tiene su propio marsupio

#%%
class Cola:
    '''Representa a una cola, con operaciones de encolar y desencolar.
    El primero en ser encolado es tambien el primero en ser desencolado.
    '''

    def __init__(self):
        '''Crea una cola vacia.'''
        self.items = []

    def encolar(self, x):
        '''Encola el elemento x.'''
        self.items.append(x)

    def desencolar(self):
        '''Elimina el primer elemento de la cola 
        y devuelve su valor. 
        Si la cola esta vacia, levanta ValueError.'''
        if self.esta_vacia():
            raise ValueError('La cola esta vacia')
        return self.items.pop(0)

    def esta_vacia(self):
        '''Devuelve 
        True si la cola esta vacia, 
        False si no.'''
        return len(self.items) == 0
#%%
class TorreDeControl:
    def __init__(self):
        self.arribos = []
        self.partidas = []
    
    def nuevo_arribo(self, vuelo):
        self.arribos.append(vuelo)
    
    def nueva_partida(self, vuelo):
        self.partidas.append(vuelo)
    
    def asignar_pista(self):
        if self.arribos:
            vuelo = self.arribos.pop(0)
            print(f'El vuelo {vuelo} aterrizó con éxito.')
        elif self.partidas:      #El orden indica quien va a aterrizar y despegar respectivamente
            vuelo = self.partidas.pop(0) #.pop saca y te dice cual sacó
            print(f'El vuelo {vuelo} despegó con éxito.')
        else:
            print('No hay vuelos en espera.')
    
    def ver_estado(self):
        print(f'Vuelos esperando para aterrizar: {", ".join(self.arribos)}')
        print(f'Vuelos esperando para despegar: {", ".join(self.partidas)}')
        
#####
torre = TorreDeControl()
torre.nuevo_arribo('AR156')
torre.nueva_partida('KLM1267')
torre.nuevo_arribo('AR32')
torre.ver_estado()
torre.asignar_pista()

#%%

class Jugador:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.salud = 100

    def mover(self, dx, dy):
        self.x += dx
        self.y += dy

    def lastimar(self, pts):
        self.salud -= pts
        
#%%
"""
Segundo parcial - Jueves 29/06/2023
Ejercicio 1:  Interpretá lo que quiso hacer le programadore y corregí los
dos bugs.
"""
def encontrar_duplicados(lista_de_elementos:list)-> list: 
    duplicados = []
    unicos = set()
    for elemento in lista_de_elementos:
        if elemento in unicos and elemento not in duplicados: #AND
            duplicados.append(elemento)
        unicos.add(elemento)
    return duplicados  #Entiendo que quiso encontrar los duplicados, mientras que la función devuelve los elementos únicos de la lista

lista=[1, 2, 3, 4, 3, 2, 5]
print(lista) 
print(encontrar_duplicados(lista))

lista=['a', 'b', 'c', 'a', 'd', 'e', 'b', 'b']
print(lista) 
print(encontrar_duplicados(lista))

#%%
"""
Segundo parcial - Miércoles 28/06/2023
Ejercicio 1:  Interpretá lo que quiso hacer le programadore y corregí los
dos bugs.
"""
def es_palindromo (palabra:str): #Tipo de dato es str, no lista
    es_palindromo = False

    for i in range(len(palabra)//2):
        if palabra[i] == palabra[-i-1]: #Faltaba un -1 por cuestion de como se manejan las listas en python
            es_palindromo = True
    if es_palindromo:
        print(f"{palabra} es un palíndromo") #Falta una f
    else:
        print(f"{palabra} no es un palíndromo")

    
palabra="casa"
es_palindromo(palabra)

palabra="radar"
es_palindromo(palabra)

#%%
"""
Hola! Este ejercicio fue hecho por mi y no es el mismo que
dieron en el parcial. Es probable que haya diferencias!
Pero, sirve para practicar :)
"""

def es_palindromo(palabra):
    palabra = palabra.lower() #Faltaba donde guardar el resultado
    palabra_invertida = palabra[::-1]
    if palabra == palabra_invertida:
        return True
    else:
        return False


print(es_palindromo("ana"))
print(es_palindromo("Anita lava la tina"))
print(es_palindromo("Enrique"))
print(es_palindromo("radar"))
print(es_palindromo("sarasa"))
#%%
"""
Hola! Este ejercicio fue hecho por mi y no es el mismo que
dieron en el parcial. Es probable que haya diferencias!
Pero, sirve para practicar :)
"""

def geringoso(palabra):
    capadepenapa = ''
    for c in palabra:
        if c in 'aeiouAEIOU':
            capadepenapa += c + 'p' + c.lower()
        else:
            capadepenapa += c
    return capadepenapa

print(geringoso('banana'))
print(geringoso('manzana'))
print(geringoso('mandarina'))
print(geringoso('Arbol'))

#%%
import csv
def leer_archivo(nombre):
    num_lista = []
    with open(nombre, 'rt') as f:
        rows = csv.reader(f)
        for num in rows:
            for nums in num:
                if nums.strip() and nums.isdigit(): #strip para eliminar los espacios en blanco, y isdigit verifica si es un numero
                    num_lista.append(int(nums)) #Esto asi para que no devuelva una lista con otra lista
    return num_lista

def ordenar_lista_creciente(lista):
    numeros_ordenados = []
    while lista:
        minimo = lista[0]
        for x in lista: 
            if x < minimo:
                minimo = x
        numeros_ordenados.append(minimo)
        lista.remove(minimo)
    
    return numeros_ordenados

def ordenar_lista_decreciente(lista):
    numeros = ordenar_lista_creciente(lista)
    return numeros[::-1]
#%%
def leer_archivo_ordenar(nombre_archivo, orden = 'crec'):
    num_lista = []
    numeros_ordenados = []
    with open(nombre_archivo, 'rt') as f:
        rows = csv.reader(f)
        for num in rows:
            for nums in num:
                if nums.strip() and nums.isdigit(): #strip para eliminar los espacios en blanco, y isdigit verifica si es un numero
                    num_lista.append(int(nums))
            while num_lista:
                minimo = num_lista[0]
                for x in num_lista: 
                    if x < minimo:
                        minimo = x
                numeros_ordenados.append(minimo)
                num_lista.remove(minimo)
            if orden == 'crec':
                return numeros_ordenados
            elif orden == 'decr':
                return numeros_ordenados[::-1]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python lista_ordenar.py <archivo_numeros> <orden>")
        sys.exit(1)

    archivo_numeros = sys.argv[1]
    orden = sys.argv[2]
    
#%%
    
class Ordenador:
    def __init__(self, nombre_archivo):
        self.nombre_archivo = nombre_archivo
        self.lista_nums = []
        
    def leer_de_archivo(self):
        with open(self.nombre_archivo, 'rt') as f:
            rows = csv.reader(f)
            for row in rows:
                for elem in row:
                    if elem.strip() and elem.isdigit():
                        self.lista_nums.append(int(elem))
                        
    def ordenar(self, orden = 'crec'):
        numeros_ordenados = []
        numeros = self.lista_nums.copy()
        while numeros:
            minimo = numeros[0]
            for x in numeros:
                if x < minimo:
                    minimo = x
            numeros_ordenados.append(minimo)
            numeros.remove(minimo)
        if orden == 'decr':
            return numeros_ordenados[::-1]
        return numeros_ordenados

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        archivo = sys.argv[1]
        orden = sys.argv[2]
        
        ordenador = Ordenador(archivo)
        ordenador.leer_de_archivo()
        print(ordenador.numeros)
        
        numeros_ordenados = ordenador.ordenar(orden=orden)
        print(numeros_ordenados)
        print(ordenador.numeros)
    
#%%
"""
Segundo parcial - Jueves 29/06/2023
Ejercicio 1:  Interpretá lo que quiso hacer le programadore y corregí los
dos bugs.
"""
def encontrar_duplicados(lista_de_elementos:list)-> list: 
    duplicados = []
    unicos = set()
    for elemento in lista_de_elementos:
        if elemento in unicos and elemento not in duplicados:
            duplicados.append(elemento)
        unicos.add(elemento)
    return duplicados

lista=[1, 2, 3, 4, 3, 2, 5]
print(lista) 
print(encontrar_duplicados(lista))

lista=['a', 'b', 'c', 'a', 'd', 'e', 'b']
print(lista) 
print(encontrar_duplicados(lista))
    
#%%
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt

def leer_data(archivo):
    df_alumnos = pd.read_csv(archivo)
    df_alumnos['fecha_fin_cursada'] = pd.to_datetime(df_alumnos['fecha_fin_cursada'])
    df_alumnos['fecha_final'] = pd.to_datetime(df_alumnos['fecha_final'])
    return df_alumnos

def estudiantes_sin_final(dataframe,N):
    df = leer_data(dataframe)
    año_actual = 2023
    df_estudiantes = df[(año_actual - df['fecha_fin_cursada'].dt.year >= 2) & (df['nota_final'].isna())]
    return print(f'Estudiantes que aprobaron la cursada hace {N} años y no rindieron el final: {df_estudiantes}')

def hacer_grafico(df):
    df = leer_data(df) #necesito crear una nueva columna que sea la diferencia de meses entre rendir y aprobar la cursada
    df['diff_meses'] = ((df.fecha_final - df.fecha_fin_cursada)/np.timedelta64(1, 'M'))
    df['diff_meses'] = df['diff_meses'].apply(np.floor).astype('Int64')
    sns.scatterplot(data = df, x ='nota_final', y = 'diff_meses')
    plt.show()

#%%
"""
Segundo parcial - Miércoles 28/06/2023
Ejercicio 1:  Interpretá lo que quiso hacer le programadore y corregí los
dos bugs.
"""
def es_palindromo (palabra:list):
    es_palindromo = False

    for i in range(len(palabra)//2):
        if palabra[i] == palabra[-i-1]: #Faltaba un -1
            es_palindromo = True
    if es_palindromo:
        print(f"{palabra} es un palíndromo") #Faltaba la f
    else:
        print(f"{palabra} no es un palíndromo")

    
palabra="casa"
es_palindromo(palabra)

palabra="radar"
es_palindromo(palabra)

#%%
from collections import Counter
def leer_archivo(archivo): #AL SER UN TXT
    with open(archivo, 'rt') as file:
        text = file.read()
        text = text.replace('\n', '') # Elimino los saltos de linea
        text = text.replace(' ', '') # Elimino los espacios
        text = text.replace(',', '') # Elimino las comas
    return text

def contar_letras(texto, N):
    contador = Counter(texto)
    for letra, cantidad in contador.most_common(N):
        print(f'{letra}: {cantidad} veces')
    
#%%
class Texto:
    def __init__(self, archivo, N):
        self.archivo = archivo
        self.N = N
    
    def leer_de_archivo(self, archivo):
        with open(self.nombre_archivo, 'rt') as f:
            text = f.read()
            text = text.replace('\n', '') #Salto de linea
            text = text.replace(' ', '') 
            text = text.replace(',', '')
        self.text = text
        
    def contador_letras(self, N):
        contador = Counter(self.text)
        for letra, cantidad in contador.most_common(N):
            print(f'{letra}: {cantidad} veces')

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        archivo = sys.argv[1]
        N = int(sys.argv[2])
        
        texto = Texto(archivo)
        texto.read_text_file()
        print(texto.contador_letras(N))
        
#%%
def geringoso(palabra):
    capadepenapa = ''
    for c in palabra:
        if c in 'aeiouAEIOU':
            capadepenapa += c + 'p' + c.lower()
        else:
            capadepenapa += c
    return capadepenapa

print(geringoso('banana'))
print(geringoso('manzana'))
print(geringoso('mandarina'))
print(geringoso('Arbol'))

#%%
import csv
def leer_archivo(archivo):
    lista_nums = []
    with open(archivo, 'rt') as f:
        rows = csv.reader(f)
        for nums in rows:
            for num in nums:
                if num.isdigit():
                    num = int(num)
                    lista_nums.append(num)
    return lista_nums

def ordenar_lista(lista, orden = 'creciente'):
    lista_ordenada = []
    while lista:
        minimo = lista[0]
        for num in lista:
            if num < minimo:
                minimo = num
            if num not in lista_ordenada:
                lista_ordenada.append(minimo)
        lista.remove(minimo)
    if orden == 'creciente':
        return lista_ordenada
    elif orden == 'decreciente':
        return lista_ordenada[::-1]
    
#%%
import csv
class Ordenador:
    def __init__(self, archivo):
        self.archivo = archivo
        self.lista = []
        
    def leer_de_archivo(self):
        with open(self.archivo, 'rt') as f:
            rows = csv.reader(f)
            for nums in rows:
                for num in nums:
                    if num.isdigit():
                        num = int(num)
                        lista.append(num)
    
    def ordenar_lista(self, orden = 'creciente'):
        lista_ordenada = []
        lista = self.lista.copy()
        while lista:
            minimo = lista[0]
            for num in lista:
                if num < minimo:
                    minimo = num
                if num not in lista_ordenada:
                    lista_ordenada.append(minimo)
            lista.remove(minimo)
        if orden == 'creciente':
            return lista_ordenada
        elif orden == 'decreciente':
            return lista_ordenada[::-1]
        
        
if __name__ == '__main__':
    if len(sys.argv) == 3:
        archivo = sys.argv[1]
        orden = sys.argv[2]
        
        ordenador = Ordenador(archivo)
        ordenador.leer_de_archivo()
        print(ordenador.numeros)
        
        numeros_ordenados = ordenador.ordenar_lista(orden)
        print(numeros_ordenados)
        print(ordenador.numeros)
        
#%%
import random

def generar_numero():
    numero = random.randint(1, 10) #falta el random.
    return numero

def comparar_numeros(intento, objetivo):
    if intento == objetivo:
        print("¡Adivinaste!")
    elif intento < objetivo:  #intento es un string
        print("Demasiado bajo. Intenta nuevamente.")
    else:
        print("Demasiado alto. Intenta nuevamente.")

def main():
    objetivo = generar_numero()
    intentos = 0
    adivinado = False

    while not adivinado:
        n_usr = int(input("Adivina el número (entre 1 y 10):" )) #Este input devuelve un string, por lo que hay que transformarlo previamente a entero
        comparar_numeros(n_usr, objetivo)
        intentos += 1
        
        if n_usr == objetivo:
            adivinado = True

    print(f"¡Felicidades! Adivinaste el número en {intentos} intentos.")

main()

#%%
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
def leer_archivo(archivo):
    df_alumnos = pd.read_csv(archivo)
    df_alumnos.drop_duplicates(
        keep = 'last',
        inplace = True,
        subset=['nombre', 'apellido', 'materia']
        )
    return df_alumnos.reset_index(drop=True) #Se ve que esto guarda el eliminar duplicados

def promedio_nota(df, materia):
    df_materia = df[df['materia'] == materia][['nombre', 'apellido', 'nota_final']]
    df_materia = df_materia.rename(columns={
        'nombre': 'Nombre', 
        'apellido': 'Apellido', 
        'nota_final': 'Nota'
    })
    promedio = df_materia['Nota'].mean()
    print(df_materia)
    print(round(promedio, 2))
    
def boxplot(df, materia):
    title = f'Notas de la materia: {materia}'
    dataf = df[df['materia'] == materia]
    plt.figure(figsize=(15,5))
    sns.boxplot(
        x='nota_final',
        y='materia',
        data = dataf,
        orient='h')
    plt.title(title)
    plt.xlabel('Nota')
    plt.show()
    
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python lista_ordenar.py <df_alumnos> <materia>")
        sys.exit(1)

    archivo = sys.argv[1]
    materia = sys.argv[2]
    
    df = leer_archivo(archivo)
    promedio_nota(df, materia)
    boxplot(df, materia)
#%%
import numpy as np
import matplotlib.pyplot as plt

# Definir la función f(x, y)
def f(x, y):
    if y > x**2:
        return 0
    elif y == 0:
        return 0
    elif y < -x**2:
        return 0
    else:
        return 1

# Crear una cuadrícula de valores de x y y
x = np.linspace(-3, 3, 400)
y = np.linspace(-3, 3, 400)
X, Y = np.meshgrid(x, y)

# Evaluar la función f(x, y) en cada punto de la cuadrícula
Z = np.array([[f(x, y) for x, y in zip(X_row, Y_row)] for X_row, Y_row in zip(X, Y)])

# Graficar la función
plt.figure(figsize=(8, 6))
plt.contourf(X, Y, Z, levels=[-0.1, 0.5, 1.1], colors=['white', 'lightblue'])
plt.title('Gráfico de la función f(x, y)')
plt.xlabel('x')
plt.ylabel('y')
plt.grid(True)
plt.show()

#%%
import numpy as np
import matplotlib.pyplot as plt

# Definir la función de la hipérbola
def hyperbola(x):
    return np.sqrt((x**2 - 4) * 4)

# Generar valores para x
x = np.linspace(-3, 3, 400)

# Calcular valores de y para la parte superior de la hipérbola
y_top = hyperbola(x)

# Calcular valores de y para la parte inferior de la hipérbola
y_bottom = -y_top

# Graficar la hipérbola
plt.plot(x, y_top, 'b')
plt.plot(x, y_bottom, 'b')

# Definir la región sombreada
x_fill = np.linspace(-2, 2, 400)
y_fill_top = hyperbola(x_fill)
y_fill_bottom = -y_fill_top

# Graficar el área sombreada
plt.fill_between(x_fill, y_fill_bottom, y_fill_top, where=(x_fill**2/4 - y_fill_bottom**2/4 <= 1), color='gray', alpha=0.3)

# Configuración del gráfico
plt.xlabel('x')
plt.ylabel('y')
plt.title(r'Gráfico de $\frac{x^2}{4} - \frac{y^2}{4} \leq 1$')
plt.grid(True)
plt.axis('equal')

# Mostrar el gráfico
plt.show()
#%%
import numpy as np
import matplotlib.pyplot as plt

# Definir la función
def f(x, y):
    return np.sqrt(y**2 - x**2 + 4) / x

# Crear una malla de valores para x y y
x = np.linspace(-2, 2, 400)
y = np.linspace(-2, 2, 400)
X, Y = np.meshgrid(x, y)

# Calcular los valores de la función en la malla
Z = f(X, Y)

# Graficar la función
plt.contourf(X, Y, Z, levels=50, cmap='viridis')
plt.colorbar(label='f(x, y)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Gráfico de la función f(x, y)')
plt.grid(True)
plt.axis('equal')

# Mostrar el gráfico
plt.show()
#%%
import numpy as np

def matriz_random():
    return np.random.randint(-5, 6, size=(5, 5))

def autovals(matriz):
    autoval, autovect = np.linalg.eig(matriz)
    num_autovalores = len(autoval)
    num_autovectores = len(autovect)
    if num_autovalores != num_autovectores: #Verificamos que halla suficientes autovectores LI
        return "No hay suficientes autovectores, por ende no es diagonalizable"  # No hay suficientes autovectores
    else:
        
mat = matriz_random()
