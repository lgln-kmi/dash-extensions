import dash_html_components as html
import dash_core_components as dcc

from dash.exceptions import PreventUpdate
from enrich import Output, Input, PrefixIdTransform, DashProxy
from Burger import Burger

URL_ID = "url"
CONTENT_ID = "content"


class Page:
    def __init__(self, id, label, layout=None, callbacks=None, prefix_ids=True, proxy=None):
        self.id = id
        self.label = label
        self._layout = layout
        # Per default, use prefix transform.
        self._proxy = proxy
        if proxy is None:
            transforms = [PrefixIdTransform(id)] if prefix_ids is None else []
            self._proxy = DashProxy(transforms=transforms)
            if callbacks is not None:
                callbacks(self._proxy)

    @property
    def layout(self):
        def _layout(*args, **kwargs):
            if self._layout:
                self._proxy.layout = self._layout(*args, **kwargs)
                for transform in self._proxy.transforms:
                    if isinstance(transform, PrefixIdTransform):
                        transform.initialized = False
            return self._proxy._layout_value()  # layout

        return _layout

    @property
    def callbacks(self):
        def _callbacks(app):
            return self._proxy._register_callbacks(app)

        return _callbacks


class PageCollection:
    def __init__(self, pages, default_page_id=None, path_to_page=None, is_authorized=None, unauthorized_layout=None):
        self._pages = pages
        self.is_authorized = is_authorized
        self.unauthorized_layout = unauthorized_layout \
            if unauthorized_layout is not None else lambda x, *args, **kwargs: html.Div("Unauthorized.")
        self.path_to_page = path_to_page
        self.default_page_id = default_page_id if default_page_id is not None else pages[0].id

    def navigate_to(self, path, *args, **kwargs):
        if path is None:
            raise PreventUpdate
        # Locate the page. Maybe make this is more advanced later, for now just snap the id.
        page_ids = [page.id for page in self.pages]
        next_page_id = self.default_page_id
        if path is not None:
            page_id = path[1:] if self.path_to_page is None else self.path_to_page(path)
            if page_id in page_ids:
                next_page_id = page_id
        # Check if user is authorized.
        if self.is_authorized is not None:
            if not self.is_authorized(next_page_id):
                return self.unauthorized_layout(path, *args, **kwargs)
        # Return page layout.
        return self.pages[page_ids.index(next_page_id)].layout(path, *args, **kwargs)

    def navigation(self, app, content_id=CONTENT_ID, url_id=URL_ID):
        @app.callback(Output(content_id, "children"), [Input(url_id, "pathname")])
        def navigate_to(path):
            return self.navigate_to(path)

    @property
    def pages(self):
        if self.is_authorized is None:
            return self._pages
        return [page for page in self._pages if self.is_authorized(page.id)]

    def callbacks(self, app):
        for page in self.pages:
            page.callbacks(app)


# region Menus

def make_burger(page_collection, before_pages=None, after_pages=None, href=None, **kwargs):
    children = []
    pages = page_collection.pages
    for i, page in enumerate(pages):
        children.append(html.A(children=page.label, href=href(page) if href is not None else "/{}".format(page.id)))
        if i < (len(pages) - 1):
            children.append(html.Br())
    children = before_pages + children if before_pages is not None else children
    children = children + after_pages if after_pages is not None else children
    return Burger(children=children, **kwargs)


# endregion

# region Conversions

def app_to_page(app, id, label):
    app.transforms.append(PrefixIdTransform(id))
    return Page(id=id, label=label, proxy=app)


def module_to_page(module, id, label, **kwargs):
    return Page(id=id, label=label, layout=module.layout, callbacks=module.callbacks, **kwargs)


# endregion

# region Example layouts

def default_layout(*args):
    return html.Div([html.Div(id=CONTENT_ID), dcc.Location(id=URL_ID)] + list(args))

# endregion
