from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.plotting import show, save
from bokeh.io import output_notebook
from bokeh.layouts import column, row

color = ['green','red','blue','purple','goldenrod','black','orange','pink', 'grey', 'saddlebrown', 'deepskyblue', 'indianred', 'yellowgreen', 'fuchsia', 'darkseagreen','navy','mediumpurple']*2

def datetime_figure(figure_title, y_data_name):
    p = figure(
            title=figure_title,
            x_axis_type="datetime",
            tools=["wheel_zoom", "pan", "box_zoom", "undo", "reset", "save"],
        )
    p.xaxis.axis_label = "date"
    p.yaxis.axis_label = y_data_name
    p.legend.title = figure_title

    return p

