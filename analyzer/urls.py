from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path, include
from social_post.views import generate_post, view_posts, list_posts, check_auth, \
    post_to_mastodon, post_to_mastodon_button, get_linked_accounts, post_history, edit_post, link_mastodon_account, \
    unlink_account

urlpatterns = [
    path('admin/', admin.site.urls),
    path('generate/', generate_post, name="generate_post"),
    path('posts/', list_posts, name="list_posts"),
    path('edit-post/<int:post_id>/', edit_post, name='edit_post'),
    path('view-posts/', view_posts, name="view_posts"),
    path('post-history/<int:post_id>/', post_history, name='post-history'),
    path('check-auth/', check_auth, name="check_auth"),
    path("auth/", include("social_django.urls", namespace="social")),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("link-mastodon/", link_mastodon_account, name="link_mastodon"),
    path("unlink-account/", unlink_account, name="unlink_account"),
    path("mastodon/<str:message>/", post_to_mastodon, name="post_mastodon"),
    path("mastodon-post/", post_to_mastodon_button, name="post_mastodon"),
    path("linked-accounts/", get_linked_accounts, name="linked_accounts"),
    path("accounts/", include("django.contrib.auth.urls")),

]
