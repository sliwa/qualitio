# -*- coding: utf-8 -*-
import re
from lepl import *

from django.core.exceptions import ValidationError, FieldError
from django.template import Context, Template, TemplateSyntaxError
from django.db.models import query, loading
from django.views import debug

dot             = Drop('.')
comma           = Drop(',')
ident           = Word(Letter() | '_', Letter() | '_' | Digit())
ID              = '$ID'
None_           = Literal('None') >> (lambda x: None)
bool_           = (Literal('True') | Literal('False')) >> (lambda x: x == 'True')
float_          = Real()   >> float
int_            = Integer() >> int
str_            = String() | String("'") | String('""')
argument        = str_ | int_ | float_ | bool_ | None_ | ident | ID
with DroppedSpace():
    args            = (argument[:, comma] > list) >> 'args'
    kwarg           = (ident & Drop("=") & argument) > tuple
    kwargs          = (kwarg[:, comma] > list) >> 'kwargs'
    arguments       = args[0:1] & Drop(",") & kwargs[0:1] | args[0:1] | kwargs[0:1]
method_name     = ident > 'name'
method_call     = dot & method_name & Drop("(") & arguments & Drop(")") > Node
methods_chain   = method_call[1:] >> 'methods'
object_type     = ident > 'name'
expr            = object_type & methods_chain > Node


ALLOWED_OBJECTS = ["TestCase", "TestCaseRun", "TestRun", "Report", "Requirement", "Bug"]
ALLOWED_METHODS = ["all", "get", "filter", "exclude", "order_by", "reverse", "count"]
ALLOWED_APPS = ["require", "store", "execute", "report"]


def get_model(model_name):
    for app in ALLOWED_APPS:
        Model = loading.get_model(app, model_name)
        if Model:
            return Model
    return None


def clean_query_string(query_string, object_id=0):
    query_string = query_string.replace("$ID", str(object_id))
    try:
        ast = expr.parse(query_string)[0]
    except FullFirstMatchException as e:
        raise ValidationError({"query": str(e)})

    return build_query(ast)


def build_query(ast):
    object_name = ast.name[0]
    if object_name not in ALLOWED_OBJECTS:
        raise ValidationError({"query": "Type '%s' is not supported" % object_name})

    Model = get_model(object_name)
    if not Model:
        return query.QuerySet()

    queryset = Model.objects.all()
    for method in ast.methods:
        method_name = method.name[0]
        if method_name not in ALLOWED_METHODS:
            raise ValidationError({"query": "Method '%s' is unsupported" % method_name})

        if hasattr(method, 'args'):
            args = method.args[0]
        else:
            args = []
        if hasattr(method, 'kwargs'):
            kwargs = dict(method.kwargs[0])
        else:
            kwargs = {}
        try:
            queryset = getattr(queryset, method_name)(*args, **kwargs)
        except Model.DoesNotExist:
            return None
        except (ValueError, FieldError, TypeError) as e:
            raise ValidationError({"query": str(e) })

    return queryset


class ReportValidator(object):
    """
    Custom report and context validator.
    Usage:

    validator = ReportValidator("{% for e in elements %}<p>{{ e.name }}</p>{% endfor %}", {
        "elements": "TestCase.all()",
    })

    OR:

    validator = ReportValidator("{% for e in elements %}<p>{{ e.name }}</p>{% endfor %}", {
        "elements": TestCase.objects.all(),  # real queryset objects
    })

    Validation goes this way:
    1) First 'query_strings' are validated, errors are stored in 'errors' attribute (dict).
    2) Then those queries are evaluated and stored in 'queries' attribute.
       If there is any error it is stored in 'errors' attribute.
    3) In the end the whole template is evaluated with the 'queries'.
       If there is any error it is stored in 'errors' attribute.

    If validation is OK there's an 'queries' dictionary attribute with QuerySet's objects results.
    """

    def __init__(self, template_string, context_queries):
        self.template_string = template_string
        self.context_queries = context_queries
        self.errors = {}
        self.queries = {}

    def is_valid(self):
        for name, query in self.context_queries.items():
            try:
                self.queries[name] = self.clean_query(query)
            except ValidationError as e:
                self.errors = e.update_error_dict(self.errors)

        try:
            self.clean_template(self.template_string, self.queries)
        except ValidationError as e:
            self.errors = e.update_error_dict(self.errors)

        return not bool(self.errors)

    def clean_query(self, query):
        if isinstance(query, basestring):
            return clean_query_string(query)
        return query

    def clean_template(self, template_string, context):
        try:
            unicode(Template(template_string).render(Context(context)))
        except TemplateSyntaxError as e:
            raise ValidationError({"template": self._format_template_error_msg(e)})

    def _get_template_exception_info(self, exception):
        origin, (start, end) = exception.source
        template_source = origin.reload()
        upto = line = 0
        for num, next in enumerate(debug.linebreak_iter(template_source)):
            if start >= upto and end <= next:
                line = num
            upto = next
        return line

    def _format_template_error_msg(self, e):
        return 'Line %s: %s' % (self._get_template_exception_info(e), e)
