from django.conf.urls.defaults import patterns, include, url

from qualitio.projects import views


urlpatterns = patterns('',
                       url(r'^$',
                           views.OrganizationDetails.as_view(),
                           name="organization_details"),

                       url(r'^settings/$',
                           views.OrganizationSettings.as_view(),
                           name="organization_settings"),

                       url(r'^settings/profile/$',
                           views.OrganizationSettings.Profile.as_view(),
                           name="organization_settings_profile"),

                       url(r'^settings/users/$',
                           views.OrganizationSettings.Users.as_view(),
                           name="organization_settings_users"),

                       url(r'^project/new/$',
                           views.ProjectNew.as_view(), name="project_new"),
                       url(r'^project/(?P<slug>[\w-]+)/$',
                           views.ProjectDetails.as_view(), name="project_details"),
                       url(r'^project/(?P<slug>[\w-]+)/edit/$',
                           views.ProjectEdit.as_view(), name="project_edit"),
                       url(r'^project/(?P<slug>[\w-]+)/settings/$',
                           views.ProjectSettingsEdit.as_view(), name="project_settings"),
                       url(r'^project/(?P<slug>[\w-]+)/users/$',
                           views.ProjectUsersEdit.as_view(), name="project_users"),
                       url(r'^project/(?P<slug>[\w-]+)/users/(?P<username>[\w-]+)/remove/$',
                           views.ProjectUserRemove.as_view(), name="project_user_remove"),
                       )
