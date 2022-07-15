from dash import html, dcc, Input, Output, State, callback_context, ALL
import dash_bootstrap_components as dbc
import plotly.express as px
from server import app
from json import loads
from os import environ
import pandas as pd
import requests


class Content:

    def __init__(self, conn):
        self.conn = conn
        self.MAX_INDEX = 3
        self.discogs_url = "https://api.discogs.com/database/search"

    def discogs_get_url(self, row):
        params = {
            "token": environ["DISCOGS_TOKEN"],
            "query": row["ARTIST"].lower() if not None else "",
            "release_title": row["TITLE"].lower() if row["TITLE"].lower() is not None else "",
            "barcode": str(row["BARCODE"]) if row["BARCODE"] is not None and row["BARCODE"] != 'None' else "",
            "country": row["ORIGIN"].lower() if not None else ""
        }
        resp = requests.get(self.discogs_url, params=params)
        if resp.status_code == 200:
            result = resp.json()["results"]
            if len(result) == 0:
                params.pop("country")
                resp = requests.get(self.discogs_url, params=params)

            if len(result) > 0:
                img = result[0]['cover_image']
                return dbc.Row([
                    dbc.Col([
                        dbc.Row(html.Img(
                            src=img
                        ), justify="center")
                    ], width=4, align="center"),
                    dbc.Col([
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(
                                    [
                                        dbc.ListGroup([
                                            dbc.ListGroupItem(dbc.CardLink(
                                                f'DISCOGS - {r["master_id"]}',
                                                href=f"https://www.discogs.com{r['uri']}",
                                                className="bi bi-body-text",
                                                external_link=True,
                                                target="_blank"
                                            )) for r in result
                                        ]),
                                    ],
                                    title=f"ARTIGOS ENCONTRADOS: {len(result)}",
                                ),
                            ], start_collapsed=True,
                        ),
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(
                                    [
                                        dbc.ListGroup(
                                            self.get_discog_tacks(
                                                result[0]['id'])
                                        )
                                    ],
                                    title="Lista de Faixas",
                                ),
                            ], start_collapsed=True,
                        ),

                    ], width=8)

                ])
            else:
                return html.Div("Nao encontrado no Discogs")
        else:
            return html.Div(f"Erro de Conexao com Discogs - {resp.status_code}")

    def get_discog_tacks(self, _id):
        resp = requests.get(f"https://api.discogs.com/releases/{_id}")
        if resp.status_code == 200:
            return [
                dbc.ListGroupItem(
                    f'{t["position"]} - {t["title"]}'
                ) for t in resp.json()["tracklist"]
            ]
        else:
            return html.Div(f"{resp.status_code}")

    def layout(self):
        return html.Div([
            dbc.Tabs(
                [
                    dbc.Tab([
                        dcc.Loading([
                            html.Div(id='disco')
                        ]
                        ),
                    ], label="Principal"
                    ),
                    dbc.Tab(dbc.Col(
                       dcc.Loading( dcc.Graph(
                            id='total_year_graph',responsive=True
                        )), width=12
                    ), label="Ano de Lançamento"),
                    dbc.Tab(dbc.Col(
                        dcc.Loading(dcc.Graph(
                            id='total_purchase_graph',responsive=True
                        )), width=12
                    ), label="Ano de Aquisição")
                ]
            )
        ], className='custom-content'
        )

    def callbacks(self):
        @app.callback(
            Output("total_year_graph", 'figure'),
            Output("total_purchase_graph", 'figure'),
            Input('df', 'data'),
            Input('filter_contents', 'data'),
        )
        def render(_, _filter):
            if _filter:
                _query = ""
                for key, value in _filter.items():
                    _query += f"{key} == '{value}' & "

                _query = _query[:_query.rfind("&")]
                df = self.conn.qyery("CD").query(_query)
            else:
                df = self.conn.qyery("CD")

            df['RELEASE_YEAR'] = pd.to_numeric(df['RELEASE_YEAR'], errors='coerce')    

            total_year = px.bar(df.groupby(['RELEASE_YEAR'])['RELEASE_YEAR'].count(),
                                labels={
                "index": "Ano",
                "value": "Total"
            },
                title="Ano de Lançamento",
                text_auto=True,
                height=600
            )
            total_year.update_layout(showlegend=False, hovermode="x unified")
            total_year.update_traces(
                hovertemplate='Total: %{y}<extra></extra>')
            try:
                df['PURCHASE'] = pd.to_datetime(df['PURCHASE'], errors='coerce')
                count = df.groupby(df['PURCHASE'].dt.year)['PURCHASE'].count()
            except:
                count = None
            total_purchase = px.bar(
                count,
                labels={
                    "index": "Ano",
                    "value": "Total"
                },
                title="Ano de Aquisição",
                text_auto=True,
                height=600
            ).update_layout(showlegend=False)
            return total_year, total_purchase

        @app.callback(
            Output('disco', 'children'),
            Output('filter_contents', 'data'),
            Input({'type': 'filter-dropdown', 'index': ALL}, 'value'),
            Input('df', 'data'),
            Input('url', 'pathname'),
            State('filter_contents', 'data'),
            prevent_initial_call=True
            )
        def update_output(value, _,url, _filter):
            df = self.conn.qyery("CD")
            cxt = callback_context.triggered
            if not any(value):
                if cxt[0]['value'] == None:
                    try:
                        _filter.pop(
                            loads(cxt[0]['prop_id'].split('.')[0])["index"]
                        )
                    except:
                        pass
                welcome = dbc.Alert(
                        [
                            html.H4("Bem Vindo!", className="alert-heading"),
                            html.P(
                                "Utilize a barra de navegação ao lado para realizar a pesquisa"
                            ),
                        ], style={"margin-top":"1rem"}
                    )
                return welcome, _filter
            else:
                if cxt[0]['prop_id'].split('.')[0] not in ["df"]:
                    _filter_index = loads(
                        cxt[0]['prop_id'].split('.')[0])["index"]
                    _filter[_filter_index] = cxt[0]["value"]
                    _filter = dict((k, v)
                                   for k, v in _filter.items() if v is not None)
                _query = ""
                for key, value in _filter.items():
                    _query += f"{key} == '{value}' & "

                _query = _query[:_query.rfind("&")]

                if len( df.query(_query)) > 30:
                    warning = dbc.Alert(
                        [
                            html.H4("Acima de 30 unidades encontradas", className="alert-heading"),
                            html.P(
                                "Utilize o filtro de forma mais granular ou Realize o download da Planilha"
                            ),
                        ], style={"margin-top":"1rem"}
                    )
                    return warning, _filter
                df = df.query(_query).groupby('ARTIST', as_index=False)
            accord = dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Accordion([
                        dbc.AccordionItem([
                            html.H4(f' {row["TITLE"]}',
                                    className="card-title bi bi-book"),
                            html.H5(f' {row["ARTIST"]}',
                                    className="card-title bi bi-person"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.ListGroup(
                                            [
                                                dbc.ListGroupItem(
                                                    f' ANO DE LANÇAMENTO: {row["RELEASE_YEAR"] if row["RELEASE_YEAR"] is not None else ""}',
                                                    className="bi bi-calendar-event"
                                                ),
                                                dbc.ListGroupItem(
                                                    f' ANO DA EDIÇÃO: {int(row["EDITION_YEAR"]) if row["EDITION_YEAR"] is not None else ""}',
                                                    className="bi bi-calendar-event"
                                                ),
                                                dbc.ListGroupItem(
                                                    f' MEDIA: {row["MEDIA"] if row["MEDIA"] is not None else ""}', className="bi bi-vinyl"
                                                ),
                                                dbc.ListGroupItem(
                                                    f' AQUISIÇÃO: {row["PURCHASE"].strftime("%d/%m/%Y") if row["PURCHASE"] is not None else "" }',
                                                    className="bi bi-cart3"
                                                )
                                            ]
                                        ), width=4),
                                
                                    dbc.Col(
                                        dbc.ListGroup([
                                            dbc.ListGroupItem(
                                                f' ORIGEM: {row["ORIGIN"]  if row["ORIGIN"] is not None else "" }',
                                                className="bi bi-house"
                                            ),
                                            dbc.ListGroupItem(
                                                f' IFPI MASTERING: {row["IFPI_MASTERING"]  if row["IFPI_MASTERING"] is not None else "" }',
                                                className="bi bi-body-text"
                                            ),
                                            dbc.ListGroupItem(
                                                f' IFPI MOULD: {row["IFPI_MOULD"]  if row["IFPI_MOULD"] is not None else "" }',
                                                className="bi bi-body-text"
                                            )
                                        ]), width=4),

                                    dbc.Col(
                                        dbc.ListGroup([
                                            dbc.ListGroupItem(
                                                f' CÓDIGO DE BARRAS: {row["BARCODE"] if row["BARCODE"] is not None else "" }',
                                                className="bi bi-body-text"
                                            ),
                                            dbc.ListGroupItem(
                                                f' MATRIZ: {row["MATRIZ"]  if row["MATRIZ"] is not None else "" }',
                                                className="bi bi-body-text"
                                            ),
                                            dbc.ListGroupItem(
                                                f' LOTE: {row["LOTE"] if row["LOTE"] is not None else "" }',
                                                className="bi bi-body-text"
                                            )
                                        ]), width=4
                                    )
                                ],
                                align="start",
                            ),
                            dbc.Row(
                                dbc.Col(
                                    [dbc.Button(
                                        html.I(className="bi bi-pencil-fill"),
                                        color="warning",
                                        outline=True,
                                        className="me-1",
                                        id={
                                            'type': 'edit_button',
                                            'index': f"{row['_id']}"
                                        },
                                    ), dbc.Button(
                                        html.I(className="bi bi-trash2-fill"),
                                        color="danger",
                                        outline=True,
                                        className="me-1",
                                        id={
                                            'type': 'delete_button',
                                            'index': f"{row['_id']}"
                                        },
                                    )], width=2),
                                justify="end",
                            ),
                            html.Hr(),
                            self.discogs_get_url(row)

                        ], title=f'{int(row["RELEASE_YEAR"]) if row["RELEASE_YEAR"] is not None else ""} - {row["TITLE"]}')
                        for row in group.sort_values("RELEASE_YEAR").to_dict('records')], start_collapsed=True)
                ], title=name,
                ) for name, group in df], start_collapsed=True)
            return accord, _filter
