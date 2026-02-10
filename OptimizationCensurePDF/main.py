import os
import re
import io
import warnings
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
import easyocr

# Silenciar warnings de PyTorch y otros
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Cargar variables de entorno
load_dotenv()

# Configuración
CEDULA = os.getenv("CEDULA", "1016071566")
CELULAR = os.getenv("CELULAR", "3022538972")
CODIGO = os.getenv("CODIGO", "94120210445")
QUALITY = int(os.getenv("QUALITY", "75"))
DPI = int(os.getenv("DPI", "150"))

# Directorios
PDF_DIR = Path("pdfs")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Inicializar OCR (español e inglés) con GPU
print("Inicializando OCR con GPU...")
reader = easyocr.Reader(["es", "en"], gpu=True, verbose=False)
print("✓ OCR listo con aceleración GPU\n")


def normalize_number(text):
    """Elimina puntos, espacios y guiones de un texto para comparar números"""
    return re.sub(r"[.\s\-]", "", text)


def find_sensitive_in_text(text, cedula, celular, codigo):
    """Verifica si un texto contiene datos sensibles"""
    text_norm = normalize_number(text)
    cedula_norm = normalize_number(cedula)
    celular_norm = normalize_number(celular)
    codigo_norm = normalize_number(codigo)

    if cedula_norm in text_norm or cedula in text:
        return True
    if celular_norm in text_norm or celular in text:
        return True
    if codigo_norm in text_norm or codigo in text:
        return True
    return False


def find_sensitive_text_in_page(page, image_np, cedula, celular, codigo, zoom):
    """
    Detecta datos sensibles usando:
    1. Búsqueda de texto en PDF (si existe texto seleccionable)
    2. OCR en la imagen renderizada (para PDFs escaneados)
    Devuelve coordenadas ya convertidas al espacio de la imagen.
    """
    sensitive_rects = []

    # Método 1: Buscar texto seleccionable en el PDF
    try:
        text = page.get_text()
        if text.strip():  # Si hay texto
            # Buscar todas las variantes
            search_terms = [
                cedula,
                celular,
                codigo,
                normalize_number(cedula),
                normalize_number(celular),
                normalize_number(codigo),
            ]

            # Agregar variantes con formato
            if len(cedula) == 10:
                search_terms.append(
                    f"{cedula[0]}.{cedula[1:4]}.{cedula[4:7]}.{cedula[7:]}"
                )
            if len(codigo) == 11:
                search_terms.append(
                    f"{codigo[0:2]}.{codigo[2:5]}.{codigo[5:8]}.{codigo[8:]}"
                )

            for term in search_terms:
                if term:
                    rects = page.search_for(str(term))
                    # Convertir coordenadas PDF a coordenadas de imagen
                    for rect in rects:
                        img_rect = {
                            "x0": rect.x0 * zoom,
                            "y0": rect.y0 * zoom,
                            "x1": rect.x1 * zoom,
                            "y1": rect.y1 * zoom,
                        }
                        sensitive_rects.append(img_rect)
    except Exception as e:
        print(f"    Advertencia al buscar texto: {str(e)}")

    # Método 2: OCR en la imagen (para escaneos o verificación adicional)
    try:
        # Realizar OCR
        ocr_results = reader.readtext(image_np, detail=1)

        # Analizar cada resultado del OCR
        for bbox, text, conf in ocr_results:
            # Verificar si el texto contiene datos sensibles
            if find_sensitive_in_text(text, cedula, celular, codigo):
                # bbox de OCR ya está en coordenadas de imagen
                # bbox es [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]

                img_rect = {
                    "x0": min(x_coords),
                    "y0": min(y_coords),
                    "x1": max(x_coords),
                    "y1": max(y_coords),
                }
                sensitive_rects.append(img_rect)
    except Exception as e:
        print(f"    Advertencia OCR: {str(e)}")

    return len(sensitive_rects) > 0, sensitive_rects


def censor_image(image, sensitive_rects):
    """Censura áreas específicas de datos sensibles en la imagen"""
    if not sensitive_rects:
        return image

    # Crear una copia para no modificar la original
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)

    # Censurar cada rectángulo encontrado
    for rect in sensitive_rects:
        # Las coordenadas ya vienen en píxeles de imagen
        x0 = int(rect["x0"])
        y0 = int(rect["y0"])
        x1 = int(rect["x1"])
        y1 = int(rect["y1"])

        # Expandir un poco el área para asegurar cobertura completa
        padding = 5
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(image.width, x1 + padding)
        y1 = min(image.height, y1 + padding)

        # Asegurar que las coordenadas estén en el orden correcto
        x_min = min(x0, x1)
        x_max = max(x0, x1)
        y_min = min(y0, y1)
        y_max = max(y0, y1)

        # Validar que el rectángulo tenga área válida
        if x_max > x_min and y_max > y_min:
            # Dibujar rectángulo negro
            draw.rectangle([x_min, y_min, x_max, y_max], fill="black")

    return img_copy


def process_pdf(pdf_path):
    """Procesa un PDF: detecta datos sensibles, censura y convierte a .webp"""
    print(f"Procesando: {pdf_path.name}")

    try:
        # Abrir PDF con PyMuPDF
        doc = fitz.open(pdf_path)
        pdf_name = pdf_path.stem
        sensitive_count = 0
        total_pages = len(doc)

        print(f"  Documento con {total_pages} página(s)")

        # Procesar cada página
        for page_num in range(total_pages):
            page = doc[page_num]

            # Renderizar página como imagen con el DPI especificado
            zoom = DPI / 72  # 72 DPI es la base de PDF
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Convertir a PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            # Convertir a numpy array para OCR
            image_np = np.array(image)

            # Detectar si tiene datos sensibles y obtener coordenadas
            print(f"  Analizando página {page_num + 1} (texto + OCR)...")
            has_sensitive, sensitive_rects = find_sensitive_text_in_page(
                page, image_np, CEDULA, CELULAR, CODIGO, zoom
            )

            # Censurar si es necesario
            if has_sensitive:
                sensitive_count += 1
                print(
                    f"  ⚠ Página {page_num + 1}: {len(sensitive_rects)} dato(s) sensible(s) - Censurando"
                )
                image = censor_image(image, sensitive_rects)

            # Optimizar imagen antes de guardar
            # Convertir a RGB si tiene canal alpha (reduce tamaño)
            if image.mode in ("RGBA", "LA", "P"):
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                rgb_image.paste(
                    image,
                    mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None,
                )
                image = rgb_image
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Guardar como .webp con máxima optimización
            output_filename = f"{pdf_name}_page{page_num:02d}.webp"
            output_path = OUTPUT_DIR / output_filename

            image.save(
                output_path,
                "WEBP",
                quality=QUALITY,
                method=6,  # Máxima compresión (0-6)
                lossless=False,  # Usar compresión con pérdida
                optimize=True,
            )

            # Mostrar tamaño del archivo
            file_size = output_path.stat().st_size / 1024  # KB
            print(
                f"  ✓ Página {page_num + 1} guardada: {output_filename} ({file_size:.1f} KB)"
            )

        doc.close()

        if sensitive_count > 0:
            print(
                f"✓ {pdf_path.name} completado ({total_pages} páginas, {sensitive_count} con datos censurados)\n"
            )
        else:
            print(f"✓ {pdf_path.name} completado ({total_pages} páginas)\n")

    except Exception as e:
        print(f"✗ Error procesando {pdf_path.name}: {str(e)}\n")
        import traceback

        traceback.print_exc()


def main():
    print("=" * 60)
    print("OPTIMIZADOR Y CONVERTIDOR DE PDFs")
    print("=" * 60)
    print(f"Calidad WebP: {QUALITY}")
    print(f"DPI: {DPI}")
    print(f"Datos a censurar: CC={CEDULA}, Tel={CELULAR}, Código={CODIGO}")
    print("=" * 60)
    print()

    # Verificar que exista la carpeta pdfs
    if not PDF_DIR.exists():
        print("✗ Error: La carpeta 'pdfs' no existe")
        print("  Creando carpeta 'pdfs'...")
        PDF_DIR.mkdir(exist_ok=True)
        print(
            "  Por favor, coloca tus archivos PDF en la carpeta 'pdfs' y ejecuta nuevamente."
        )
        return

    # Obtener todos los PDFs
    pdf_files = list(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print("✗ No se encontraron archivos PDF en la carpeta 'pdfs'")
        return

    print(f"Se encontraron {len(pdf_files)} archivo(s) PDF\n")

    # Procesar cada PDF
    for pdf_file in pdf_files:
        process_pdf(pdf_file)

    print("=" * 60)
    print(f"✓ PROCESO COMPLETADO")
    print(f"✓ Todas las imágenes están en la carpeta: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
