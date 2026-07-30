import asyncio
import websockets
import json
import os


clientes = set()

# websocket -> datos dispositivo
dispositivos = {}

# viewer websocket -> pc seleccionada
selecciones = {}

# pc -> cámaras
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


    print(
        "[+] Cliente conectado"
    )

    print(
        "Conexiones:",
        len(clientes)
    )



    try:


        async for mensaje in websocket:



            # ==================================================
            # FRAMES BINARIOS
            # ==================================================

            if isinstance(mensaje, bytes):


                info = dispositivos.get(
                    websocket
                )


                if not info:

                    continue



                if info.get("role") != "client":

                    continue



                nombre = info["name"]



                for viewer, pc in list(selecciones.items()):


                    if pc == nombre:


                        try:

                            await viewer.send(
                                mensaje
                            )

                        except:

                            pass



                continue





            # ==================================================
            # JSON
            # ==================================================


            try:

                datos=json.loads(
                    mensaje
                )


            except:

                continue




            tipo=datos.get(
                "type"
            )





            # ==================================================
            # REGISTER
            # ==================================================


            if tipo=="register":


                role=datos.get(
                    "role"
                )



                if role=="client":


                    nombre=datos.get(
                        "name",
                        "PC"
                    )



                    # cerrar duplicado


                    for ws,info in list(dispositivos.items()):


                        if (

                            info.get("role")=="client"

                            and info.get("name")==nombre

                            and ws!=websocket

                        ):


                            try:

                                await ws.close()

                            except:

                                pass



                            dispositivos.pop(
                                ws,
                                None
                            )





                    dispositivos[websocket]={


                        "role":"client",

                        "name":nombre,

                        "screen_width":datos.get(
                            "screen_width",
                            1920
                        ),

                        "screen_height":datos.get(
                            "screen_height",
                            1080
                        )

                    }





                    print(
                        "CLIENTE:",
                        nombre
                    )






                elif role=="viewer":


                    dispositivos[websocket]={

                        "role":"viewer"

                    }



                    print(
                        "VIEWER conectado"
                    )









            # ==================================================
            # LISTAR PCS
            # ==================================================


            elif tipo=="list_devices":



                lista=[]



                for info in dispositivos.values():


                    if info.get("role")=="client":


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








            # ==================================================
            # SELECCIONAR PC
            # ==================================================


            elif tipo=="select_device":


                nombre=datos.get(
                    "name"
                )


                info=dispositivos.get(
                    websocket
                )



                if info and info.get("role")=="viewer":



                    selecciones[websocket]=nombre



                    print(
                        "Seleccionado:",
                        nombre
                    )



                    if nombre in camera_lists:


                        await enviar_json(

                            websocket,

                            {

                                "type":"camera_list",

                                "cameras":camera_lists[nombre]

                            }

                        )









            # ==================================================
            # LISTA CAMARAS
            # ==================================================


            elif tipo=="camera_list":



                nombre=datos.get(
                    "device"
                )


                cams=datos.get(
                    "cameras",
                    []
                )



                camera_lists[nombre]=cams



                for viewer,pc in list(selecciones.items()):


                    if pc==nombre:


                        await enviar_json(

                            viewer,

                            {

                                "type":"camera_list",

                                "cameras":cams

                            }

                        )









            # ==================================================
            # CAMBIAR CAMARA
            # ==================================================


            elif tipo=="set_camera":


                pc=selecciones.get(
                    websocket
                )


                if not pc:

                    continue



                for ws,info in dispositivos.items():


                    if (

                        info.get("role")=="client"

                        and info.get("name")==pc

                    ):



                        await enviar_json(

                            ws,

                            {

                                "type":"set_camera",

                                "camera":datos.get(
                                    "camera"
                                )

                            }

                        )


                        break







            # ==================================================
            # CONTROL REMOTO
            # ==================================================


            elif tipo in [

                "mouse_move",

                "mouse_click",

                "mouse_scroll",

                "key_press"

            ]:



                viewer_info=dispositivos.get(
                    websocket
                )



                if not viewer_info:

                    continue



                if viewer_info.get("role")!="viewer":

                    continue




                pc=selecciones.get(
                    websocket
                )



                if not pc:

                    continue





                for ws,info in dispositivos.items():



                    if (

                        info.get("role")=="client"

                        and info.get("name")==pc

                    ):



                        comando=datos.copy()



                        # ESCALADO MOUSE

                        if tipo=="mouse_move":



                            ancho_pc=info.get(
                                "screen_width",
                                1920
                            )


                            alto_pc=info.get(
                                "screen_height",
                                1080
                            )



                            ancho_viewer=720

                            alto_viewer=1600



                            comando["x"]=int(

                                comando["x"] *
                                ancho_pc /
                                ancho_viewer

                            )



                            comando["y"]=int(

                                comando["y"] *
                                alto_pc /
                                alto_viewer

                            )





                        await ws.send(

                            json.dumps(
                                comando
                            )

                        )



                        break







    except websockets.ConnectionClosed:

        pass



    except Exception as e:


        print(
            "Error:",
            e
        )





    finally:



        info=dispositivos.pop(
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


            nombre=info.get(
                "name"
            )


            if nombre:

                camera_lists.pop(
                    nombre,
                    None
                )



        print(
            "[-] Desconectado"
        )








async def main():


    PORT=int(

        os.environ.get(
            "PORT",
            8765
        )

    )



    print(
        "SERVIDOR REMOTEVIEW INICIADO",
        PORT
    )



    async with websockets.serve(

        manejar_cliente,

        "0.0.0.0",

        PORT,

        max_size=None

    ):


        await asyncio.Future()





asyncio.run(
    main()
)