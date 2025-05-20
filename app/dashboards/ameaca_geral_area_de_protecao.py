# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import io
import dash
import unidecode
import pandas as pd
import geopandas as gpd
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc, Output, Input, State

# ---------------------------------------------------------------------------
# Funções utilitárias e carregamento de dados 
# ---------------------------------------------------------------------------
def load_geojson(url: str):
    try:
        return gpd.read_file(url)
    except Exception as e:
        print(f"Erro ao carregar {url}: {e}")
        return None


def load_df(url: str):
    return pd.read_parquet(url)


roi = load_geojson(
    "https://raw.githubusercontent.com/imazon-cgi/ap/main/dataset/geojson/AMEACA_GERAL_Area_de_Protecao.geojson"
)
roi["NOME"] = roi["NOME"].str.upper().apply(
    lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
)
roi = roi.sort_values(by="RANK")

df = load_df(
    "https://github.com/imazon-cgi/ap/raw/refs/heads/main/dataset/csv/AMEACA_GERAL_Area_de_Protecao.parquet"
)
df["NOME"] = df["NOME"].str.upper().apply(
    lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
)
df = df.sort_values(by="RANK")

# ---------------------------------------------------------------------------
# Opções fixas de filtro
# ---------------------------------------------------------------------------
state_options = [{"label": s, "value": s} for s in sorted(df["UF"].dropna().unique())]

modalidade_options = [
    {"label": "UC Federal", "value": "UC Federal"},
    {"label": "UC Estadual", "value": "UC Estadual"},
]

uso_options = [
    {"label": "Uso Sustentável", "value": "Uso Sustentavel"},
    {"label": "Proteção Integral", "value": "Protecao Integral"},
]

# =============================================================================
# Função pública: registra o dashboard no servidor Flask
# =============================================================================
def register_area_de_protecao_dashboard(flask_server):
    dash_app = dash.Dash(
        __name__,
        server=flask_server,
        url_base_pathname="/area_de_protecao/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
        ],
        suppress_callback_exceptions=True,
    )

    # ------------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------------
    dash_app.layout = dbc.Container(
        [
            html.Meta(name="viewport", content="width=device-width, initial-scale=1"),
            # ---------- Título + filtros ----------
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
                                        dbc.Col(
                                            html.Label("Modalidade:", className="fw-bold"),
                                            width="auto",
                                            className="align-self-center",
                                        ),
                                        dbc.Col(
                                            dcc.Dropdown(
                                                id="modalidade-dropdown",
                                                options=modalidade_options,
                                                multi=True,
                                                placeholder="Selecione a modalidade",
                                            ),
                                            width=3,
                                        ),
                                        dbc.Col(
                                            html.Label("Uso:", className="fw-bold"),
                                            width="auto",
                                            className="align-self-center",
                                        ),
                                        dbc.Col(
                                            dcc.Dropdown(
                                                id="uso-dropdown",
                                                options=uso_options,
                                                multi=True,
                                                placeholder="Selecione o uso",
                                            ),
                                            width=3,
                                        ),
                                        dbc.Col(
                                            html.Label("UF:", className="fw-bold"),
                                            width="auto",
                                            className="align-self-center",
                                        ),
                                        dbc.Col(
                                            dcc.Dropdown(
                                                id="state-dropdown",
                                                options=state_options,
                                                multi=True,
                                                placeholder="Selecione o(s) Estado(s)",
                                            ),
                                            width=3,
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                [html.I(className="fa fa-filter mr-1"), "Remover Filtros"],
                                                id="reset-button",
                                                color="primary",
                                                className="btn-sm custom-button",
                                            ),
                                            width="auto",
                                            className="d-flex justify-content-end",
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                [html.I(className="fa fa-download mr-1"), "Baixar CSV"],
                                                id="open-modal-button",
                                                color="secondary",
                                                className="btn-sm custom-button",
                                            ),
                                            width="auto",
                                            className="d-flex justify-content-end",
                                        ),
                                    ],
                                    justify="end",
                                    className="mb-3 align-items-center",
                                ),
                            ]
                        ),
                        className="mb-4 title-card",
                    )
                )
            ),
            dcc.Download(id="download-dataframe-csv"),
            # ---------- Gráficos ----------
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="bar-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="map-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
            ),
            dcc.Store(id="selected-states", data=[]),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="pie-uso-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="pie-unid-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
            ),
            # ---------- Top-10 tabela ----------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Top 10 Áreas Protegidas Mais Afetadas"),
                            dbc.CardBody(
                                dbc.Table(
                                    id="top-10-table",
                                    bordered=True,
                                    hover=True,
                                    responsive=True,
                                    striped=True,
                                )
                            ),
                        ],
                        className="mb-4",
                    )
                )
            ),
            # ---------- Modal download ----------
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            "Escolha as Áreas de Proteção Ambiental da Amazônia Legal"
                        )
                    ),
                    dbc.ModalBody(
                        [
                            dbc.Checklist(
                                options=state_options,
                                id="state-checklist",
                                inline=True,
                            ),
                            html.Hr(),
                            html.Div(
                                [
                                    html.Label("Configurações para gerar o CSV"),
                                    dbc.RadioItems(
                                        options=[
                                            {"label": "Ponto", "value": "."},
                                            {"label": "Vírgula", "value": ","},
                                        ],
                                        value=".",
                                        id="decimal-separator",
                                        inline=True,
                                        className="mb-2",
                                    ),
                                    dbc.Checkbox(
                                        label="Sem acentuação",
                                        id="remove-accents",
                                        value=False,
                                    ),
                                ]
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Download",
                                id="download-button",
                                className="mr-2",
                                color="success",
                            ),
                            dbc.Button("Fechar", id="close-modal-button", color="danger"),
                        ]
                    ),
                ],
                id="modal",
                is_open=False,
            ),
        ],
        fluid=True,
    )

    # ------------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------------
    @dash_app.callback(
        [
            Output("bar-graph", "figure"),
            Output("map-graph", "figure"),
            Output("pie-uso-graph", "figure"),
            Output("pie-unid-graph", "figure"),
            Output("selected-states", "data"),
            Output("top-10-table", "children"),
        ],
        [
            Input("modalidade-dropdown", "value"),
            Input("uso-dropdown", "value"),
            Input("state-dropdown", "value"),
            Input("reset-button", "n_clicks"),
            Input("bar-graph", "clickData"),
            Input("map-graph", "clickData"),
        ],
        State("selected-states", "data"),
    )
    def update_graphs(
        modalidade,
        uso,
        states,
        reset_clicks,
        bar_click_data,
        map_click_data,
        selected_states,
    ):
        # ---------- Seleções ----------
        if reset_clicks:
            selected_states = []

        if bar_click_data:
            nome = bar_click_data["points"][0]["y"]
            selected_states = (
                [n for n in selected_states if n != nome]
                if nome in selected_states
                else selected_states + [nome]
            )

        if map_click_data:
            nome = map_click_data["points"][0]["location"]
            selected_states = (
                [n for n in selected_states if n != nome]
                if nome in selected_states
                else selected_states + [nome]
            )

        filtered_df = df.copy()

        if modalidade:
            modalidade = modalidade if isinstance(modalidade, list) else [modalidade]
            filtered_df = filtered_df[filtered_df["MODALIDADE"].isin(modalidade)]

        if uso:
            uso = uso if isinstance(uso, list) else [uso]
            filtered_df = filtered_df[filtered_df["USO"].isin(uso)]

        if states:
            filtered_df = filtered_df[filtered_df["UF"].isin(states)]

        if selected_states:
            filtered_df = filtered_df[filtered_df["NOME"].isin(selected_states)]

        top_10 = filtered_df.nlargest(10, "DESMATAM_1")

        # ---------- Tabela ----------
        header = html.Thead(
            html.Tr(
                [
                    html.Th("Nome"),
                    html.Th("Focos de Calor"),
                    html.Th("Número de CAR"),
                    html.Th("Área de CAR"),
                    html.Th("Estradas Não Oficiais"),
                ]
            )
        )
        body = [
            html.Tr(
                [
                    html.Td(r["NOME"]),
                    html.Td(r["FOCOS DE C"]),
                    html.Td(r["N DE CAR"]),
                    html.Td(f"{r['CAR']:.2f} km²"),
                    html.Td(f"{r['ESTRADAS N']:.2f} km"),
                ]
            )
            for _, r in top_10.iterrows()
        ]
        table = dbc.Table(
            [header, html.Tbody(body)],
            bordered=True,
            hover=True,
            responsive=True,
            striped=True,
        )

        # ---------- Gráfico de barras ----------
        bar_fig = go.Figure(
            go.Bar(
                y=top_10["NOME"],
                x=top_10["DESMATAM_1"],
                orientation="h",
                marker_color=[
                    "green" if n in selected_states else "DarkSeaGreen" for n in top_10["NOME"]
                ],
                text=[f"{v:.2f} km²" for v in top_10["DESMATAM_1"]],
                textposition="auto",
            )
        )
        bar_fig.update_yaxes(autorange="reversed")
        bar_fig.update_layout(
            xaxis_title="Área (km²)",
            yaxis_title="Área de Proteção Ambiental",
            bargap=0.1,
            font=dict(size=10),
            title=dict(
                text="Top 10 Áreas de Proteção Ambiental por Desmatamento",
                x=0.5,
                xanchor="center",
            ),
        )

        # ---------- Mapa ----------
        map_fig = px.choropleth_mapbox(
            top_10,
            geojson=roi,
            color="DESMATAM_1",
            locations="NOME",
            featureidkey="properties.NOME",
            mapbox_style="carto-positron",
            center={"lat": -14, "lon": -55},
            color_continuous_scale="YlOrRd",
            zoom=4,
        )
        map_fig.update_layout(
            title=dict(
                text="Mapa de Ameaça de Desmatamento (km²)",
                x=0.5,
                xanchor="center",
                font={"size": 14},
            ),
            margin={"r": 0, "t": 50, "l": 0, "b": 0},
            mapbox={"zoom": 3, "center": {"lat": -14, "lon": -55}},
        )

        # ---------- Pizzas ----------
        pie_colors = px.colors.sequential.YlOrRd
        pie_uso_fig = px.pie(
            top_10,
            values="DESMATAM_1",
            names="UF",
            color="MODALIDADE",
            title="Ameaça Desmatamento por Estado de Uso e Categoria",
        )
        pie_uso_fig.update_traces(textinfo="percent+label", marker=dict(colors=pie_colors))

        pie_unid_fig = px.pie(
            top_10,
            values="DESMATAM_1",
            names="NOME",
            color="UF",
            title="Ameaça Desmatamento por Área de Proteção Ambiental",
        )
        pie_unid_fig.update_traces(
            textinfo="none",
            hoverinfo="label+value+percent",
            marker=dict(colors=pie_colors),
        )

        return bar_fig, map_fig, pie_uso_fig, pie_unid_fig, selected_states, table

    # ------------------------------------------------------------------------
    # Modal on/off
    # ------------------------------------------------------------------------
    @dash_app.callback(
        Output("modal", "is_open"),
        [Input("open-modal-button", "n_clicks"), Input("close-modal-button", "n_clicks")],
        State("modal", "is_open"),
    )
    def toggle_modal(n_open, n_close, is_open):
        return not is_open if n_open or n_close else is_open

    # ------------------------------------------------------------------------
    # Download CSV
    # ------------------------------------------------------------------------
    @dash_app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State("decimal-separator", "value"),
        State("remove-accents", "value"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, decimal_sep, remove_accents):
        if not n_clicks:
            return dash.no_update

        out_df = df.copy()
        if remove_accents:
            out_df = out_df.applymap(
                lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
            )

        return dcc.send_data_frame(
            out_df.to_csv,
            "ameaça_area_protecao.csv",
            index=False,
            sep=decimal_sep,
            encoding="utf-8-sig",
        )

    # --------- devolve a instância Dash caso precise ----------
    return dash_app
