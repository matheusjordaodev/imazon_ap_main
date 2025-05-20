# app/dashboards/ameaca_geral_terras_indigenas.py
"""
Dashboard – Ameaça Geral em Terras Indígenas
Rota Flask: /ameaca_terras_indigenas/
"""

# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------
import io, os, tempfile, requests, dash, unidecode
import pandas as pd
import geopandas as gpd
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc, Output, Input, State

# ----------------------------------------------------------------------
# Helpers de download (dribla HTTP-429 do GitHub Raw)
# ----------------------------------------------------------------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

def _download_tmp(url: str, suffix: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(r.content)
    tmp.close()
    return tmp.name

def load_geojson(url: str):
    try:
        return gpd.read_file(url)
    except Exception:
        try:
            path = _download_tmp(url, ".geojson")
            gdf  = gpd.read_file(path)
            os.unlink(path)
            return gdf
        except Exception:
            return None

def load_df(url: str):
    try:
        return pd.read_parquet(url)
    except Exception:
        try:
            buf = io.BytesIO(requests.get(url, headers=HEADERS, timeout=30).content)
            return pd.read_parquet(buf)
        except Exception:
            return None

# ----------------------------------------------------------------------
# URLs (1ª opção: JSDelivr CDN – sem rate-limit; 2ª fallback: GitHub Raw)
# ----------------------------------------------------------------------
GEOJSON_URLS = [
    "https://cdn.jsdelivr.net/gh/imazon-cgi/ap@main/"
    "dataset/geojson/AMEACA_GERAL_Terra_indigena.geojson",
    "https://raw.githubusercontent.com/imazon-cgi/ap/main/"
    "dataset/geojson/AMEACA_GERAL_Terra_indigena.geojson",
]

PARQUET_URLS = [
    "https://cdn.jsdelivr.net/gh/imazon-cgi/ap@main/"
    "dataset/csv/AMEACA_GERAL_Terra_indigena.parquet",
    "https://github.com/imazon-cgi/ap/raw/refs/heads/main/"
    "dataset/csv/AMEACA_GERAL_Terra_indigena.parquet",
]

# ----------------------------------------------------------------------
# Carrega datasets 
# ----------------------------------------------------------------------
roi = None
for url in GEOJSON_URLS:
    roi = load_geojson(url)
    if roi is not None:
        break
if roi is None:
    raise RuntimeError("Falha ao baixar GeoJSON de Ameaça TI em todas as URLs.")

roi["NOME"] = roi["NOME"].str.upper().apply(
    lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
)
roi = roi.sort_values(by="RANK")

df = None
for url in PARQUET_URLS:
    df = load_df(url)
    if df is not None:
        break
if df is None:
    raise RuntimeError("Falha ao baixar Parquet de Ameaça TI em todas as URLs.")

df["NOME"] = df["NOME"].str.upper().apply(
    lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
)
df = df.sort_values(by="RANK")

# ----------------------------------------------------------------------
# Listas para filtros
# ----------------------------------------------------------------------
state_options = [{"label": s, "value": s} for s in sorted(df["UF"].dropna().unique())]
modalidade_options = [{"label": "Terra Indígena", "value": "Terra Indigena"}]
uso_options = [
    {"label": "Regularizada",  "value": "Regularizada"},
    {"label": "Declarada",     "value": "Declarada"},
    {"label": "Delimitada",    "value": "Delimitada"},
    {"label": "Em Estudo",     "value": "Em Estudo"},
    {"label": "Homologada",    "value": "Homologada"},
    {"label": "Encaminhada RI","value": "Encaminhada RI"},
]

# =============================================================================
# Função pública – registra o dashboard
# =============================================================================
def register_ameaca_terra_indigena_dashboard(flask_server):
    dash_app = dash.Dash(
        __name__,
        server=flask_server,
        url_base_pathname="/ameaca_terras_indigenas/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
        ],
        suppress_callback_exceptions=True,
    )

    # ------------------------------------------------------------------ Layout
    dash_app.layout = dbc.Container(
        [
            html.Meta(name="viewport", content="width=device-width, initial-scale=1"),
            # ---------- filtros ----------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H1(
                                    "Análise de Ameaça de Desmatamento - Amazônia Legal",
                                    className="text-center mb-4",
                                ),
                                dbc.Row(
                                    [
                                        # Modalidade
                                        dbc.Col(html.Label("Modalidade:", className="fw-bold"),
                                                width="auto"),
                                        dbc.Col(dcc.Dropdown(id="modalidade",
                                                             options=modalidade_options,
                                                             value="Terra Indigena",
                                                             clearable=False), width=3),
                                        # Fase
                                        dbc.Col(html.Label("Fase:", className="fw-bold"),
                                                width="auto"),
                                        dbc.Col(dcc.Dropdown(id="fase",
                                                             options=uso_options,
                                                             multi=True,
                                                             placeholder="Selecione a(s) Fase(s)"),
                                                width=3),
                                        # UF
                                        dbc.Col(html.Label("UF:", className="fw-bold"),
                                                width="auto"),
                                        dbc.Col(dcc.Dropdown(id="uf",
                                                             options=state_options,
                                                             multi=True,
                                                             placeholder="Selecione o(s) Estado(s)"),
                                                width=3),
                                        dbc.Col(dbc.Button([html.I(className="fa fa-filter mr-1"),
                                                            "Remover Filtros"],
                                                           id="reset",
                                                           color="primary",
                                                           className="btn-sm"), width="auto"),
                                        dbc.Col(dbc.Button([html.I(className="fa fa-download mr-1"),
                                                            "Baixar CSV"],
                                                           id="open-modal",
                                                           color="secondary",
                                                           className="btn-sm"), width="auto"),
                                    ],
                                    justify="end",
                                    className="mb-3 align-items-center",
                                ),
                            ]
                        ),
                        className="mb-4",
                    )
                )
            ),
            dcc.Download(id="download-csv"),

            # ---------- gráficos ----------
            dbc.Row(
                [
                    dbc.Col(dbc.Card(dcc.Graph(id="bar"),  className="graph-block"),
                            width=12, lg=6),
                    dbc.Col(dbc.Card(dcc.Graph(id="map"),  className="graph-block"),
                            width=12, lg=6),
                ],
                className="mb-4",
            ),
            dcc.Store(id="selecionados", data=[]),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(dcc.Graph(id="pie-fase"),  className="graph-block"),
                            width=12, lg=6),
                    dbc.Col(dbc.Card(dcc.Graph(id="pie-ti"),   className="graph-block"),
                            width=12, lg=6),
                ],
                className="mb-4",
            ),

            # ---------- Tabela ----------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Top 10 Terras Indígenas Mais Afetadas"),
                            dbc.CardBody(dbc.Table(id="top10",
                                                   bordered=True, hover=True,
                                                   responsive=True, striped=True)),
                        ],
                        className="mb-4",
                    )
                )
            ),

            # ---------- Modal CSV ----------
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Terras Indígenas - baixar CSV")),
                    dbc.ModalBody(
                        [
                            dbc.Checklist(options=state_options, id="uf-check", inline=True),
                            html.Hr(),
                            html.Label("Configurações CSV"),
                            dbc.RadioItems(options=[{"label": "Ponto", "value": "."},
                                                    {"label": "Vírgula", "value": ","}],
                                           value=".", id="sep", inline=True),
                            dbc.Checkbox(label="Sem acentuação", id="no-acc", value=False),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Download", id="dwn-btn", color="success"),
                            dbc.Button("Fechar", id="close-modal",  color="danger"),
                        ]
                    ),
                ],
                id="modal",
                is_open=False,
            ),
        ],
        fluid=True,
    )

    # ------------------------------------------------------------------ Callbacks
    @dash_app.callback(
        [
            Output("bar", "figure"),
            Output("map", "figure"),
            Output("pie-fase", "figure"),
            Output("pie-ti", "figure"),
            Output("selecionados", "data"),
            Output("top10", "children"),
        ],
        [
            Input("modalidade", "value"),
            Input("fase", "value"),
            Input("uf", "value"),
            Input("reset", "n_clicks"),
            Input("bar", "clickData"),
            Input("map", "clickData"),
        ],
        State("selecionados", "data"),
    )
    def atualizar(modalidade, fase, uf, reset, bar_click, map_click, selecionados):
        if reset:
            selecionados = []

        for click_data in (bar_click, map_click):
            if click_data:
                nome = click_data["points"][0].get("y") or click_data["points"][0].get("location")
                if nome:
                    selecionados = selecionados or []
                    selecionados = ([n for n in selecionados if n != nome]
                                    if nome in selecionados else selecionados + [nome])

        df_f = df[df["MODALIDADE"] == modalidade]
        if fase:
            fase = fase if isinstance(fase, list) else [fase]
            df_f = df_f[df_f["FASE"].isin(fase)]
        if uf:
            df_f = df_f[df_f["UF"].isin(uf)]
        if selecionados:
            df_f = df_f[df_f["NOME"].isin(selecionados)]

        top10 = df_f.nlargest(10, "DESMATAM_1")

        # ---------- tabela ----------
        thead = html.Thead(html.Tr([
            html.Th("Nome"), html.Th("Focos de Calor"), html.Th("Nº CAR"),
            html.Th("Área CAR"), html.Th("Estradas Não Oficiais")
        ]))
        tbody = html.Tbody([
            html.Tr([
                html.Td(r["NOME"]), html.Td(r["FOCOS DE C"]), html.Td(r["N DE CAR"]),
                html.Td(f"{r['CAR']:.2f} km²"), html.Td(f"{r['ESTRADAS N']:.2f} km")
            ]) for _, r in top10.iterrows()
        ])
        tabela = dbc.Table([thead, tbody], bordered=True,
                           hover=True, responsive=True, striped=True)

        # ---------- barras ----------
        bar = go.Figure(go.Bar(
            y=top10["NOME"], x=top10["DESMATAM_1"], orientation="h",
            marker_color=["green" if n in (selecionados or []) else "DarkSeaGreen"
                          for n in top10["NOME"]],
            text=[f"{v:.2f} km²" for v in top10["DESMATAM_1"]],
            textposition="auto",
        ))
        bar.update_yaxes(autorange="reversed")
        bar.update_layout(
            xaxis_title="Área (km²)", yaxis_title="Terras Indígenas", bargap=0.1,
            font=dict(size=10),
            title=dict(text="Top 10 Terras Indígenas por Desmatamento",
                       x=0.5, xanchor="center"),
        )

        # ---------- mapa ----------
        mapa = px.choropleth_mapbox(
            top10, geojson=roi, color="DESMATAM_1",
            locations="NOME", featureidkey="properties.NOME",
            mapbox_style="carto-positron",
            center={"lat": -14, "lon": -55},
            color_continuous_scale="YlOrRd", zoom=4,
        )
        mapa.update_layout(
            title=dict(text="Mapa de Ameaça de Desmatamento (km²)",
                       x=0.5, xanchor="center", font={"size": 14}),
            margin=dict(r=0, t=50, l=0, b=0),
            mapbox=dict(zoom=3, center={"lat": -14, "lon": -55},
                        style="open-street-map"),
        )

        # ---------- pizzas ----------
        cores = px.colors.sequential.YlOrRd
        pie_fase = px.pie(top10, values="DESMATAM_1", names="UF", color="FASE",
                          title="Ameaça por Estado/Fase")
        pie_fase.update_traces(textinfo="percent+label", marker=dict(colors=cores))

        pie_ti = px.pie(top10, values="DESMATAM_1", names="NOME", color="FASE",
                        title="Ameaça por Terra Indígena")
        pie_ti.update_traces(textinfo="percent+label", marker=dict(colors=cores))

        return bar, mapa, pie_fase, pie_ti, selecionados, tabela

    # ---------------- modal toggle ----------------
    @dash_app.callback(
        Output("modal", "is_open"),
        [Input("open-modal", "n_clicks"), Input("close-modal", "n_clicks")],
        State("modal", "is_open"),
    )
    def modal_toggle(n_open, n_close, opened):
        return not opened if n_open or n_close else opened

    # ---------------- download CSV ----------------
    @dash_app.callback(
        Output("download-csv", "data"),
        Input("dwn-btn", "n_clicks"),
        State("sep", "value"),
        State("no-acc", "value"),
        prevent_initial_call=True,
    )
    def download(n, sep, no_acc):
        if not n:
            return dash.no_update
        out = df.copy()
        if no_acc:
            out = out.applymap(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
        return dcc.send_data_frame(out.to_csv,
                                   "ameaca_terras_indigenas.csv",
                                   index=False, sep=sep,
                                   encoding="utf-8-sig")

    # ------------------------------------------------
    return dash_app
