import plotly.graph_objects as go
import pandas as pd
import numpy as np
from operator import itemgetter


def update_waterfall(data, max_features=10):
    pred_value = float(data['predicted_rv'])
    shap_dict = data['shap_values']
    avg_value = pred_value - sum([v for k,v in shap_dict.items()])

    # determine which features to show
    shap_df = pd.DataFrame([ { 'feature':k, 'shap_value':v } for k, v in shap_dict.items()])
    #print(shap_df)
    shap_df['abs_shap_value'] = abs(shap_df['shap_value'])
    shap_df['shap_sign'] = np.where(shap_df['shap_value'] < 0, "negative", "positive")

    features = shap_df.nlargest(max_features, columns='abs_shap_value')[['feature', 'shap_value']]
    #print(features)
    features_list = features['feature'].tolist()
    features.set_index('feature', inplace=True)
    others_dict = shap_df[~shap_df['feature'].isin(features_list)][['shap_sign', 'shap_value']].groupby('shap_sign').sum('shap_value').to_dict()['shap_value']
    others_dict['All other negative factors'] = others_dict.pop('negative')
    others_dict['All other positive factors'] = others_dict.pop('positive')
    features_dict = features.to_dict()['shap_value']
    features_dict.update(others_dict)
    sorted_features_dict = dict(sorted(features_dict.items(), key=itemgetter(1)))

    measure = ['absolute'] + ['relative'] * len(sorted_features_dict) + ['total']
    y = ['Average Value'] + list(sorted_features_dict.keys()) + ['Estimated Value']
    x = [avg_value] + list(sorted_features_dict.values()) + [None]
    print(len(measure), len(y), len(x))
    #
    #
    fig_w = go.Figure(go.Waterfall(
        name = "shap_waterfall", orientation="h", measure=measure,
        y = y,
        x = x,
        connector={"mode":"between", "line":{"width":4, "color":"rgb(0, 0, 0)", "dash":"solid"}},
        decreasing = {"marker":{"color":"#3498DB"}},
        increasing = {"marker":{"color":"#18BC9C"}},
        totals = {"marker":{"color":"#2C3E50"}}
    ))
    fig_w.update_layout(plot_bgcolor='#FFFFFF', xaxis_title="Rateable value £ per square meter",
                        margin=go.layout.Margin(
                            l=0,  # left margin
                            r=0,  # right margin
                            #b=0,  # bottom margin
                            t=5,  # top margin
                        )
                        )

    return fig_w