import yt_dlp
import requests
import pyperclip
import re
import tkinter as tk
from tkinter import messagebox
import traceback
import xml.etree.ElementTree as ET

def extract_youtube_id(url_input):
    """
    Extrae el ID de un video de YouTube de varios formatos de URL.
    """
    if not url_input:
        return None
    url_input = str(url_input).strip()
    youtube_regex = (
        r'(?:https?://)?(?:www\.)?'
        r'(?:youtube\.com/(?:watch\?v=|live\?v=|shorts/)|youtu\.be/)'
        r'([A-Za-z0-9_-]{11})'
    )
    match = re.search(youtube_regex, url_input)
    return match.group(1) if match else None

def descargar_y_parsear_subtitulos(url):
    """
    Descarga un archivo de subtítulos VTT o SRT desde la URL y lo parsea.
    Devuelve una lista de líneas de texto.
    """
    try:
        resp = requests.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Error al descargar subtítulos: {e}")
        traceback.print_exc()
        return None

    lines = resp.text.splitlines()
    transcript = []
    for line in lines:
        line = line.strip()
        # Omitir líneas vacías, numeración y timestamps
        if not line or re.match(r'^\d+$', line) or '-->' in line or re.match(r'^\d{2}:\d{2}:\d{2}\.', line):
            continue
        transcript.append(line)
    transcript = extraer_texto_de_p(transcript)
    return transcript

def obtener_transcripcion(video_id):
    """
    Obtiene la transcripción de un video de YouTube usando yt-dlp.
    Intenta en este orden:
        1) auto-generated Spanish (es)
        2) auto-generated English (en)
        3) manual Spanish (es)
        4) manual English (en)
    Devuelve una lista de líneas de texto, o None si no hay transcript.
    """
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['es', 'en'],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)

    except Exception as e:
        print(f"❌ Error al extraer info del video: {e}")
        traceback.print_exc()
        return None

    # Fuentes en orden: auto-generated, luego manual
    for source in ('subtitles','automatic_captions'):
        captions = info.get(source) or {}
        for lang in ['es', 'en']:
            if lang in captions:
                entries = captions[lang]
                # Elegir la primera pista .vtt/.srt/ttml
                entry = next((c for c in entries if c.get('ext') in ('vtt', 'srt', 'ttml')), entries[0])
                url = entry.get('url')
                if url:
                    print(f"✅ Transcripción encontrada ({source}) en: {lang}")
                    return descargar_y_parsear_subtitulos(url)

    print("❌ No se encontró transcripción en ningún idioma soportado.")
    return None

def extraer_texto_de_p(lineas):
    """
    Dada una lista de líneas como
    '<p begin="..." end="..." style="...">Texto aquí</p>',
    devuelve una lista con 'Texto aquí' para cada línea válida.
    """
    textos = []
    for linea in lineas:
        linea = linea.strip()
        try:
            # Parseamos la línea como XML y obtenemos el texto del nodo <p>
            elemento = ET.fromstring(linea)
            if elemento.text:
                textos.append(elemento.text.strip())
        except ET.ParseError:
            # Si no es un <p> bien formado, lo ignoramos
            continue
    return textos

def main():
    # Inicializar Tkinter para diálogos
    root = tk.Tk()
    root.withdraw()

    # Extraer ID desde el portapapeles
    clipboard_content = pyperclip.paste()
    video_id = extract_youtube_id(clipboard_content)
    if not video_id:
        messagebox.showerror("Error", "No hay un enlace de YouTube válido en el portapapeles.")
        root.destroy()
        return

    # Obtener la transcripción
    transcript = obtener_transcripcion(video_id)
    if not transcript:
        messagebox.showerror("Error", "No se encontró transcripción para este video.")
        root.destroy()
        return

    # Unir líneas y crear prompt
    transcript_text = ' '.join(transcript)
    prompt = f"""
    I'm going to give you the full transcript of a YouTube video. Please read it and write a summary in Spanish that is clear, well-structured, and easy to understand for someone who hasn't watched the video. It doesn't need to be super short; instead, focus on fully developing the main ideas, key points, and any final conclusions or takeaways. If possible, organize the summary into thematic sections or parts of the content, so it's easier to follow.

    Full transcript:
    {transcript_text}
    """

    pyperclip.copy(prompt)
    #messagebox.showinfo("Éxito", "Prompt copiado al portapapeles.")
    root.destroy()

if __name__ == "__main__":
    main()

    