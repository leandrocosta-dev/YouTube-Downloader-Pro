import streamlit as st
import yt_dlp
import os
import time

# --- Configuração Inicial ---
st.set_page_config(page_title="YouTube Downloader Pro", page_icon="🎵", layout="centered")

# CSS Estilizado
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
    }
    .success-msg {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
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

# --- Configurações Anti-Bloqueio (403 Bypass) ---
def get_ydl_base_opts():
    """Retorna opções base para evitar detecção de bot"""
    return {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        # Simula um cliente Android para evitar bloqueio de IP de servidor
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['js', 'configs', 'web']
            }
        },
        # User Agent comum de navegador Desktop
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

# --- Funções de Backend ---

def search_youtube(query, max_results=5):
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'default_search': f'ytsearch{max_results}',
        'extract_flat': True, # Busca mais rápida, não extrai detalhes pesados
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if not info: return []
            if 'entries' in info: return [e for e in info['entries'] if e is not None]
            return [info]
        except Exception as e:
            print(f"Erro na busca: {e}")
            return []

def download_media(url, format_type):
    """
    Baixa e converte a mídia.
    Correção de áudio: Usa MKV se MP4 falhar ou força recodificação.
    """
    timestamp = int(time.time())
    
    # Pega as opções base anti-bloqueio
    ydl_opts = get_ydl_base_opts()
    
    # Adiciona configurações de saída
    ydl_opts.update({
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s_{timestamp}.%(ext)s',
    })

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
        # Tenta pegar fluxos que já sejam compatíveis com MP4 primeiro para evitar recodificação pesada
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
            
            # Verifica se o arquivo existe (correção para merge mp4 e variações do yt-dlp)
            base_name = os.path.splitext(filename)[0]
            
            final_file = None
            if os.path.exists(filename):
                final_file = filename
            elif os.path.exists(base_name + ".mkv"):
                final_file = base_name + ".mkv"
            elif os.path.exists(base_name + ".webm"):
                final_file = base_name + ".webm"
            elif os.path.exists(base_name + ".mp4"):
                final_file = base_name + ".mp4"
            
            if final_file:
                return final_file, info.get('title', 'midia')
            else:
                return None, "Arquivo não encontrado após download."

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
        # Verifica se é link direto
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
                    if not url: continue
                    
                    title = entry.get('title', 'Sem título')
                    uploader = entry.get('uploader', 'Desconhecido')
                    thumbnails = entry.get('thumbnails', [])
                    thumb = thumbnails[-1]['url'] if thumbnails else None
                    
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
                st.warning("Nenhum resultado encontrado.")

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
        with st.status("Processando (Isso pode demorar em nuvem)...", expanded=True) as status:
            st.write("Iniciando conexão segura...")
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
                st.info("Dica: Se persistir o erro 403, o IP do servidor pode estar em blacklist temporária.")
import streamlit as st
import yt_dlp
import os
import time

# --- Configuração Inicial ---
st.set_page_config(page_title="YouTube Downloader Pro", page_icon="🎵", layout="centered")

# CSS Estilizado
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
    }
    .success-msg {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
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

# --- Configurações Anti-Bloqueio (403 Bypass) ---
def get_ydl_base_opts():
    """Retorna opções base para evitar detecção de bot"""
    return {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        # Simula um cliente Android para evitar bloqueio de IP de servidor
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['js', 'configs', 'web']
            }
        },
        # User Agent comum de navegador Desktop
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

# --- Funções de Backend ---

def search_youtube(query, max_results=5):
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'default_search': f'ytsearch{max_results}',
        'extract_flat': True, # Busca mais rápida, não extrai detalhes pesados
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if not info: return []
            if 'entries' in info: return [e for e in info['entries'] if e is not None]
            return [info]
        except Exception as e:
            print(f"Erro na busca: {e}")
            return []

def download_media(url, format_type):
    """
    Baixa e converte a mídia.
    Correção de áudio: Usa MKV se MP4 falhar ou força recodificação.
    """
    timestamp = int(time.time())
    
    # Pega as opções base anti-bloqueio
    ydl_opts = get_ydl_base_opts()
    
    # Adiciona configurações de saída
    ydl_opts.update({
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s_{timestamp}.%(ext)s',
    })

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
        # Tenta pegar fluxos que já sejam compatíveis com MP4 primeiro para evitar recodificação pesada
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
            
            # Verifica se o arquivo existe (correção para merge mp4 e variações do yt-dlp)
            base_name = os.path.splitext(filename)[0]
            
            final_file = None
            if os.path.exists(filename):
                final_file = filename
            elif os.path.exists(base_name + ".mkv"):
                final_file = base_name + ".mkv"
            elif os.path.exists(base_name + ".webm"):
                final_file = base_name + ".webm"
            elif os.path.exists(base_name + ".mp4"):
                final_file = base_name + ".mp4"
            
            if final_file:
                return final_file, info.get('title', 'midia')
            else:
                return None, "Arquivo não encontrado após download."

    except Exception as e:
        return None, str(e)

# --- Interface Principal ---

st.title("🎵 YouTube Downloader Pro")

# --- TELA 1: BUSCA ---
if st.session_state.view == 'search':
    col_search, col_btn = st.columns([4, 1])
    
    with col_search:
        query = st.text_input("Buscar", placeholder="Digite nome ou link...", label_visibility="collapsed", key="search_input")
    
    with col_btn:
        search_clicked = st.button("🔍 Buscar")

    if search_clicked and query:
        # Verifica se é link direto
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
                    if not url: continue
                    
                    title = entry.get('title', 'Sem título')
                    uploader = entry.get('uploader', 'Desconhecido')
                    thumbnails = entry.get('thumbnails', [])
                    thumb = thumbnails[-1]['url'] if thumbnails else None
                    
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
                st.warning("Nenhum resultado encontrado.")

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
        with st.status("Processando (Isso pode demorar em nuvem)...", expanded=True) as status:
            st.write("Iniciando conexão segura...")
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
                st.info("Dica: Se persistir o erro 403, o IP do servidor pode estar em blacklist temporária.")

