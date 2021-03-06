from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from . import views
from .controllers import BaseController

base = BaseController()

router = DefaultRouter()

router.register(r'guilds', views.GuildViewSet)
router.register(r'channels', views.ChannelViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'members', views.MemberViewSet)
router.register(r'messages', views.MessageViewSet)
router.register(r'strings', views.StringViewSet)

urlpatterns = [
    url(r'^api/', include(router.urls)),
]

# link 'extension/' URLs to the extension's URLConfs
extensions = base.get_extensions()
for extension in extensions:
    try:
        urlpatterns.append(url(r'^' + extension + r'/', include('dwarf.' + extension + '.urls')))
    except ImportError:
        pass
