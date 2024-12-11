import pandas as pd
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import webbrowser
from threading import Timer
df = pd.read_csv('netflix_titles.csv')



# Preprocesar la columna 'country' para dividir países
df['country'] = df['country'].str.split(', ')  # Dividir por comas
df = df.explode('country')  # Expandir cada país en filas individuales
# Eliminar actores duplicados para cada título
def process_cast(cast):
    if not pd.isna(cast):
        # Dividir por comas, eliminar espacios y hacer únicos
        unique_actors = sorted(set(actor.strip() for actor in cast.split(',')))
        return ', '.join(unique_actors)
    return cast

df['unique_cast'] = df['cast'].apply(process_cast)

# Consolidar los títulos para eliminar duplicados
df = df.drop_duplicates(subset=['title']).reset_index(drop=True)
# Crear un DataFrame de agregados por país
country_counts = df.groupby('country').size().reset_index(name='count')

# Crear opciones únicas para el Dropdown de países
unique_countries = df['country'].dropna().unique()
country_options = [{'label': country, 'value': country} for country in sorted(unique_countries)]

# Crear la aplicación Dash con Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout de la aplicación
app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                dcc.Graph(
                    id='world-map',
                    config={'scrollZoom': False},
                    style={'height': '70vh'}
                ),
                width=12
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4("Seleccionar País", className="card-title"),
                            dcc.Dropdown(
                                id='country-dropdown',
                                options=country_options,
                                placeholder='Selecciona un país'
                            ),
                            html.Div(id='country-stats', style={'marginTop': '20px'}),
                        ]
                    ),
                    className="mb-3",
                ),
                width=12
            )
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Seleccionar Tipo", className="card-title"),
                                dcc.RadioItems(
                                    id='type-filter',
                                    options=[
                                        {'label': 'Películas', 'value': 'Movie'},
                                        {'label': 'TV Shows', 'value': 'TV Show'}
                                    ],
                                    value='Movie',
                                    labelStyle={'display': 'block'}
                                ),
                                html.Hr(),
                                dcc.Dropdown(
                                    id='titles-dropdown',
                                    placeholder='Selecciona un título',
                                    style={'marginTop': '10px'}
                                ),
                            ]
                        ),
                        className="mb-3",
                    ),
                    width=6
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Detalles del Título", className="card-title"),
                                html.Div(id='title-details', style={'marginTop': '20px'}),
                                html.Hr(),
                                html.H4("Actores", className="card-title"),
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button("Anterior", id='prev-actors', n_clicks=0),
                                        dbc.Button("Siguiente", id='next-actors', n_clicks=0),
                                    ],
                                    className="d-flex justify-content-center mb-3"
                                ),
                                html.Ul(id='actors-list', className='list-group'),
                            ]
                        ),
                        className="mb-3",
                    ),
                    width=6
                )
            ]
        )
    ],
    fluid=True
)

# Variables de paginación globales
actors_per_page = 10

# Callback para actualizar el mapa mundial
@app.callback(
    Output('world-map', 'figure'),
    Input('country-dropdown', 'value')
)
def update_map(selected_country):
    # Crear el mapa mundial con diseño mejorado
    fig = px.choropleth(
        country_counts,
        locations='country',
        locationmode='country names',
        color='count',
        hover_name='country',
        title='Distribución de Títulos en Netflix por País',
        color_continuous_scale='Rainbow',  # Paleta de colores más atractiva
        range_color=(0, 850)  # Ajustar rango de la leyenda
    )

    # Mejorar diseño del mapa
    fig.update_layout(
        geo=dict(
            showframe=False,  # Ocultar bordes del marco
            showcoastlines=False,  # Ocultar líneas de costa
            projection_type='equirectangular',  # Proyección limpia
            bgcolor='rgba(255, 255, 255, 0)'  # Fondo transparente
        ),
        title=dict(
            text='Distribución de Títulos en Netflix por País',
            font=dict(size=20, family='Arial'),
            x=0.5  # Centrar título
        ),
        coloraxis_colorbar=dict(
            thickness=15,  # Grosor de la barra de color
            len=0.6,  # Longitud de la barra de color
            title=dict(text='Número de Títulos', side='right', font=dict(size=12))
        )
    )
    return fig
# Callback para sincronizar mapa y Dropdown
@app.callback(
    Output('country-dropdown', 'value'),
    Input('world-map', 'clickData'),
    State('country-dropdown', 'value')
)
def sync_dropdown_with_map(click_data, dropdown_value):
    if click_data:
        country = click_data['points'][0]['location']
        return country
    return dropdown_value
# Callback para mostrar estadísticas del país
@app.callback(
    Output('country-stats', 'children'),
    Input('country-dropdown', 'value')
)
def update_country_stats(selected_country):
    if not selected_country:
        return html.Div("Selecciona un país para ver las estadísticas.")

    # Filtrar los datos por el país seleccionado
    filtered_data = df[df['country'] == selected_country]
    movies_count = len(filtered_data[filtered_data['type'] == 'Movie'])
    tv_shows_count = len(filtered_data[filtered_data['type'] == 'TV Show'])

    return html.Div(
        [
            html.P(f"Películas: {movies_count}"),
            html.P(f"TV Shows: {tv_shows_count}")
        ]
    )

# Callback para actualizar los títulos según el tipo seleccionado
@app.callback(
    Output('titles-dropdown', 'options'),
    [Input('type-filter', 'value'),
     Input('country-dropdown', 'value')]
)
def update_titles(type_filter, selected_country):
    if not selected_country:
        return []

    # Filtrar los datos por país y tipo
    filtered_data = df[(df['country'] == selected_country) & (df['type'] == type_filter)]
    
    # Validar si hay datos disponibles
    if filtered_data.empty:
        return []
    
    # Crear opciones para el Dropdown
    return [{'label': title, 'value': title} for title in filtered_data['title']]

# Callback para mostrar los detalles del título seleccionado
@app.callback(
    Output('title-details', 'children'),
    Input('titles-dropdown', 'value')
)
def update_title_details(selected_title):
    if not selected_title:
        return html.Div("Selecciona un título para ver los detalles.")

    filtered_data = df[df['title'] == selected_title]

    if filtered_data.empty:
        return html.Div("No se encontraron detalles para este título.")

    data = filtered_data.iloc[0]
    return html.Div(
        [
            html.P(f"Título: {data['title']}"),
            html.P(f"Tipo: {data['type']}"),
            html.P(f"Director: {data['director']}"),
            html.P(f"Año de Lanzamiento: {data['release_year']}"),
            html.P(f"Duración: {data['duration']}"),
            html.P(f"Clasificación: {data['rating']}"),
        ]
    )

# Callback para mostrar los actores con paginación
@app.callback(
    Output('actors-list', 'children'),
    [Input('titles-dropdown', 'value'),
     Input('prev-actors', 'n_clicks'),
     Input('next-actors', 'n_clicks')]
)
def update_actors(selected_title, prev_clicks, next_clicks):
    if not selected_title:
        return [html.Li('Selecciona un título para ver los actores', className='list-group-item')]

    filtered_data = df[df['title'] == selected_title]
    all_actors = ', '.join(filtered_data['cast'].values).split(', ')
    page = max(0, next_clicks - prev_clicks)
    start_idx = page * actors_per_page
    end_idx = start_idx + actors_per_page

    actors = all_actors[start_idx:end_idx]
    actors_content = [html.Li(actor.strip(), className='list-group-item') for actor in actors if actor.strip()]

    return actors_content

# Función para abrir el navegador automáticamente
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8080)

