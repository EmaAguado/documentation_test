---
hide:
  - toc
  - navigation
---

<div class="banner">
  <video
    id="banner-video"
    class="banner-video"
    autoplay
    muted
    loop
    playsinline
    src="assets/video/gwaio_teaser.mp4"
    type="video/mp4"
  ></video>
  <div class="banner-content">
    <h1>GwaIO</h1>
    <p class="subtitle">Potencia tu Pipeline</p>
    <a class="btn" href="user/setup" target="_blank">User Guide</a>
    <a class="btn" href="dev/home"   target="_blank">Dev Guide</a>
  </div>
</div>


<script>
  document.addEventListener('scroll', () => {
    const video = document.getElementById('banner-video');
    const scrollY = window.pageYOffset;
    const translateY = -scrollY * 0.3;
    // mantenemos el zoom 1.2 y movemos solo en Y
    video.style.transform = `translate(-50%, calc(-50% + ${translateY}px)) scale(1.5)`;
  });
</script>


<p></p>
<p></p>

**GwaIO es una aplicación de escritorio diseñada para optimizar y simplificar la producción audiovisual a través de potentes automatizaciones.**

![type:video](assets/video/gwaio_teaser.mp4){ align=right }


GwaIO actúa como un puente inteligente entre la estación de trabajo del artista, el servidor compartido y la base de datos del proyecto. Esto se traduce en un flujo de trabajo más ágil y eficiente, minimizando errores humanos y facilitando tareas cotidianas como:


<br></br>

<figure markdown="span">
  ![Gwaio file system](assets/img/diagrama-gwaio.png "Diagrama del sistema de archivos de GwaIO")
</figure>

<br></br>

* **Creación de ficheros con el naming convention adecuado.**
* **Subida y gestión de archivos en servidor y base de datos.**
* **Exportación y guardado de ficheros de forma consistente.**
<br></br>

# **Beneficios Clave de GwaIO:**

<br></br>


<div class="grid cards" style="grid-template-columns: repeat(4, minmax(0,1fr));" markdown>

-   :material-rocket:{ .lg .middle } __Aumento de la Productividad__

    ---

    Trabaja más rápido gracias a la automatización de tareas repetitivas y la simplificación del flujo de trabajo. GwaIO permite integrar herramientas y scripts que agilizan las tareas repetitivas.

-   :material-shield-check:{ .lg .middle } __Reducción de Errores__

    ---

    Minimiza el error humano al automatizar procesos críticos, garantizando resultados consistentes y de alta calidad.


-   :material-factory:{ .lg .middle } __Control de Producción Mejorado__

    ---

    Asegura que todo el material producido cumpla con los estándares establecidos y se almacene correctamente.

-   :material-currency-eur:{ .lg .middle } __Reducción de Costes__

    ---

    Integra utilidades que a menudo requieren software externo, como la sincronización de archivos local/servidor, reduciendo licencias y gastos operativos.


</div>

<br></br>

# **¿Cómo funciona GwaIO en la práctica?**

Se presenta a los artistas con una interfaz intuitiva, una lista clara de tareas pendientes. Además, facilita la generación de nuevos ficheros mediante la automatización de:

* **Nomenclatura de archivos.**
* **Recopilación automática de material de entrada de tareas previas.**
* **Publicación eficiente de nuevas versiones en la base de datos.**

Recopilacion de archivos de tarea previa < sincronizado de ficheros < Creación de archivo de version con naming correcto

<br></br>

# **Herramientas integradas**

**Unifica y controla tu pipeline con GwaIO**. Integra múltiples DCC de manera robusta y flexible. La arquitectura modular de GwaIO facilita la incorporación de cualquier software, adaptándose completamente a tus necesidades.

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

<div class="grid-container">
  <div class="md-button md-button--primary">
    <a href="">
      <img src="assets/img/logo_app_maya.png" alt="Maya">
      <div class="card-info">
        <h3>Maya</h3>
        <span class="status ready"><i class="fas fa-check-circle"></i></span>
      </div>
    </a>
  </div>

  <div class="md-button md-button--primary">
    <a href="">
      <img src="assets/img/logo_app_nuke.png" alt="Nuke">
      <div class="card-info">
        <h3>Nuke</h3>
        <span class="status wip"><i class="fas fa-hourglass-half"></i></span>
      </div>
    </a>
  </div>

  <div class="md-button md-button--primary">
    <a href="">
      <img src="assets/img/logo_app_deadline.png" alt="Deadline">
      <div class="card-info">
        <h3>Deadline</h3>
        <span class="status ready"><i class="fas fa-check-circle"></i></span>
      </div>
    </a>
  </div>

  <div class="md-button md-button--primary">
    <a href="">
      <img src="assets/img/logo_app_fpt.png" alt="FPT">
      <div class="card-info">
        <h3>FPT</h3>
        <span class="status ready"><i class="fas fa-check-circle"></i></span>
      </div>
    </a>
  </div>

  <div class="md-button md-button--primary">
    <a href="">
      <img src="assets/img/logo_app_substance.png" alt="Substance">
      <div class="card-info">
        <h3>Substance</h3>
        <span class="status ready"><i class="fas fa-check-circle"></i></span>
      </div>
    </a>
  </div>

  <div class="md-button md-button--primary">
    <a href="">
      <img src="assets/img/logo_app_psd.png" alt="Photoshop">
      <div class="card-info">
        <h3>Photoshop</h3>
        <span class="status wip"><i class="fas fa-hourglass-half"></i></span>
      </div>
    </a>
  </div>
</div>


# **Explora la Documentación:**

A lo largo de esta documentación, profundizaremos en cada una de estas funcionalidades y te guiaremos para sacar el máximo provecho de GwaIO en tu pipeline de producción 3D. [Comienza a explorar aquí](user/setup.md) 
