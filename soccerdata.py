import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import glob
import plotly.express as px
import pdfkit
from jinja2 import Environment, FileSystemLoader
import base64
import hashlib
import os

# Configuración API
API_KEY = "1b18f0ff04a44cafb87fc7e206fd91cf"
HEADERS = {"X-Auth-Token": API_KEY}
COMPETITIONS_URL = "https://api.football-data.org/v4/competitions"

# Configuración página
st.set_page_config(
    page_title="Football Analytics Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. SISTEMA DE AUTENTICACIÓN CON GESTIÓN DE SESIONES
def manage_auth():
    """Gestiona autenticación y estado de sesión."""
    # Inicializar estado de sesión
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Mostrar formulario de login si no está autenticado
    if not st.session_state.authenticated:
        with st.form("Login"):
            st.write("🔐 Inicio de sesión")
            username = st.text_input("Usuario", key="user_input")
            password = st.text_input("Contraseña", type="password", key="pass_input")
            submitted = st.form_submit_button("Acceder")
            
            if submitted:
                if authenticate(username, password):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
        st.stop()  # Detener ejecución hasta autenticación

def authenticate(username, password):
    """Verifica credenciales con hash seguro."""
    hashed_pass = hashlib.sha256(password.encode()).hexdigest()
    # Usuario: admin | Contraseña: admin
    return username == "admin" and hashed_pass == "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"

# Verificar autenticación al inicio
manage_auth()

# 2. FUNCIONES DE CACHÉ
@st.cache_data(ttl=3600)
def get_competitions():
    try:
        response = requests.get(COMPETITIONS_URL, headers=HEADERS)
        response.raise_for_status()
        competitions = response.json()["competitions"]
        return [comp for comp in competitions if comp["name"] != "Campeonato Brasileiro Série A"]
    except Exception as e:
        st.error(f"Error al obtener competiciones: {str(e)}")
        return []

@st.cache_data(ttl=1800)
def get_standings(competition_id):
    try:
        url = f"{COMPETITIONS_URL}/{competition_id}/standings"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener clasificación: {str(e)}")
        return None

@st.cache_data(ttl=1800)
def get_scorers(competition_id):
    try:
        url = f"{COMPETITIONS_URL}/{competition_id}/scorers"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json().get("scorers", [])
    except Exception as e:
        st.error(f"Error al obtener goleadores: {str(e)}")
        return []

@st.cache_data(ttl=1800)
def get_teams(competition_id):
    try:
        url = f"{COMPETITIONS_URL}/{competition_id}/teams"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json().get("teams", [])
    except Exception as e:
        st.error(f"Error al obtener equipos: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def load_delanteros_data():
    try:
        # Ruta completa al archivo CSV
        ruta_csv = os.path.join(
            "C:/Users/RafaelMorenodelRio/Desktop/Master Python Avanzado al Deporte/mi_app_streamlit/data/processed/raw",
            "delantero_centro_ratings_2025-01-31.csv"
        )
        if not os.path.exists(ruta_csv):
            st.warning(f"No se encontró el archivo en la ruta: {ruta_csv}")
            return None
        return pd.read_csv(ruta_csv)
    except Exception as e:
        st.error(f"Error al cargar datos de delanteros centro: {str(e)}")
        return None

# 3. FUNCIONES PARA PDF
def generate_pdf(html_content, filename):
    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
    try:
        pdfkit.from_string(html_content, filename, configuration=config)
        return True
    except Exception as e:
        st.error(f"Error al generar PDF: {str(e)}")
        return False

def create_html_template(content, title):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("report_template.html")
    return template.render(content=content, title=title)

# 4. INTERFAZ PRINCIPAL
with st.sidebar:
    st.image("https://www.football-data.org/assets/logo.png", width=200)
    
    # Botón de logout
    if st.session_state.authenticated:
        if st.button("🚪 Cerrar sesión"):
            st.session_state.authenticated = False
            st.rerun()
    
    st.title("⚙ Configuración")
    menu_option = st.radio(
        "**Seleccionar módulo:**",
        ["🏆 Clasificación", "⚽ Goleadores", "👥 Equipos", "🎯 Delanteros Centro"],
        index=0
    )
    st.divider()
    st.markdown(f"""
    **Fuente de datos:**  
    [Football Data API](https://www.football-data.org/)  
    **Actualizado:** {datetime.now().strftime("%d/%m/%Y %H:%M")}  
    © 2024 Football Analytics Pro
    """)

# 5. LÓGICA DE LA APLICACIÓN
if menu_option in ["🏆 Clasificación", "⚽ Goleadores", "👥 Equipos"]:
    competitions = get_competitions()
    league_options = {comp["name"]: comp["id"] for comp in competitions}
    selected_league = st.selectbox("**Seleccionar Liga:**", list(league_options.keys()), index=0)
    selected_league_id = league_options[selected_league]

    if menu_option == "🏆 Clasificación":
        data = get_standings(selected_league_id)
        if data:
            standings = data.get("standings", [{}])[0].get("table", [])
            season = data.get("season", {})
            
            col1, col2 = st.columns([1, 4])
            with col1:
                emblem = data.get("competition", {}).get("emblem", "https://via.placeholder.com/150x150?text=No+Logo")
                st.image(emblem, width=120)
            with col2:
                st.markdown(f'<div class="header-text">Clasificación {data.get("competition", {}).get("name", "")}</div>', unsafe_allow_html=True)
                if season:
                    start_year = season.get("startDate", "")[:4]
                    end_year = season.get("endDate", "")[:4]
                    current_matchday = season.get("currentMatchday", "N/A")
                    st.caption(f"Temporada {start_year}-{end_year} | Jornada actual: {current_matchday}")
            
            if standings:
                cols = st.columns(4)
                with cols[0]:
                    st.metric("Equipos", len(standings))
                with cols[1]:
                    st.metric("Partidos jugados", standings[0].get("playedGames", "N/A"))
                with cols[2]:
                    best_attack = max(standings, key=lambda x: x.get("goalsFor", 0))
                    st.metric("Mejor ataque", f"{best_attack.get('team', {}).get('name', 'N/A')} ({best_attack.get('goalsFor', 0)})")
                with cols[3]:
                    best_defense = min(standings, key=lambda x: x.get("goalsAgainst", 0))
                    st.metric("Mejor defensa", f"{best_defense.get('team', {}).get('name', 'N/A')} ({best_defense.get('goalsAgainst', 0)})")

                df_data = []
                for team in standings:
                    team_info = {
                        "Pos": team.get("position", "N/A"),
                        "Equipo": f"<img src='{team.get('team', {}).get('crest', 'https://via.placeholder.com/25x25')}' width='25'> {team.get('team', {}).get('shortName', team.get('team', {}).get('name', 'N/A'))}",
                        "PJ": team.get("playedGames", 0),
                        "G": team.get("won", 0),
                        "E": team.get("draw", 0),
                        "P": team.get("lost", 0),
                        "GF": team.get("goalsFor", 0),
                        "GC": team.get("goalsAgainst", 0),
                        "DG": team.get("goalDifference", 0),
                        "PTS": team.get("points", 0)
                    }
                    df_data.append(team_info)
                
                df = pd.DataFrame(df_data)
                st.markdown(df.style.hide(axis="index").to_html(escape=False), unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("📊 Comparación de Goles")
                gf_gc_df = pd.DataFrame({
                    "Equipo": [team.get("team", {}).get("name", "N/A") for team in standings],
                    "GF": [team.get("goalsFor", 0) for team in standings],
                    "GC": [team.get("goalsAgainst", 0) for team in standings]
                })
                fig = px.bar(gf_gc_df, x="Equipo", y=["GF", "GC"], barmode="group", title="Goles a Favor vs En Contra")
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")
                with st.container():
                    st.subheader("📤 Opciones de Exportación")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🖨️ Imprimir Clasificación"):
                            st.markdown("<script>window.print()</script>", unsafe_allow_html=True)
                    with col2:
                        if st.button("📥 Exportar a PDF"):
                            html_content = create_html_template(df.to_html(escape=False), f"Clasificación {selected_league}")
                            if generate_pdf(html_content, "clasificacion.pdf"):
                                with open("clasificacion.pdf", "rb") as f:
                                    st.download_button("Descargar PDF", f, file_name=f"clasificacion_{selected_league}.pdf")

    elif menu_option == "⚽ Goleadores":
        scorers = get_scorers(selected_league_id)
        if scorers:
            st.markdown(f'<div class="header-text">Máximos Goleadores - {selected_league}</div>', unsafe_allow_html=True)
            
            scorers_df = pd.DataFrame([{
                "Jugador": scorer.get("player", {}).get("name", "N/A"),
                "Equipo": scorer.get("team", {}).get("name", "N/A"),
                "Goles": scorer.get("goals", 0),
                "Asistencias": scorer.get("assists", 0),
                "Partidos": scorer.get("playedMatches", "N/A"),
                "Goles/Partido": round(scorer.get("goals", 0) / scorer.get("playedMatches", 1), 2) if scorer.get("playedMatches", 0) > 0 else 0.0
            } for scorer in scorers])

            st.dataframe(scorers_df, use_container_width=True, hide_index=True, height=600)

            st.markdown("---")
            fig = px.scatter(scorers_df, x="Goles", y="Asistencias", color="Equipo", size="Goles/Partido", hover_name="Jugador")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            with st.container():
                st.subheader("📤 Opciones de Exportación")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🖨️ Imprimir Goleadores"):
                        st.markdown("<script>window.print()</script>", unsafe_allow_html=True)
                with col2:
                    if st.button("📥 Exportar a PDF"):
                        img_bytes = fig.to_image(format="png")
                        html_content = create_html_template(
                            scorers_df.to_html() + f'<img src="data:image/png;base64,{base64.b64encode(img_bytes).decode()}">',
                            f"Goleadores {selected_league}"
                        )
                        if generate_pdf(html_content, "goleadores.pdf"):
                            with open("goleadores.pdf", "rb") as f:
                                st.download_button("Descargar PDF", f, file_name=f"goleadores_{selected_league}.pdf")

    elif menu_option == "👥 Equipos":
        teams = get_teams(selected_league_id)
        if teams:
            st.markdown(f'<div class="header-text">Equipos de {selected_league}</div>', unsafe_allow_html=True)
            selected_team = st.selectbox("Seleccionar equipo:", [team.get("name", "Equipo") for team in teams])
            team = next((t for t in teams if t.get("name") == selected_team), None)
            
            if team:
                col1, col2 = st.columns([1, 3])
                with col1:
                    crest = team.get("crest", "https://via.placeholder.com/150x150?text=Sin+Escudo")
                    st.image(crest, width=150)
                with col2:
                    st.markdown(f"""
                    <div class="team-card">
                        <h2>{selected_team}</h2>
                        <p>🏟️ {team.get('venue', 'Desconocido')}</p>
                        <p>🎨 Colores: {team.get('clubColors', 'N/A')}</p>
                        <p>🌍 {team.get('address', 'N/A')}</p>
                        <p>🔗 <a href="{team.get('website', '#')}" target="_blank">Sitio web</a></p>
                    </div>
                    """, unsafe_allow_html=True)

                squad = team.get('squad', [])
                if squad:
                    players_df = pd.DataFrame([{
                        "Nombre": player.get("name", "N/A"),
                        "Posición": player.get("position", "N/A"),
                        "Nacionalidad": player.get("nationality", "N/A"),
                        "Fecha Nacimiento": player.get("dateOfBirth", "N/A"),
                        "Edad": datetime.now().year - int(player.get("dateOfBirth", "1900")[:4]) if player.get("dateOfBirth") else "N/A"
                    } for player in squad])
                    
                    st.dataframe(players_df, use_container_width=True, hide_index=True, height=600)

                    st.markdown("---")
                    with st.container():
                        st.subheader("📤 Opciones de Exportación")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🖨️ Imprimir Equipo"):
                                st.markdown("<script>window.print()</script>", unsafe_allow_html=True)
                        with col2:
                            if st.button("📥 Exportar a PDF"):
                                html_content = create_html_template(players_df.to_html(), f"Equipo {selected_team}")
                                if generate_pdf(html_content, "equipo.pdf"):
                                    with open("equipo.pdf", "rb") as f:
                                        st.download_button("Descargar PDF", f, file_name=f"equipo_{selected_team}.pdf")

elif menu_option == "🎯 Delanteros Centro":
    st.markdown(f'<div class="header-text">Análisis de Delanteros Centro</div>', unsafe_allow_html=True)
    delanteros_df = load_delanteros_data()
    
    if delanteros_df is not None:
        # Selección de competición
        selected_competicion = st.selectbox("**Seleccionar Competición:**", delanteros_df['Liga'].unique(), index=0)
        delanteros_filtrados = delanteros_df[delanteros_df['Liga'] == selected_competicion]
        
        # Filtrar solo las columnas que deseas mostrar
        columnas_a_mostrar = ['Nombre', 'Equipo', 'Liga', 'Fin de contrato', 'rank']
        delanteros_filtrados = delanteros_filtrados[columnas_a_mostrar]
        
        # Mostrar el DataFrame filtrado
        st.dataframe(delanteros_filtrados, use_container_width=True)

        st.markdown("---")
        with st.container():
            st.subheader("📤 Opciones de Exportación")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🖨️ Imprimir Datos"):
                    st.markdown("<script>window.print()</script>", unsafe_allow_html=True)
            with col2:
                if st.button("📥 Exportar a PDF"):
                    html_content = create_html_template(delanteros_filtrados.to_html(), "Análisis de Delanteros")
                    if generate_pdf(html_content, "delanteros.pdf"):
                        with open("delanteros.pdf", "rb") as f:
                            st.download_button("Descargar PDF", f, file_name=f"delanteros_{selected_competicion}.pdf")
