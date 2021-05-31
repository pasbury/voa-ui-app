# -*- coding: utf-8 -*-

# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import csv
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
import requests
import json
import waterfall as wf

external_stylesheets = [dbc.themes.FLATLY]

meta_tags_list = [
    {'property': 'og:title', 'content': 'Rateable Value Calculator'},
    {'property': 'og:image', 'content': 'https://voa-ui-app.herokuapp.com/assets/VOA UI.png'},
    {'property': 'og:url', 'content': 'https://voa-ui-app.herokuapp.com/'},
    {'property': 'og:description', 'content': 'Calculate the rateable value of UK commercial property, based on VOA ratings list.'}
]

# get area unit options
area_unit_lookup = {'NIA':1, 'GIA':2, 'OTH':3, 'GEA':4, 'EFA':5, 'RCA':6}
area_unit_options = [ {"label": k, "value": v } for k,v in area_unit_lookup.items() ]

# get billing authority options
with open ('data/ba_lookup.csv', 'r') as ba:
    reader = csv.reader(ba)
    billing_authority_options = [ { "label":row[0], "value":row[1] } for row in reader ]

# get special category codes
with open ('data/scat_lookup.csv', 'r') as scat:
    reader = csv.reader(scat)
    scat_options = [ { "label":row[0], "value":row[2] } for row in reader ]

# get line items and additional items
with open ('data/line_items_and_additions.csv', 'r') as line_items:
    reader = list(csv.reader(line_items))
    line_items_options = [ { "label":row[1], "value":row[0] } for row in reader ]
    line_item_lookup = {row[0]:row[1] for row in reader}
    line_item_varname_lookup = {row[1]: row[0] for row in reader}

# get column names and types for model data
with open ('data/X_column_names.json', 'r') as fp:
    col_names = json.load(fp)
with open ('data/X_column_types.json', 'r') as fp:
    col_types = json.load(fp)
schema = { c:col_types[i] for i,c in enumerate(col_names) }

total_area_input = dbc.FormGroup(
    [
        dbc.Label("Area", html_for="area"),
        dbc.Input(id="total_area_input", placeholder="Total area of hereditament", type="number", min=0, max=1000, step=10, value=10),
        dbc.FormText("Please enter the total area of the hereditament, measured in metres squared.",color="secondary"),
    ]
)
area_unit_input = dbc.FormGroup(
    [
        dbc.Label("Area measuring standard", html_for="area_unit"),
        dbc.Select(
            id="area_unit_input",
            options=area_unit_options,
            value='1'
        ),
        dbc.FormText("Please select the measuring standard corresponding to the total area entered above." ,color="secondary"),
    ]
)
billing_authority_input = dbc.FormGroup(
    [
        dbc.Label("Billing Authority (used here to indicate the location of the hereditment)", html_for="billing_authority"),
        dbc.Select(
            id="billing_authority_input",
            options=billing_authority_options,
            value='4605'
        ),
        dbc.FormText("Please select the Billing Authority where the hereditment is located." ,color="secondary"),
    ]
)
scat_input = dbc.FormGroup(
    [
        dbc.Label("Special Category and Description", html_for="scat"),
        dbc.Select(
            id="scat_input",
            options=scat_options,
            value='203'
        ),
        dbc.FormText("Please select the special category for the hereditment." ,color="secondary"),
    ]
)
parking_spaces_input = dbc.FormGroup(
    [
        dbc.Label("Car Parking Spaces", html_for="parking spaces"),
        dbc.Input(id="parking_spaces_input", placeholder="Total number of car parking spaces", type="number", min=0, max=200, step=1, value=0),
        dbc.FormText("Please enter the total number of car parking spaces.",color="secondary"),
    ]
)
floors_split_input = dbc.FormGroup(
    [
        dbc.Label("Proportion of total area on ground, first and second floors", html_for="floors 0-2"),
        dbc.InputGroup([
            dbc.Input(id="low_floors_input", value=0, placeholder="Proportion of total area in ground, first and "
                                                                  "second floors", type="number", min=0,max=100, step=5),
            dbc.InputGroupAddon("%", addon_type="append"),
            ]),
        dbc.FormText("Please enter the propotion of the total area of the hereditment that is on the ground, first and second floors.",color="secondary"),
        dbc.Label(id="high_low_floor_text", color="secondary"),
    ]
)

select_line_items_form = form = dbc.Form([
    dbc.FormGroup(
            [
                dbc.Label("Line item", className="mr-2"),
                dbc.Select(id="line_item_input", options=line_items_options),#,value='Internal Storage'),
            ],
            className="mr-3",
        ),
        dbc.Button("Add line", color="primary",className="mr-3",n_clicks=0,id='add_line_item'),
#        dbc.Button("Clear lines", color="secondary",className="mr-3",n_clicks=0,id='clear_line_items'),
    ],
    inline=True,
)

line_items_table = dash_table.DataTable(
        id='line_items_table',
        columns=(
            [{'id': 'line_item', 'name': 'Line item'},
             {'id': 'line_item_area', 'name': 'Area', 'editable':True, 'type': 'numeric'}]
        ),
        data=[],
        style_table={'width':'500px'},
        style_cell={'font_family': 'lato',},
        style_cell_conditional=[
                {
                    'if': {'column_id': 'line_item'},
                    'textAlign': 'left'
                }
            ],
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        row_deletable=True)

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, meta_tags=meta_tags_list)

server = app.server

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1('Welcome to the Rateable Value Calculator'))),
    html.Br(),
    dbc.Row(dbc.Col(html.H3('Please enter the details of the hereditment to value:'))),
    html.Br(),
    dbc.Row(dbc.Col([dbc.Form([total_area_input, area_unit_input, billing_authority_input, scat_input,
                              parking_spaces_input, floors_split_input ]),
                    dbc.Label("Select and add the line items for the hereditment"),
                    select_line_items_form,
                    html.Br(),
                    dbc.Label(id="line_items_total_text", color="secondary"),
                    html.Br(),
                    line_items_table,
                    html.Br(),
                    dbc.Button("Calculate rateable value", id='run_model', n_clicks=0, color="primary",className="mr-3")
                    ]
                    )),
    dbc.Row(dbc.Col([html.Br(), html.H3("Rateable value calculation result")])),
    html.Br(),
    dbc.Row([
        dbc.Col(dbc.Label(id='rv_number'), style={'text-align': 'center', 'font-size': '30px'}),
        dbc.Col(dbc.Label(id='rv_calc_text')),
    ]),
    html.Br(),
    dbc.Row(dbc.Col([html.Br(), html.H3("Explanation of rateable value estimation")])),
    dbc.Row(dbc.Col(dbc.Label(["This chart 'explains' the estimated rateable value per square meter as a series of "
                              "adjustments to the overall average rateable value per square meter in the ratings list."
                              "  Only the most significant factors are shown.  The adjustments are ",
                               html.A("SHAP values.", href='https://github.com/slundberg/shap',target="_blank")]))),
    dbc.Row(dbc.Col(dcc.Graph(id="waterfall_chart"))),
    ])

# Callback to update text about the split of area between low and high floors
@app.callback(
    Output(component_id='high_low_floor_text', component_property='children'),
    [Input(component_id='total_area_input', component_property='value'),
     Input(component_id='low_floors_input', component_property='value')]
)
def create_text(total_area, prop_low_floors):
    if total_area is None or prop_low_floors is None:
        return ""
    else:
        low_floors_area = int(total_area * prop_low_floors / 100)
        high_floors_area = total_area - low_floors_area
        prop_high_floors = 100 - prop_low_floors
        msg = "You have entered that " + str(prop_low_floors) + "% of the total area is on the lower floors.  That equates" \
            " to " + str(low_floors_area) + "sqm.  The remaining " + str(high_floors_area) + "sqm (i.e. " + str(prop_high_floors) \
              + "%) is on the third and higher floors."
        return msg

# Callback for adding of line item to line items table
@app.callback(
    Output('line_items_table', 'data'),
    Input('add_line_item', 'n_clicks'),
    State('line_item_input', 'value'),
    State('line_items_table', 'data'),)
def add_row(n_clicks, item, rows):#, columns):
    if n_clicks > 0:
        if rows is None:
            #rows = [{'line_item': item, 'line_item_area':0, 'line_item_area_pct':0}]
            pass
        else:
            rows.append({'line_item': line_item_lookup[item], 'line_item_area':0})
    return rows

# Callback to add text to tell user the total area of the line items entered
@app.callback(
    Output(component_id='line_items_total_text', component_property='children'),
    Input('line_items_table', 'data'),
    State('total_area_input', 'value'))
def create_line_item_total_text(rows, total_area):
    if total_area is not None:
        if total_area > 0:
            line_items_total_area = 0
            for row in rows:
                line_items_total_area += row['line_item_area']
            percent_area = 100 * line_items_total_area / total_area
            return "Line items total " + str(int(line_items_total_area)) + "sqm, " + str(int(percent_area)) + "% of the total area entered."

# Callback to build request body from user inputs, post request, and update UI with result
@app.callback(
    Output(component_id='rv_number', component_property='children'),
    Output(component_id='rv_calc_text', component_property='children'),
    Output(component_id='waterfall_chart', component_property='figure'),
    Input('run_model', 'n_clicks'),
    State('total_area_input', 'value'),
    State('area_unit_input', 'value'),
    State('billing_authority_input', 'value'),
    State('scat_input', 'value'),
    State('parking_spaces_input', 'value'),
    State('low_floors_input', 'value'),
    State('line_items_table', 'data'), )
def get_rateable_value(n_clicks, total_area, area_unit, billing_authority, scat, parking_spaces, low_floors_pct, line_items):
    if n_clicks > 0:
        X_dict = { c:0 for c in schema }
        # Add the values entered by the user
        X_dict["BillingAuthorityCode"]=int(billing_authority)
        X_dict["TotalArea"]=total_area
        X_dict["SCATCodeOnly"]=int(scat)
        X_dict["CPSpaces"]=int(parking_spaces)
        X_dict["GroundFirstOrSecondPct"]=low_floors_pct/100
        X_dict["OtherFloorPct"]=1-X_dict["GroundFirstOrSecondPct"]
        X_dict["UnitofMeasurement_Int"]=int(area_unit)
        # Process the line items
        for line_item in line_items:
            X_dict[line_item_varname_lookup[line_item['line_item']]] = line_item['line_item_area']/total_area

        X = [[ v for k,v in X_dict.items() ]]
        url = 'https://voa-model-api.herokuapp.com/voa-api/'
        json_X = json.dumps(X)
        headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
        r = requests.post(url, data=json_X, headers=headers)
        json_response_text = json.loads(r.text)
        rv_per_sqm = int(float(json_response_text['predicted_rv']))

        rv = rv_per_sqm * total_area
        message = "The model estimated a rateable value of £{:,} per sqm;  multiplying that by the total " \
                  "area of {:,} gives the estimated rateable value shown.".format(rv_per_sqm, total_area)

        return '£{:,}'.format(rv), message, wf.update_waterfall(data=json_response_text, max_features=10)
    else:
        return  "","", dash.no_update

if __name__ == '__main__':
    app.run_server(debug=True)