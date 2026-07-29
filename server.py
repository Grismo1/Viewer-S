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


            # ======================================================
            # MENSAJES BINARIOS (PANTALLA)
            # ======================================================

            if isinstance(mensaje, bytes):


                info_pc = dispositivos.get(websocket)


                if not info_pc:
                    continue


                nombre_pc = info_pc["name"]



                for viewer, pc_seleccionada in list(selecciones.items()):


                    if pc_seleccionada == nombre_pc:


                        try:

                            await viewer.send(mensaje)


                        except:

                            pass



                continue




            # ======================================================
            # MENSAJES JSON
            # ======================================================


            try:

                datos = json.loads(mensaje)


            except:


                print("Mensaje JSON inválido")

                continue



            print("MENSAJE:")
            print(datos)




            # ======================================================
            # REGISTRO
            # ======================================================


            if datos["type"] == "register":



                if datos["role"] == "client":


                    nombre = datos["name"]



                    # ==========================================
                    # EVITAR CLIENTES DUPLICADOS
                    # ==========================================


                    for ws, info in list(dispositivos.items()):


                        if (
                            info.get("role") == "client"
                            and info.get("name") == nombre
                            and ws != websocket
                        ):


                            print(
                                "Cliente duplicado encontrado:",
                                nombre
                            )


                            try:

                                await ws.close()


                            except:

                                pass



                            dispositivos.pop(ws, None)




                    dispositivos[websocket] = {

                        "role": "client",

                        "name": nombre

                    }



                    print()
                    print("========== CLIENTE ==========")
                    print("Nombre:", nombre)
                    print("=============================")



                elif datos["role"] == "viewer":



                    dispositivos[websocket] = {


                        "role":"viewer"


                    }



                    print()
                    print("========== VIEWER ==========")
                    print("Viewer registrado")
                    print("=============================")




            # ======================================================
            # VIEWER SELECCIONA PC
            # ======================================================


            elif datos["type"] == "select_device":



                nombre = datos["name"]



                info = dispositivos.get(websocket)



                if info and info["role"] == "viewer":



                    selecciones[websocket] = nombre



                    print(
                        "Viewer seleccionó:",
                        nombre
                    )






            # ======================================================
            # LISTA DE PCS
            # ======================================================


            elif datos["type"] == "list_devices":



                lista = []



                for dispositivo in dispositivos.values():



                    if dispositivo["role"] == "client":



                        lista.append({


                            "name": dispositivo["name"],

                            "status":"online"


                        })





                await websocket.send(json.dumps({


                    "type":"device_list",

                    "devices":lista


                }))






            # ======================================================
            # PING
            # ======================================================


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



    except Exception as e:


        print("Error:", e)




    finally:



        dispositivos.pop(websocket, None)


        selecciones.pop(websocket, None)


        clientes.discard(websocket)



        print("[-] Cliente desconectado")

        print(
            "Conexiones activas:",
            len(clientes)
        )





async def main():


    print("===================================")

    print(" SERVIDOR REMOTEVIEW INICIADO ")

    print(
        " Puerto:",
        os.environ.get("PORT",8765)
    )

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

        PORT,

        max_size=None

    ):


        await asyncio.Future()






asyncio.run(main())