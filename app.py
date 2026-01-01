import streamlit as st
import yt_dlp
import os
import time

# --- Configuração Inicial ---
st.set_page_config(page_title="YouTube Downloader Pro", page_icon="🎵", layout="centered")

# CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; }
    .success-msg { padding: 1rem; border-radius: 0.5rem; background-color: #d4edda; color: #155724; }
    </style>
""", unsafe_allow_html=True)

# Diretório
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- Estado ---
if 'view' not in st.session_state: st.session_state.view = 'search'
if 'search_results' not in st.session_state: st.session_state.search_results = []
if 'selected_video' not in st.session_state: st.session_state.selected_video = None

# --- CONFIGS (Modificadas para Robustez) ---

def get_search_opts():
    return {
        'quiet': True,
        'no_warnings': True,
        # Tenta pegar info sem baixar, mas de forma mais profunda
        'extract_flat': 'in_playlist', 
        'ignoreerrors': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

def get_download_opts():
    return {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        # Mantém Android para download (evita 403)
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['js', 'configs', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

# --- Funções Backend ---

def search_youtube(query, max_results=5):
    ydl_opts = get_search_opts()
    ydl_opts.update({'default_search': f'ytsearch{max_results}'})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # 1. Busca inicial
            info = ydl.extract_info(query, download=False)
            
            raw_entries = []
            if not info: return []
            
            if 'entries' in info:
                raw_entries = [e for e in info['entries'] if e is not None]
            else:
                raw_entries = [info]
            
            # 2. Refinamento (Correção do "Sem Título")
            final_results = []
            for entry in raw_entries:
                # Se o título estiver faltando ou for genérico, tenta buscar detalhes individuais
                title = entry.get('title')
                url = entry.get('webpage_url') or entry.get('url')
                
                if not url: continue
                
                # Se não tiver título, faz uma consulta rápida individual
                if not title or title == 'Sem título':
                    try:
                        # Consulta leve apenas para metadados
                        with yt_dlp.YoutubeDL({'quiet':True, 'ignoreerrors':True}) as ydl_mini:
                            mini_info = ydl_mini.extract_info(url, download=False, process=False)
                            if mini_info:
                                entry['title'] = mini_info.get('title', 'Vídeo sem nome')
                                entry['uploader'] = mini_info.get('uploader', 'Desconhecido')
                    except:
                        pass # Mantém o que tem se falhar
                
                final_results.append(entry)
                
            return final_results

        except Exception as e:
            print(f"Erro busca: {e}")
            return []

def download_media(url, format_type):
    timestamp = int(time.time())
    ydl_opts = get_download_opts()
    
    ydl_opts.update({
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s_{timestamp}.%(ext)s',
    })

    if format_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if format_type == 'audio':
                filename = os.path.splitext(filename)[0] + ".mp3"
            
            base_name = os.path.splitext(filename)[0]
            final_file = None
            
            if os.path.exists(filename): final_file = filename
            elif os.path.exists(base_name + ".mkv"): final_file = base_name + ".mkv"
            elif os.path.exists(base_name + ".webm"): final_file = base_name + ".webm"
            elif os.path.exists(base_name + ".mp4"): final_file = base_name + ".mp4"
            
            if final_file:
                return final_file, info.get('title', 'midia')
            else:
                return None, "Arquivo perdido."

    except Exception as e:
        return None, str(e)

# --- Interface ---

st.title("🎵 YouTube Downloader Pro")

if st.session_state.view == 'search':
    c1, c2 = st.columns([4, 1])
    with c1:
        query = st.text_input("Buscar", placeholder="Link ou nome...", label_visibility="collapsed")
    with c2:
        btn = st.button("🔍 Buscar")

    if btn and query:
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
                    url = entry.get('webpage_url') or entry.get('url')
                    title = entry.get('title', 'Sem título')
                    uploader = entry.get('uploader', 'Desconhecido')
                    
                    # Tenta pegar melhor thumbnail
                    thumb = None
                    if entry.get('thumbnails'):
                        thumb = entry['thumbnails'][-1]['url']
                    
                    # Layout Cartão
                    col_img, col_txt = st.columns([1, 3])
                    with col_img:
                        if thumb: st.image(thumb, use_container_width=True)
                        else: st.write("📷 Sem imagem")
                    with col_txt:
                        st.subheader(title)
                        st.caption(f"📺 {uploader}")
                        if st.button(f"Baixar este vídeo", key=f"btn_{i}"):
                            st.session_state.selected_video = {
                                'url': url, 'title': title, 'thumbnail': thumb, 'uploader': uploader
                            }
                            st.session_state.view = 'download'
                            st.rerun()
                st.divider()
            else:
                st.warning("Nada encontrado. Tente colar o link direto.")

elif st.session_state.view == 'download' and st.session_state.selected_video:
    data = st.session_state.selected_video
    if st.button("⬅️ Voltar"):
        st.session_state.view = 'search'
        st.session_state.search_results = []
        st.rerun()
        
    st.divider()
    st.markdown(f"### 🎬 {data['title']}")
    
    # Preview
    try:
        st.video(data['url'])
    except:
        if data['thumbnail']: st.image(data['thumbnail'])
    
    st.write("---")
    opt = st.radio("Formato:", ["MP4 (Vídeo)", "MP3 (Áudio)"], horizontal=True)
    target = 'audio' if 'MP3' in opt else 'video'
    
    if st.button("⬇️ INICIAR DOWNLOAD", type="primary"):
        with st.status("Baixando (pode demorar)...", expanded=True) as s:
            path, info = download_media(data['url'], target)
            if path and os.path.exists(path):
                s.update(label="✅ Pronto!", state="complete", expanded=False)
                mime = "audio/mpeg" if target == 'audio' else "video/mp4"
                with open(path, "rb") as f:
                    st.download_button("💾 Salvar Arquivo", f, os.path.basename(path), mime=mime)
            else:
                s.update(label="❌ Erro", state="error")
                st.error(f"Detalhe: {info}")
