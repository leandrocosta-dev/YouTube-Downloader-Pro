import streamlit as st
import yt_dlp
import os
import time

# --- Configuração Inicial ---
st.set_page_config(page_title="YouTube Downloader Pro", page_icon="🎵", layout="centered")

# CSS Estilizado
st.markdown("""
    <style>
    .stTextInput input {
        border-radius: 10px;
        padding: 10px;
    }
    .stButton button {
        border-radius: 10px;
        height: 45px;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Diretório de Download
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- Gerenciamento de Estado ---
if 'view' not in st.session_state:
    st.session_state.view = 'search'
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_video' not in st.session_state:
    st.session_state.selected_video = None

# --- Funções de Backend ---
def search_youtube(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'default_search': f'ytsearch{max_results}',
        'ignoreerrors': True,
        'no_warnings': True,
        'extract_flat': True,  # Otimização crucial para busca rápida sem bloqueio
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if not info: return []
            if 'entries' in info: return [e for e in info['entries'] if e is not None]
            return [info]
        except Exception:
            return []

def download_media(url, format_type):
    """
    Baixa e converte a mídia.
    Correção de áudio: Usa MKV se MP4 falhar ou força recodificação.
    """
    timestamp = int(time.time())

    # Opções Base
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    if format_type == 'audio':
        # Configuração para Áudio (MP3)
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # Configuração para Vídeo (MP4 com Áudio)
        # Tenta pegar fluxos que já sejam compatíveis com MP4 primeiro
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4', # Força a união em MP4
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            # Ajuste de extensão final
            if format_type == 'audio':
                filename = os.path.splitext(filename)[0] + ".mp3"

            # Verifica se o arquivo existe (correção para merge mp4)
            # Às vezes o yt-dlp muda a extensão automaticamente para mkv se o mp4 falhar
            base_name = os.path.splitext(filename)[0]

            if not os.path.exists(filename):
                if os.path.exists(base_name + ".mkv"):
                    filename = base_name + ".mkv"
                elif os.path.exists(base_name + ".webm"):
                    filename = base_name + ".webm"
                elif os.path.exists(base_name + ".mp4"):
                    filename = base_name + ".mp4"

            return filename, info.get('title', 'midia')

    except Exception as e:
        return None, str(e)

# --- Interface Principal ---
st.title("🎵 YouTube Downloader Pro")

# --- TELA 1: BUSCA ---
if st.session_state.view == 'search':
    col_search, col_btn = st.columns([4, 1])

    with col_search:
        query = st.text_input("Buscar", placeholder="Digite nome ou link...", label_visibility="collapsed")

    with col_btn:
        search_clicked = st.button("🔍 Buscar")

    if search_clicked and query:
        if query.startswith("http"):
            st.session_state.selected_video = {
                'url': query, 'title': 'Link Direto', 'thumbnail': None, 'uploader': 'YouTube'
            }
            st.session_state.view = 'download'
            st.rerun()
        else:
            with st.spinner("Pesquisando..."):
                st.session_state.search_results = search_youtube(query)

            if st.session_state.search_results:
                st.write("### Resultados")
                for i, entry in enumerate(st.session_state.search_results):
                    # Tenta pegar a URL de várias formas possíveis
                    url = entry.get('webpage_url') or entry.get('url')
                    if not url:
                        # Se não tiver URL completa, constrói com o ID
                        vid_id = entry.get('id')
                        if vid_id: url = f"https://www.youtube.com/watch?v={vid_id}"
                        else: continue
                    
                    title = entry.get('title', 'Sem título')
                    uploader = entry.get('uploader', 'Desconhecido')
                    
                    # Tenta pegar thumbnails de forma mais robusta
                    thumbnails = entry.get('thumbnails', [])
                    thumb = None
                    if thumbnails:
                        thumb = thumbnails[-1].get('url')
                    else:
                        # Fallback para thumbnail padrão do YouTube se não vier na busca flat
                        vid_id = entry.get('id')
                        if vid_id:
                            thumb = f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if thumb: st.image(thumb, use_container_width=True)
                    with c2:
                        st.subheader(title)
                        st.caption(f"📺 {uploader}")
                        if st.button("Selecionar ➔", key=f"sel_{i}"):
                            st.session_state.selected_video = {
                                'url': url, 'title': title, 'thumbnail': thumb, 'uploader': uploader
                            }
                            st.session_state.view = 'download'
                            st.rerun()
                    st.divider()

            else:
                st.warning("Nenhum resultado encontrado. Tente colar o link direto do vídeo.")

# --- TELA 2: DOWNLOAD ---
elif st.session_state.view == 'download' and st.session_state.selected_video:
    video_data = st.session_state.selected_video

    if st.button("⬅️ Nova Pesquisa"):
        st.session_state.view = 'search'
        st.session_state.search_results = []
        st.session_state.selected_video = None
        st.rerun()

    st.divider()
    st.success(f"**Selecionado:** {video_data['title']}")

    try:
        st.video(video_data['url'])
    except:
        if video_data['thumbnail']: st.image(video_data['thumbnail'], width=300)

    st.write("### ⬇️ Opções de Download")

    ftype = st.radio("Escolha o formato:", ["MP4 (Vídeo HD)", "MP3 (Áudio HD)"], horizontal=True)
    target_type = 'audio' if 'MP3' in ftype else 'video'

    if st.button(f"Baixar {target_type.upper()}", type="primary"):
        with st.status("Processando...", expanded=True) as status:
            file_path, info = download_media(video_data['url'], target_type)

            if file_path and os.path.exists(file_path):
                status.update(label="✅ Sucesso!", state="complete", expanded=False)

                # Detecta MIME type correto
                mime_type = "audio/mpeg" if target_type == 'audio' else "video/mp4"
                if file_path.endswith(".mkv"): mime_type = "video/x-matroska"

                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"💾 Salvar {os.path.basename(file_path)}",
                        data=f,
                        file_name=os.path.basename(file_path),
                        mime=mime_type
                    )
            else:
                status.update(label="❌ Falha", state="error")
                st.error(f"Erro: {info}")

