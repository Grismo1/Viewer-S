import asyncio
import websockets
import json
import os


clientes = set()

# websocket -> datos del dispositivo
dispositivos = {}

# viewer websocket -> nombre PC seleccionada
selecciones = {}

# nombre PC -> lista de cámaras
camera_lists = {}




async def enviar_json(ws, datos):

    try:

        await ws.send(
            json.dumps(datos)
        )

    except:

        pass





async def manejar_cliente(websocket):


    clientes.add(websocket)


    print("[+] Cliente conectado")
    print(
        "Conexiones activas:",
        len(clientes)
    )



    try:


        async for mensaje in websocket:



            # ======================================================
            # FRAMES BINARIOS
            # SCREEN / CAMERA
            # ======================================================


            if isinstance(mensaje, bytes):


                info_pc = dispositivos.get(
                    websocket
                )



                if not info_pc:

                    continue



                if info_pc.get("role") != "client":

                    continue



                nombre_pc = info_pc["name"]




                for viewer, pc in list(selecciones.items()):


                    if pc == nombre_pc:


                        try:

                            await viewer.send(
                                mensaje
                            )

                        except:

                            pass



                continue







            # ======================================================
            # JSON
            # ======================================================



            try:

                datos = json.loads(
                    mensaje
                )


            except:


                print(
                    "JSON inválido"
                )

                continue




            print(
                "MENSAJE:",
                datos
            )




            tipo = datos.get(
                "type"
            )





            # ======================================================
            # REGISTER
            # ======================================================


            if tipo == "register":



                role = datos.get(
                    "role"
                )



                # -------------------------
                # CLIENTE PC
                # -------------------------


                if role == "client":


                    nombre = datos.get(
                        "name",
                        "PC"
                    )



                    # eliminar duplicados


                    for ws, info in list(dispositivos.items()):


                        if (

                            info.get("role") == "client"

                            and info.get("name") == nombre

                            and ws != websocket

                        ):


                            print(
                                "Cliente duplicado:",
                                nombre
                            )


                            try:

                                await ws.close()

                            except:

                                pass



                            dispositivos.pop(
                                ws,
                                None
                            )





                    dispositivos[websocket] = {


                        "role":"client",

                        "name":nombre


                    }




                    print()
                    print(
                        "========== CLIENTE =========="
                    )
                    print(
                        nombre
                    )
                    print(
                        "============================="
                    )





                # -------------------------
                # VIEWER
                # -------------------------


                elif role == "viewer":



                    dispositivos[websocket] = {


                        "role":"viewer"


                    }



                    print()
                    print(
                        "========== VIEWER =========="
                    )
                    print(
                        "Viewer conectado"
                    )
                    print(
                        "============================="
                    )








            # ======================================================
            # LISTAR PCS
            # ======================================================


            elif tipo == "list_devices":



                lista = []



                for info in dispositivos.values():



                    if info.get("role") == "client":



                        lista.append({

                            "name":info["name"],

                            "status":"online"

                        })





                await enviar_json(

                    websocket,

                    {

                        "type":"device_list",

                        "devices":lista

                    }

                )







            # ======================================================
            # SELECCIONAR PC
            # ======================================================


                        # ======================================================
            # SELECCIONAR PC
            # ======================================================


            elif tipo == "select_device":


                nombre = datos.get(
                    "name"
                )


                info = dispositivos.get(
                    websocket
                )


                if info and info.get("role") == "viewer":


                    selecciones[websocket] = nombre


                    print(
                        "Viewer seleccionó:",
                        nombre
                    )



                    # enviar cámaras disponibles si existen


                    if nombre in camera_lists:


                        await enviar_json(

                            websocket,

                            {

                                "type":"camera_list",

                                "cameras":camera_lists[nombre]

                            }

                        )



                    # ==============================
                    # PRUEBA CONTROL REMOTO
                    # ==============================


                    for ws, info_pc in dispositivos.items():


                        if (

                            info_pc.get("role") == "client"

                            and info_pc.get("name") == nombre

                        ):


                            await enviar_json(

                                ws,

                                {

                                    "type":"mouse_move",

                                    "x":500,

                                    "y":300

                                }

                            )


                            print(
                                "Prueba mouse enviada"
                            )


                            break
            # ======================================================
            # CLIENTE ENVIA LISTA DE CAMARAS
            # ======================================================


            elif tipo == "camera_list":



                nombre = datos.get(
                    "device"
                )


                cams = datos.get(
                    "cameras",
                    []
                )



                camera_lists[nombre] = cams



                print(
                    "Cámaras de",
                    nombre,
                    ":",
                    cams
                )




                # avisar al viewer que esté mirando esa PC


                for viewer, pc in list(selecciones.items()):



                    if pc == nombre:



                        await enviar_json(

                            viewer,

                            {

                                "type":"camera_list",

                                "cameras":cams

                            }

                        )







            # ======================================================
            # CAMBIAR CAMARA
            # ======================================================


            elif tipo == "set_camera":



                pc = selecciones.get(
                    websocket
                )



                if not pc:

                    continue




                nueva = datos.get(
                    "camera"
                )



                for ws, info in dispositivos.items():



                    if (

                        info.get("role") == "client"

                        and info.get("name") == pc

                    ):



                        await enviar_json(

                            ws,

                            {

                                "type":"set_camera",

                                "camera":nueva

                            }

                        )



                        print(
                            "Cambio cámara",
                            pc,
                            nueva
                        )



                        break
                        # ======================================================
            # CONTROL REMOTO
            # MOUSE / TECLADO
            # ======================================================


            elif tipo in [

                "mouse_move",

                "mouse_click",

                "mouse_scroll",

                "key_press"

            ]:



                info_viewer = dispositivos.get(
                    websocket
                )



                if not info_viewer:

                    continue



                if info_viewer.get("role") != "viewer":

                    continue




                pc = selecciones.get(
                    websocket
                )



                if not pc:


                    print(
                        "Viewer sin PC seleccionada"
                    )


                    continue






                for ws, info_pc in dispositivos.items():



                    if (

                        info_pc.get("role") == "client"

                        and info_pc.get("name") == pc

                    ):



                        try:



                            await ws.send(

                                json.dumps(
                                    datos
                                )

                            )



                            print(
                                "Comando remoto enviado:",
                                datos
                            )



                        except Exception as e:



                            print(
                                "Error enviando comando:",
                                e
                            )



                        break        






            # ======================================================
            # PING
            # ======================================================


            elif tipo == "ping":


                info = dispositivos.get(
                    websocket
                )


                if info:


                    print(
                        "PING <-",
                        info.get("name","VIEWER")
                    )






    except websockets.ConnectionClosed:

        pass



    except Exception as e:


        print(
            "Error:",
            e
        )




    finally:



        info = dispositivos.pop(
            websocket,
            None
        )



        selecciones.pop(
            websocket,
            None
        )



        clientes.discard(
            websocket
        )



        if info:

            nombre = info.get(
                "name"
            )


            if nombre:

                camera_lists.pop(
                    nombre,
                    None
                )



        print(
            "[-] Cliente desconectado"
        )

        print(
            "Conexiones activas:",
            len(clientes)
        )







async def main():


    PORT = int(
        os.environ.get(
            "PORT",
            8765
        )
    )



    print(
        "==================================="
    )

    print(
        " SERVIDOR REMOTEVIEW INICIADO "
    )

    print(
        " Puerto:",
        PORT
    )

    print(
        "==================================="
    )





    async with websockets.serve(

        manejar_cliente,

        "0.0.0.0",

        PORT,

        max_size=None

    ):


        await asyncio.Future()





asyncio.run(main())