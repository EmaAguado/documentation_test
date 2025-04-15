import fitz
import os
import sys

def export_images(pdf_path, output_folder):
    # Abrir el PDF
    doc = fitz.open(pdf_path)
    
    # Crear carpeta de salida si no existe
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    image_count = 0
    
    # Recorrer cada página
    for page_index in range(len(doc)):
        page = doc[page_index]
        # Extraer imágenes de la página
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            # Extraer pixmap de la imagen
            pix = fitz.Pixmap(doc, xref)
            
            # Si la imagen tiene más de 4 componentes, convertir a RGB
            if pix.n >= 5:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            
            # Definir nombre de archivo
            img_filename = os.path.join(output_folder, f"page{page_index+1}_img{img_index}.png")
            
            # Guardar imagen
            pix.save(img_filename)
            print(f"Imagen guardada: {img_filename}")
            image_count += 1
            
            # Liberar recursos
            pix = None

    print(f"Total de imágenes exportadas: {image_count}")




if __name__ == "__main__":
    inp = r"D:\scripts\documentation_tools\pdf\mut_documentation_model_w001.pdf"
    out = "./md_out"
    export_images(inp,out)
    # if len(sys.argv) != 3:
    #     print("Uso: python pdf_to_md.py archivo.pdf salida.md")
    # else:
    #     pdf_to_md(sys.argv[1], sys.argv[2])


# from marker.converters.pdf import PdfConverter
# from marker.models import create_model_dict
# from marker.output import text_from_rendered

# # Configuración del convertidor
# converter = PdfConverter(
#     artifact_dict=create_model_dict(),
# )

# # Convierte el PDF (reemplaza "ruta/al/archivo.pdf" por el camino a tu PDF)
# rendered = converter(r"D:\scripts\documentation_tools\pdf\concept_art\mut_documentation_bdl_v001.pdf")

# # Extrae el Markdown, metadata e imágenes
# markdown_text, metadata, images = text_from_rendered(rendered)

# # Guarda el resultado en un archivo Markdown
# with open("./out/salida.md", "w", encoding="utf8") as f:
#     f.write(markdown_text)
