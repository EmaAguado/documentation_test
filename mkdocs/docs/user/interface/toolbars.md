### Barra de Menus 

La **"Barra de Menus"** se sitúa en la parte superior de la aplicación y tiene la siguiente disposición: 

![Toolbar menu](resources/img/toolbar-menu.png "Toolbar menu")

* **File**: contiene tres acciones: 
  * **Update GwaIO**: cuando haya alguna actualización de GwaIO se deberá pulsar este botón para obtenerla. 
  * **Remove empty folders**: elimina directorios vacíos que existan dentro del proyecto. 
  * **Manage enviroments**: abre una ventana para editar las variables de entorno de los proyectos. 
* **View**: activa o desactiva la visibilidad de paneles. 
* **Plugins**: inicializa el plugin seleccionado. Solo se puede inicializar un plugin a la vez. 
* **<"Nombre del Proyecto">**: activa o desactiva las "Barras de herramientas" de cada proyecto. 
* **Apps**: abre aplicaciones de trabajo desde GwaIO. 
* **Help**: muestra el dialogo de ayuda, hasta la fecha sólo tiene un "About". 

### Barra de Estado 

Muestra diversos mensajes dependiendo de cuál sea la última acción hecha por el artista. 
![Status bar detail](resources/img/status-bar-detail.png "Status bar detail")

## Barras de herramientas 
Las barras de herramientas, también conocidas como **"toolbars"** se pueden ocultar, mostrar, desacoplar de la interfaz o mover de posición al gusto del usuario. Cada una de estas barras de herramientas contienen bonotes con funcionalidades que se describen a continuación. 

![Multiples toolbars](resources/img/multiples-toolbars.png "Multiples toolbars")

Algunas barras de herramientas (Toolbars). 

Para mostrar u ocultar las barras de herramientas, haga clic en **"Toolbars"** y/o **<"Nombre del proyecto">**, que se encuentra en la barra de menus, en la parte superior de la ventana, y seleccione o deseleccione las barras de herramientas que desee modificar. 

### Barra de herramientas del explorador 

| Icono        | Nombre del botón | Acción  |
| ------------ |:----------------:|:--------|
|![Button](resources/img/explorer_local.png "Button")|Open local folder | Abre la carpeta local de la tarea seleccionada. Esto es, la carpeta de la tarea dentro del sistema de ficheros local del ordenador que está ejecutando la aplicación. 
|![Button](resources/img/explorer_server.png "Button")|Open server folder | Abre la carpeta del servidor de la tarea seleccionada. Esto es, la carpeta de la tarea dentro del sistema de ficheros del servidor que está ejecutando la aplicación. Si el ordenador está en remoto, necesitará una VPN para acceder a esta carpeta. 
|![Button](resources/img/add_version.png "Button")|Add version | Crea un nuevo fichero para la tarea seleccionada. El número de version elegido se calcula como una unidad superior a la mayor versión encontrada en el sistema de ficheros local. Tiene varias opciones:  <ul><li>![submenu add file](resources/img/submenu-button-add-file.png "submenu add file")<li>**From selected file:** Crea una nueva versión en la tarea seleccionada a partir del archivo seleccionado en el explorador de ficheros.<li>**From <"extensión"> file:** Crea una nueva versión en la tarea seleccionada de la extensión dada por el submenú del botón. (<"extensión"> es equivalente al formato del archivo de versión que se desee)  <li>Cuando no hay ningún archivo, el programa recogerá la última versión de la tarea anterior. En caso de no haber tarea anterior o esta tarea no tuviese ningún archivo, se abrirá la carpeta de "Templates" asociada a su proyecto. 
|![Button](resources/img/publish.png "Button")|Publish version | Abre la ventana de publicador de versiones. Para más información consulte el epígrafe de **"Diálogo de Publicación"**. 



Tiene funcionalidades relacionadas con el manejo de ficheros. Además, tiene herramientas relacionadas con la publicación de versiones dentro de una base de datos. 


### Barra de herramientas de sincronización 
Tiene funcionalidades relacionadas con la sincronización de los sistemas de ficheros local y del servidor.  

| Icono        | Nombre del botón | Acción  |
| ------------ |:----------------:|:--------|
|![Button](resources/img/sync_local_to_server.png "Button")|Up task sync | Sincroniza todos los archivos desde el sistema de ficheros local hacia el sistema de ficheros del servidor de las tareas seleccionadas en el **"Panel de Tareas"** o sincroniza unicamente los ficheros seleccionados en el **Panel de ficheros**. 
|![Button](resources/img/sync_server_to_local.png "Button")|Down task sync | Sincroniza todos los archivos desde el sistema de ficheros del servidor hacia el sistema de ficheros local de las tareas seleccionadas en el **"Panel de Tareas"** o sincroniza unicamente los ficheros seleccionados en el **Panel de ficheros**. 
|![Button](resources/img/sync_server_to_local_mayas.png "Button")| Maya sync | Sincroniza las dependencias del archivo maya seleccionado del servidor hacia el sistema de ficheros local.


### Barra de herramientas de reproducción (Obsoleto)
Contiene herramientas relacionadas con la visualización y comprobación de ficheros. 

| Icono        | Nombre del botón | Acción  |
| ------------ |:----------------:|:--------|
|![Button](resources/img/player.png "Button")|Open in RV | Requiere tener instalado el programa RV. Permite previsualizar ficheros dentro del programa RV con distintas opciones:<ul><li>![submenu concat](resources/img/submenu-concat.png "submenu concat")<li>**Concat video**: abre en RV concatenando los archivos de video seleccionados en el explorador de ficheros. Si no hay ficheros seleccionados, are en RV concatenando el ultimo fichero de video que contenga cada tarea seleccionada en el **"Panel de Tareas"** siempre que no haya archivos seleccionados en el explorador de ficheros.<li>**Concat image:** Abre en RV concatenando los archivos de imagen seleccionados en el **"Panel de ficheros"**, si no hay ficheros seleccionados, abre en RV concatenando el ultimo fichero de imagen que contenga cada tarea seleccionada en el **"Panel de Tareas"** siempre que no haya archivos seleccionados en el explorador de ficheros.<li>**Open concatenator:** Abre el **"Panel de concatenar"**.  
|![Button](resources/img/compare.png "Button")|Compare in RV | Requiere tener instalado el programa RV. Permite comparar ficheros dentro del programa RV con distintas opciones:<ul><li>![submenu compare](resources/img/submenu-compare.png "submenu compare")<li>**Compare video:** Abre en RV en modo comparación los archivos de video seleccionados en el **"Panel de Ficheros"**. Si no hay ficheros seleccionados, abre en RV en modo comparación el ultimo fichero de video que contenga cada tarea seleccionada en el **"Panel de Tareas"**.<li>**Compare images:** Abre en RV en modo comparación los archivos de imagen seleccionados en el **"Panel de Ficheros"**. Si no hay ficheros seleccionados, abre en RV en modo comparación el ultimo fichero de video que contenga cada tarea seleccionada en el **"Panel de Tareas"**. 


### Barra de herramientas de SG 
Contiene funcionalidades relacionadas con Shotgrid.  

| Icono        | Nombre del botón | Acción  |
| ------------ |:----------------:|:--------|
|![Button](resources/img/synchronize.png "Button")|Refresh list of tasks | Actualiza la lista de tareas en el **"Panel del Tareas"**. Tienes que seleccionar qué tipo de entidad quieres previsualizar: Assets, Episodes, Sequences o Shots. <li>![submenu synchronize](resources/img/submenu-synchronize.png "submenu synchronize")
|![Button](resources/img/sgw.png "Button")|Open task in shotgrid| Abre en el navegador de internet la página de Shotgrid de la tarea seleccionada en el **"Panel de Tareas"**. 
|![Button](resources/img/table.png "Button")|Open Check BDL | Abre el **"Panel de BDL"**. 
|![Button](resources/img/playlist.png "Button")|Open Download playlist version | Abre el **"Panel de descarga de listas de reproducción"**. 
|![Button](resources/img/sg_upload.png "Button")|Upload Package | Sube a la base de datos de Shotgrid los archivos seleccionados en el **"Panel de ficheros"**. 
|![Button](resources/img/sg_download.png "Button")|Download Package | Descarga al sistema de ficheros local el ultimo package de los archivos que hay subido a Shotgrid de la tarea seleccionada en el **"Panel de tareas"**. Como alternativa, podemos abrir la **"Tool Download Package"**. 
|![Button](resources/img/edl.png "Button")|Open EDL | Abre el **"Panel de EDL"**. 
|![Button](resources/img/timelog.png "Button")|Open Timelog | Abre el **"Panel de Timelog"**. 
|![Button](resources/img/open_rv.png "Button")|Open RV | Abre RV concatenando los shots previos y posteriores a la task seleccionada. Para usar este botón, seleccione una task de animación y apriete el boton **"Open RV"**, seleccione el paddin con la cantidad de videos anteriores y posteriores. 