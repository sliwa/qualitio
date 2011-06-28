from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType

from qualitio import core
from qualitio.report import validators


class ReportDirectory(core.BaseDirectoryModel):
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Report directories'


class Report(core.BasePathModel):
    template = models.TextField(blank=True)
    public = models.BooleanField()
    link = models.URLField(blank=True, verify_exists=False)
    MIME_CHOICES = (('text/html', 'html'),
                    ('application/xml', 'xml'),
                    ('application/json', 'json'),
                    ('text/plain', 'plain'))
    mime = models.CharField(blank=False, max_length=20, choices=MIME_CHOICES,
                            default="text/html", verbose_name="format")
    limit_choices_to = {'model__in': ["testcase", "requirement", "testrun"]}
    bound_type = models.ForeignKey(ContentType, blank=True, null=True,
                                   limit_choices_to=limit_choices_to)

    class Meta(core.BasePathModel.Meta):
        parent_class = 'ReportDirectory'
        for_parent_unique = True

    @property
    def context_dict(self):
        context_dict = {}
        for context_element in self.context.all():
           context_dict[context_element.name] = context_element.build()
        return context_dict

    @property
    def content(self):
        template = Template(self.template)
        context = Context(self.context_dict)
        return template.render(context)

    def is_html(self):
        return self.mime == "text/html"

    def save(self, *args, **kwargs):
        # significant part of this link is only ID, rest is only for information purposes.
        # Filter applayed to get rid root's empty path
        if not self.pk:
            super(Report, self).save(*args, **kwargs)

        link_elements = filter(lambda x:x, [str(self.pk),
                                            slugify(self.parent.path),
                                            slugify(self.parent.name),
                                            slugify(self.name),
                                            self.created_time.strftime("%Y/%m/%d")])

        self.link = "/".join(link_elements)
        kwargs['force_insert'] = False
        super(Report, self).save(*args, **kwargs)


class ContextElement(models.Model):
    report = models.ForeignKey("Report", related_name="context")
    name = models.CharField(max_length=512)
    query = models.TextField()

    def full_clean(self):
        """
        full_clean starts the base class full_clean validation and
        also adds 'clean_query' validation.

        Construction of the method looks like this, because 'full_clean'
        should return ALL validation errors, not just a part.
        """
        errors = {}

        try:
            super(ContextElement, self).full_clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        try:
            self.clean_query()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def clean_query(self):
        """
        clean_query validates query string
        """
        validators.clean_query_string(self.query)

    def build(self):
        return validators.clean_query_string(self.query)
