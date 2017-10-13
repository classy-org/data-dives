from collections import OrderedDict


def classy_colors():
    colors = OrderedDict()
    colors['pink'] = "#F77462"
    colors['blue'] = "#42C2F6"
    colors['green'] = "#50D1BF"
    colors['dark_grey'] = "#44505D"
    colors['light_grey'] = "#828B94"
    colors['black'] = "#000000"
    return colors


def classy_colorscale():
    return ((0.0, "225276"), (0.25, "42C2F6"), (0.5, "FFFFFF"), (1.0, "F77462"))


def classy_font():
    return dict(family="Museo Sans, sans-serif")
