from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
from server import app
import pandas as pd
import base64
from io import StringIO, BytesIO


class Sidebar:

    def __init__(self, conn):
        self.conn = conn

    def layout(self):
        return dbc.Col(
            [
                html.H2("Music", className="display-4"),
                html.Hr(),
                html.P("Collection Mananger", className="lead"),
                html.Hr(),
                dbc.Form(
                    [
                        html.Div(id="drop"),
                        html.Hr(),
                        html.Div(id="media_totals"),
                        html.Hr(),
                        dbc.Row(
                            [
                                dcc.Download(id="download_xlsx"),
                                html.Div(id="download_alert"),
                                html.Div(id="upload_alert"),
                                dbc.Col(
                                    dbc.Button(
                                        " Download XLSX",
                                        color="success",
                                        className="bi bi-download",
                                        id="download_xlsx_btn"
                                    ),
                                    width=12
                                ),
                                dbc.Col(
                                    dcc.Upload(
                                        dbc.Button(
                                            " Upload XLSX",
                                            color="info",
                                            className="bi bi-upload",
                                        ),
                                        id="upload_xlsx"
                                    ),
                                    width=12
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        " Adicionar",
                                        color="secondary",
                                        className="bi bi-plus-circle",
                                        id="insert_btn"
                                    ), width=12
                                ),
                            ],
                            className="g-2",
                        ),
                    ]
                )
            ],
            className="custom-sidebar"
        )

    def callbacks(self):
        @app.callback(
            Output("media_totals", 'children'),
            Input('df', 'data')
        )
        def render(value):
            df = self.conn.qyery("CD")

            table_header = [
                html.Thead(html.Tr([html.Th("MEDIA"), html.Th("QUANTIDADE")]))
            ]
            rows = [
                    html.Tr([html.Td(i), html.Td(len(df.query(f"MEDIA=='{i}'").index))])
                    for i in sorted(df['MEDIA'].unique())
                ]
            table_body = [html.Tbody(rows,className="g-2")]
            return dbc.Table(table_header + table_body, bordered=True)

        @ app.callback(
            Output("drop", 'children'),
            Input('filter_contents', 'data'),
            prevent_initial_call=True
        )
        def toggle_modal(_filter):
            df = self.conn.qyery("CD")
            if _filter != {}:
                _query = ""
                for key, value in _filter.items():
                    _query += f"{key} == '{value}' & "

                _query = _query[:_query.rfind("&")]
                dff = df.query(_query)
            else:
                dff = df
            return [dbc.Row(
                [
                    dbc.Label(" Artista", width=3,
                              className="bi bi-person"),
                    dbc.Col(
                        dcc.Dropdown(
                            id={
                                'type': 'filter-dropdown',
                                'index': 'ARTIST'
                            },
                            options=[{'label': str(i), 'value': str(i)}
                                     for i in sorted(dff['ARTIST'].unique())],
                            value=_filter["ARTIST"] if "ARTIST" in _filter else None,
                            optionHeight=40,
                            className="me-3"
                        ), width=9
                    ),
                ],
                className="g-2",
            ),
                html.Hr(),
                dbc.Row(
                [
                    dbc.Label(" Media", width=3, className="bi bi-disc"),
                    dbc.Col(
                        dcc.Dropdown(
                            id={
                                'type': 'filter-dropdown',
                                'index': 'MEDIA'
                            },
                            options=[{'label': str(i), 'value': str(i)}
                                     for i in sorted(dff['MEDIA'].unique())],
                            value=_filter["MEDIA"] if "MEDIA" in _filter else None,
                            className="me-3"
                        ), width=9
                    ),
                ],
                className="g-2",
            ),
                html.Hr(),
                dbc.Row(
                [
                    dbc.Label(" Origem", width=3, className="bi bi-house"),
                    dbc.Col(
                        dcc.Dropdown(
                            id={
                                'type': 'filter-dropdown',
                                'index': 'ORIGIN'
                            },
                            options=[{'label': str(i), 'value': str(i)}
                                     for i in sorted(dff['ORIGIN'].dropna().unique())],
                            value=_filter["ORIGIN"] if "ORIGIN" in _filter else None,
                            className="me-3"
                        ), width=9
                    ),
                ],
                className="g-2",
            )]

        @ app.callback(
            Output("upload_alert", "children"),
            Input('upload_xlsx', 'contents'),
            State("upload_xlsx", "filename"),
            prevent_initial_call=True,
        )
        def on_button_click(data, filename):
            content_type, content_string = data.split(',')
            decoded = base64.b64decode(content_string)

            if filename is None:
                raise ""
            else:
                if 'csv' in filename:
                    df = pd.read_csv(
                        StringIO(decoded.decode('utf-8')), sep=";")
                elif 'xls' in filename:
                    df = pd.read_excel(
                        BytesIO(decoded), dtype={'BARCODE': str})
                else:
                    return dbc.Alert("FORMATO INVALIDO",
                                     is_open=True,  duration=4000, color="danger")

                COLUMNS = ('RELEASE_YEAR', 'ARTIST', 'TITLE', 'MEDIA', 'PURCHASE', 'ORIGIN',
                           'EDITION_YEAR', 'IFPI_MASTERING', 'IFPI_MOULD', 'BARCODE', 'MATRIZ', 'LOTE', 'ANO_AQUISICAO', 'RECENTE', 'LISTA')

                for col in df.select_dtypes(include=['datetime64']).columns.tolist():
                    df[col] = df[col].astype(str)

                df.replace({pd.NaT: None, np.nan: None, "NaT": None,
                           "": None, "None": None}, inplace=True)

                df = df.to_dict("records")

                newList = []

                for d in df:
                    newDf = {}
                    for key, value in d.items():
                        if key in COLUMNS:
                            newDf[key] = value
                    newList.append(newDf)

                self.conn.drop("CD")
                self.conn.insert_many("CD", newList)

                return dbc.Alert("SALVO",
                                 is_open=True,  duration=4000)

        @ app.callback(
            Output("download_xlsx", "data"),
            Input("download_xlsx_btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def on_button_click(n):
            if n is None:
                raise ""
            else:
                df = self.conn.qyery("CD")
                df.drop('_id', axis=1, inplace=True)
                return dcc.send_data_frame(df.to_excel, "collection.xlsx")
