from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import qrcode

# ========= Helpers =========
def _to_number(x, name):
    try:
        return float(x)
    except Exception:
        raise TypeError(f"El parámetro '{name}' debe ser numérico (mm). Recibido: {type(x).__name__} -> {x}")

def mm_to_px(mm, dpi=300):
    """
    Convierte mm a px. Acepta:
      - escalar (int/float/str convertible)
      - secuencia (tuple/list) -> convierte cada elemento
    """
    if isinstance(mm, (list, tuple)):
        return tuple(int(round(_to_number(v, "mm_item") / 25.4 * dpi)) for v in mm)
    return int(round(_to_number(mm, "mm") / 25.4 * dpi))

def definir_colores() -> dict:
    return {
        "Organizer": (255, 99, 71),
        "Speaker":   (70, 130, 180),
        "Sponsor":   (255, 165, 0),
        "Attendee":  (34, 139, 34)
    }

def resize_to_fit(img, max_w, max_h):
    w, h = img.size

    # Imagen más grande → reducir
    if w > max_w or h > max_h:
        scale = min(max_w / w, max_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return img.resize((new_w, new_h), Image.LANCZOS)

    # Imagen más pequeña → NO ampliar (evita pixelación)
    return img



def cargar_logo(width, logo_path, top_margin_mm=10, scale=0.55, dpi=300):
    logo = Image.open(logo_path).convert("RGBA")
    logo_width = int(width * scale)
    ratio = logo_width / logo.width
    logo_height = int(logo.height * ratio)
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    x = (width - logo_width) // 2
    y = mm_to_px(top_margin_mm, dpi)
    return (logo, x, y, logo_height)

def definir_letra(url_fuentes):
    try:
        font_perfil     = ImageFont.truetype(url_fuentes + "Bitcount-Regular.ttf", 80)
        font_nombre     = ImageFont.truetype(url_fuentes + "Bitcount-Regular.ttf", 60)
        font_afiliacion = ImageFont.truetype(url_fuentes + "Bitcount-Regular.ttf", 40)
    except:
        font_perfil     = ImageFont.truetype("arialbd.ttf", 80)
        font_nombre     = ImageFont.truetype("arialbd.ttf", 60)
        font_afiliacion = ImageFont.truetype("arial.ttf", 40)
    return (font_perfil, font_nombre, font_afiliacion)

def generar_qr(qr_data, size_px=230):
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    img = img.resize((size_px, size_px), Image.LANCZOS)
    return img

def draw_crop_marks(draw, rect, mark_length_px, gap_px, stroke=2):
    x0, y0, x1, y1 = rect
    # sup-izq
    draw.line([(x0 - gap_px - mark_length_px, y0), (x0 - gap_px, y0)], fill="black", width=stroke)
    draw.line([(x0, y0 - gap_px - mark_length_px), (x0, y0 - gap_px)], fill="black", width=stroke)
    # sup-der
    draw.line([(x1 + gap_px, y0), (x1 + gap_px + mark_length_px, y0)], fill="black", width=stroke)
    draw.line([(x1, y0 - gap_px - mark_length_px), (x1, y0 - gap_px)], fill="black", width=stroke)
    # inf-izq
    draw.line([(x0 - gap_px - mark_length_px, y1), (x0 - gap_px, y1)], fill="black", width=stroke)
    draw.line([(x0, y1 + gap_px), (x0, y1 + gap_px + mark_length_px)], fill="black", width=stroke)
    # inf-der
    draw.line([(x1 + gap_px, y1), (x1 + gap_px + mark_length_px, y1)], fill="black", width=stroke)
    draw.line([(x1, y1 + gap_px), (x1, y1 + gap_px + mark_length_px)], fill="black", width=stroke)

def draw_lanyard_hole(draw, content_w, hole_diameter_px, hole_offset_px, stroke=3):
    cx = content_w // 2
    cy = hole_offset_px
    r  = hole_diameter_px // 2
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.ellipse(bbox, outline="black", width=stroke)
    cross = max(6, r // 2)
    draw.line([(cx - cross, cy), (cx + cross, cy)], fill="black", width=1)
    draw.line([(cx, cy - cross), (cx, cy + cross)], fill="black", width=1)

def crea_acreditacion(
    datos_personales,
    background_path,
    logo_path,
    output_path,
    url_fuentes,
    *,
    dpi=300,
    content_width_mm=80,
    content_height_mm=120,
    outer_margin_mm=6,
    hole_diameter_mm=7,
    hole_offset_mm=7,
    # Ajustes para subir las cajas:
    top_safe_mm=4,
    perfil_height_mm=6,
    nombre_block_height_mm=16,
    gap_mm=1,
    # Fila de 3 imágenes (logo–QR–logo):
    three_col_row_height_mm=10,
    three_col_horizontal_margin_mm=8,
    three_col_gap_mm=6,
    three_col_vertical_offset_mm=0,   # <<--- AJUSTA ESTO para subir/bajar la fila centrada (mm)
    # Sponsors (contenedor único con 3 filas):
    sponsor_row_heights_mm=(3, 5, 6),   # (SUPPORTING, SILVER, GOLD) mm
    sponsor_row_gap_mm=3,
    sponsor_container_side_margin_mm=6,
    sponsor_container_bottom_gap_mm=6,
    sponsor_container_inner_pad_mm=3,
    sponsor_cell_gap_mm=6,
    sponsor_container_corner_radius_mm=4,
    sponsor_container_blur_radius=10,
    sponsor_container_white_alpha=140,
    sponsors_supporting_paths=None,
    sponsors_silver_paths=None,
    sponsors_gold_paths=None,
    # Rutas (fila inferior):
    logo_left_path=None,
    logo_right_path=None,
    qr_default_path=None
):
    """
    La fila de 3 (logo–QR–logo) queda centrada automáticamente entre la caja de institución
    y el contenedor de sponsors. Para afinar, usa `three_col_vertical_offset_mm`
    (positivo = baja; negativo = sube). El contenedor de sponsors NO se mueve.
    """
    # Datos
    perfil, nombre, afiliacion, qr_data = datos_personales[0], datos_personales[1], datos_personales[2], datos_personales[3]

    # Normalización anti-tuplas en content_width_mm
    if isinstance(content_width_mm, (list, tuple)) and not isinstance(content_height_mm, (int, float, str)):
        if len(content_width_mm) == 2:
            content_width_mm, content_height_mm = content_width_mm
        else:
            raise TypeError("content_width_mm como secuencia debe tener longitud 2: (ancho_mm, alto_mm)")

    # Validaciones básicas
    content_width_mm  = _to_number(content_width_mm,  "content_width_mm")
    content_height_mm = _to_number(content_height_mm, "content_height_mm")
    outer_margin_mm   = _to_number(outer_margin_mm,   "outer_margin_mm")
    hole_diameter_mm  = _to_number(hole_diameter_mm,  "hole_diameter_mm")
    hole_offset_mm    = _to_number(hole_offset_mm,    "hole_offset_mm")
    top_safe_mm       = _to_number(top_safe_mm,       "top_safe_mm")
    perfil_height_mm  = _to_number(perfil_height_mm,  "perfil_height_mm")
    nombre_block_height_mm = _to_number(nombre_block_height_mm, "nombre_block_height_mm")
    gap_mm            = _to_number(gap_mm,            "gap_mm")
    three_col_row_height_mm        = _to_number(three_col_row_height_mm, "three_col_row_height_mm")
    three_col_horizontal_margin_mm = _to_number(three_col_horizontal_margin_mm, "three_col_horizontal_margin_mm")
    three_col_gap_mm               = _to_number(three_col_gap_mm, "three_col_gap_mm")
    three_col_vertical_offset_mm   = _to_number(three_col_vertical_offset_mm, "three_col_vertical_offset_mm")

    # Conversión mm -> px
    cw = mm_to_px(content_width_mm, dpi)
    ch = mm_to_px(content_height_mm, dpi)
    outer = mm_to_px(outer_margin_mm, dpi)
    gap = mm_to_px(gap_mm, dpi)
    top_safe = mm_to_px(top_safe_mm, dpi)
    perfil_h = mm_to_px(perfil_height_mm, dpi)
    nombre_h = mm_to_px(nombre_block_height_mm, dpi)
    row_h = mm_to_px(three_col_row_height_mm, dpi)
    row_margin_x = mm_to_px(three_col_horizontal_margin_mm, dpi)
    row_gap = mm_to_px(three_col_gap_mm, dpi)
    row_v_offset = mm_to_px(three_col_vertical_offset_mm, dpi)

    # Fondo contenido
    bg_content = Image.open(background_path).convert("RGBA").resize((cw, ch), Image.LANCZOS)
    draw_content = ImageDraw.Draw(bg_content)

    # Logo superior
    logo, lx, ly, l_h = cargar_logo(cw, logo_path, top_margin_mm=8, scale=0.52, dpi=dpi)
    bg_content.paste(logo, (lx, ly), logo)

    # Tipografías
    font_perfil, font_nombre, font_afiliacion = definir_letra(url_fuentes)

    # Troquel
    draw_lanyard_hole(draw_content, cw, mm_to_px(hole_diameter_mm, dpi), mm_to_px(hole_offset_mm, dpi), stroke=3)

    # Cajetines de perfil y nombre/afiliación
    perfil_color = definir_colores().get(perfil, (0, 0, 0))
    perfil_top = top_safe + l_h + gap
    perfil_bot = perfil_top + perfil_h
    draw_content.rectangle([(0, perfil_top), (cw, perfil_bot)], fill=perfil_color)
    draw_content.text((cw/2, (perfil_top + perfil_bot)//2),
                      perfil.upper(), font=font_perfil, fill="white", anchor="mm")

    nombre_top = perfil_bot
    nombre_bot = nombre_top + nombre_h
    draw_content.rectangle([(0, nombre_top), (cw, nombre_bot)], fill=(255, 255, 255, 235))
    draw_content.text((cw/2, nombre_top + int(nombre_h*0.32)), nombre,
                      font=font_nombre, fill="black", anchor="mm")
    draw_content.text((cw/2, nombre_top + int(nombre_h*0.72)), afiliacion,
                      font=font_afiliacion, fill="gray", anchor="mm")

    # ===========================
    # CONTENEDOR ÚNICO SPONSORS
    # ===========================
    sponsors_supporting_paths = sponsors_supporting_paths or []
    sponsors_silver_paths     = sponsors_silver_paths or []
    sponsors_gold_paths       = sponsors_gold_paths or []

    # Orden: SUPPORTING (arriba), SILVER (medio), GOLD (abajo)
    row_heights_px = tuple(mm_to_px(v, dpi) for v in sponsor_row_heights_mm)
    row_gap_px     = mm_to_px(sponsor_row_gap_mm, dpi)
    side_px        = mm_to_px(sponsor_container_side_margin_mm, dpi)
    bottom_gap_px  = mm_to_px(sponsor_container_bottom_gap_mm, dpi)
    inner_pad_px   = mm_to_px(sponsor_container_inner_pad_mm, dpi)
    cell_gap_px    = mm_to_px(sponsor_cell_gap_mm, dpi)
    corner_px      = mm_to_px(sponsor_container_corner_radius_mm, dpi)

    rows = [
        ("Supporting Sponsor", sponsors_supporting_paths, row_heights_px[0]),
        ("Silver Sponsor",     sponsors_silver_paths,     row_heights_px[1]),
        ("Golden Sponsor",       sponsors_gold_paths,       row_heights_px[2]),
    ]
    rows = [(title, paths, h) for (title, paths, h) in rows if len(paths) > 0]

    container_top = None
    container_bottom = None
    inner_left = inner_right = None

    if rows:
        # Texto de título por fila
        title_h_px = mm_to_px(2.5, dpi)  # altura reservada para texto
        inner_rows_h = sum(h + title_h_px for _,_,h in rows) + row_gap_px * (len(rows)-1)
        container_h = inner_rows_h + inner_pad_px*2

        # Rect del contenedor (NO se mueve)
        container_left   = side_px
        container_right  = cw - side_px
        container_bottom = ch - bottom_gap_px
        container_top    = container_bottom - container_h
        container_w      = container_right - container_left

        # Fondo “frosted”
        cont_box = (container_left, container_top, container_right, container_bottom)
        bg_crop  = bg_content.crop(cont_box).filter(ImageFilter.GaussianBlur(radius=sponsor_container_blur_radius))
        overlay  = Image.new("RGBA", (container_w, container_h), (255, 255, 255, sponsor_container_white_alpha))
        frosted  = Image.alpha_composite(bg_crop, overlay)

        # Esquinas redondeadas
        mask = Image.new("L", (container_w, container_h), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle([0, 0, container_w, container_h], radius=corner_px, fill=255)
        bg_content.paste(frosted, (container_left, container_top), mask)

        # Área interna
        inner_left   = container_left + inner_pad_px
        inner_right  = container_right - inner_pad_px
        cur_y        = container_top + inner_pad_px

        # Fuente títulos (alineados a la izquierda, sin espacio extra)
        try:
            font_titles = ImageFont.truetype(url_fuentes + "Bitcount-Regular.ttf", mm_to_px(1.8, dpi))
        except:
            font_titles = ImageFont.truetype("arialbd.ttf", mm_to_px(1.8, dpi))

        def paste_fit_full(img, box_w, box_h):
            w, h = img.size
            s = min(box_w / w, box_h / h)
            new_w = max(1, int(w * s))
            new_h = max(1, int(h * s))
            return img.resize((new_w, new_h), Image.LANCZOS)

        # Render filas
        for (title, paths, row_h_px) in rows:
            # Título a la izquierda
            draw_content.text(
                (inner_left, cur_y),
                title.upper(),
                font=font_titles,
                fill=(60, 60, 60, 255),
                anchor="la"
            )
            # Línea divisoria bajo el título
            line_y = cur_y + title_h_px - mm_to_px(0.5, dpi)
            draw_content.line(
                [(inner_left, line_y), (inner_right, line_y)],
                fill=(0, 0, 0, 150),
                width=1
            )
            logos_top = line_y + mm_to_px(0.8, dpi)

            n = len(paths)
            if n > 0:
                inner_w = inner_right - inner_left
                col_w = int((inner_w - (n-1)*cell_gap_px) / n)
                col_h = row_h_px
                cx = inner_left
                for p in paths:
                    try:
                        simg = Image.open(p).convert("RGBA")
                        simg = paste_fit_full(simg, col_w, col_h)
                        px = cx + (col_w - simg.width)//2
                        py = logos_top + (col_h - simg.height)//2
                        bg_content.paste(simg, (px, py), simg)
                    except Exception:
                        pass
                    cx += col_w + cell_gap_px

            cur_y = logos_top + row_h_px + row_gap_px

    # ==================================
    # Fila de 3 (logo – QR – logo) CENTRADA
    # ==================================
    # Cálculo de columnas
    total_inner_w = cw - 2*row_margin_x
    col_w = (total_inner_w - 2*row_gap) // 3
    col_h = row_h
    col_x1 = row_margin_x
    col_x2 = row_margin_x + col_w + row_gap
    col_x3 = row_margin_x + 2*(col_w + row_gap)

    # def paste_centered_fit(img, box_w, box_h):
    #     w, h = img.size
    #     scale = min(box_w / w, box_h / h)
    #     new_w = max(1, int(w * scale))
    #     new_h = max(1, int(h * scale))
    #     return img.resize((new_w, new_h), Image.LANCZOS)


    def paste_fit_full(img, box_w, box_h):
        img = resize_to_fit(img, box_w, box_h)
        return img

    # Limites verticales para centrar: desde nombre_bot hasta container_top
    # (si no hay contenedor de sponsors, centramos respecto al fondo inferior con bottom_gap)
    if container_top is not None:
        available_h = container_top - nombre_bot
        row_top = nombre_bot + (available_h - row_h)//2 + row_v_offset
    else:
        # fallback: centra entre nombre_bot y (ch - margen inferior teórico)
        fallback_bottom = ch - mm_to_px(8, dpi)
        available_h = max(1, fallback_bottom - nombre_bot)
        row_top = nombre_bot + (available_h - row_h)//2 + row_v_offset

    row_bottom = row_top + row_h

    # Columna 1 → logo izquierda
    if logo_left_path:
        left_img = Image.open(logo_left_path).convert("RGBA")
        # left_img = paste_centered_fit(left_img, col_w, col_h)
        left_img = paste_fit_full(left_img, col_w, col_h)
        bg_content.paste(
            left_img,
            (col_x1 + (col_w - left_img.width)//2,
             row_top + (col_h - left_img.height)//2),
            left_img
        )

    # Columna 2 → QR
    if qr_data:
        qr_img = generar_qr(qr_data, size_px=min(col_w, col_h))
    else:
        if qr_default_path:
            qr_img = Image.open(qr_default_path).convert("RGBA")
            # qr_img = paste_centered_fit(qr_img, col_w, col_h)
            qr_img = paste_fit_full(qr_img, col_w, col_h)
        else:
            qr_img = generar_qr("https://example.com", size_px=min(col_w, col_h))

    bg_content.paste(
        qr_img,
        (col_x2 + (col_w - qr_img.width)//2,
         row_top + (col_h - qr_img.height)//2),
        qr_img
    )

    # Columna 3 → logo derecha
    if logo_right_path:
        right_img = Image.open(logo_right_path).convert("RGBA")
        # right_img = paste_centered_fit(right_img, col_w, col_h)
        right_img = paste_fit_full(right_img, col_w, col_h)
        bg_content.paste(
            right_img,
            (col_x3 + (col_w - right_img.width)//2,
             row_top + (col_h - right_img.height)//2),
            right_img
        )

    # ---- Lienzo final con marcas de corte ----
    final_w = cw + 2*outer
    final_h = ch + 2*outer
    canvas = Image.new("RGB", (final_w, final_h), "white")
    canvas.paste(bg_content, (outer, outer), bg_content)

    draw_canvas = ImageDraw.Draw(canvas)
    rect = (outer, outer, outer + cw, outer + ch)
    draw_crop_marks(draw_canvas, rect,
                    mark_length_px=mm_to_px(3, dpi),
                    gap_px=mm_to_px(1, dpi),
                    stroke=2)

    # Guardar
    canvas.save(output_path + ".png")
    canvas.convert("RGB").save(output_path + ".pdf", "PDF", resolution=dpi)
    print(f"Acreditación generada: {output_path}.png / .pdf")
