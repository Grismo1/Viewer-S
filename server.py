import asyncio
import websockets
import json
import os


clientes = set()

dispositivos = {}

selecciones = {}



async def manejar_cliente(websocket):

    clientes.add(websocket)

    print("[+] Cliente conectado")
    print("Conexiones activas:", len(clientes))


    try:

        async for mensaje in websocket:


            datos = json.loads(mensaje)


            print("MENSAJE:")
            print(datos)



            # REGISTRO DE CLIENTES Y VIEWERS

            if datos["type"] == "register":


                if datos["role"] == "client":


                    dispositivos[websocket] = {

                        "role":"client",

                        "name":datos["name"]

                    }


                    print()
                    print("========== CLIENTE ==========")
                    print("Nombre:", datos["name"])
                    print("=============================")



                elif datos["role"] == "viewer":


                    dispositivos[websocket] = {

                        "role":"viewer"

                    }


                    print()
                    print("========== VIEWER ==========")
                    print("Viewer registrado")
                    print("=============================")




            # CLIENTE ENVIA PANTALLA

            elif datos["type"] == "screen":


                info_pc = dispositivos.get(websocket)


                if not info_pc:
                    continue


                nombre_pc = info_pc["name"]



                mensaje_pantalla = json.dumps({

                    "type":"screen",

                    "image":datos["image"]

                })



                for viewer, pc_seleccionada in list(selecciones.items()):


                    if pc_seleccionada == nombre_pc:


                        try:

                            await viewer.send(mensaje_pantalla)


                        except:

                            pass





            # VIEWER ELIGE UNA PC

            elif datos["type"] == "select_device":


                nombre = datos["name"]


                info_viewer = dispositivos.get(websocket)



                if info_viewer and info_viewer["role"] == "viewer":


                    selecciones[websocket] = nombre


                    print(
                        "Viewer seleccionó:",
                        nombre
                    )






            # VIEWER PIDE LISTA DE PCS

            elif datos["type"] == "list_devices":


                lista = []



                for dispositivo in dispositivos.values():


                    if dispositivo["role"] == "client":


                        lista.append({

                            "name":dispositivo["name"],

                            "status":"online"

                        })



                respuesta = {


                    "type":"device_list",

                    "devices":lista

                }



                await websocket.send(

                    json.dumps(respuesta)

                )







            elif datos["type"] == "ping":


                info = dispositivos.get(websocket)


                if info:


                    if info["role"] == "client":

                        print(
                            "PING <-",
                            info["name"]
                        )

                    else:

                        print(
                            "PING <- VIEWER"
                        )





    except websockets.ConnectionClosed:

        pass




    finally:


        if websocket in dispositivos:

            del dispositivos[websocket]


        if websocket in selecciones:

            del selecciones[websocket]



        clientes.remove(websocket)


        print("[-] Cliente desconectado")
        print(
            "Conexiones activas:",
            len(clientes)
        )







async def main():


    print("===================================")
    print(" SERVIDOR REMOTEVIEW INICIADO ")
    print(" Puerto: 8765")
    print("===================================")



    PORT = int(
        os.environ.get(
            "PORT",
            8765
        )
    )



    async with websockets.serve(

        manejar_cliente,

        "0.0.0.0",

        PORT

    ):


        await asyncio.Future()





asyncio.run(main())