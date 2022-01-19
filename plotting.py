from bokeh.plotting import figure
from bokeh.models import CDSView, DatetimeTickFormatter
from bokeh.transform import factor_cmap
from bokeh.palettes import brewer, Category10


def times_series_scatter_plot(
    data,
    source,
    x,
    y,
    legend_field,
    title="no title",
    xlabel="no xlabel",
    ylabel="no ylabel",
    view=None,
    factors=[],
):

    if view == None:
        view = CDSView(source=source)
    print(factors)
    number_of_factors = len(factors)
    if number_of_factors < 3:
        number_of_factors = 3
    p = figure(
        title=title,
        x_axis_type="datetime",
        tools=["wheel_zoom", "pan", "box_zoom", "undo", "reset", "save"],
    )

    p.xaxis.formatter = DatetimeTickFormatter(
        hours=["%d %b %Y"],
        days=["%d %b %Y"],
        months=["%d %b %Y"],
        years=["%d %b %Y"],
    )
    p.xaxis.axis_label = xlabel
    p.yaxis.axis_label = ylabel
    palette = "Category20_{}".format(number_of_factors)
    mapper = factor_cmap(
        field_name=legend_field,
        palette=palette,
        factors=sorted(factors),
        nan_color="#121212",
    )

    p.scatter(
        x=x,
        y=y,
        source=source,
        view=view,
        legend_group=legend_field,
        hover_color="green",
        color=mapper,
        size=8,
    )

    p.legend.click_policy = "hide"

    return p
