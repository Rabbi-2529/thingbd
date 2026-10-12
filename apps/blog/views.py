from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.core.seo import build_seo

from .models import Category, Post


def _categories_with_posts():
    live = Q(posts__status=Post.Status.PUBLISHED, posts__published_at__lte=timezone.now())
    return Category.objects.annotate(live_posts=Count("posts", filter=live)).filter(live_posts__gt=0)


def post_list(request, category_slug=None):
    posts = Post.published.select_related("category")
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(category=category)
    page = Paginator(posts, 9).get_page(request.GET.get("page"))
    title = f"{category.name} — Blog" if category else "Blog"
    return render(request, "website/blog/post_list.html", {
        "page_obj": page,
        "category": category,
        "categories": _categories_with_posts(),
        "seo": build_seo(request, title=title,
                         description="Notes on software, automation, SEO and growing a business online."),
    })


def post_detail(request, slug):
    # Staff can preview drafts and scheduled posts; everyone else only sees live posts.
    is_staff = request.user.is_authenticated and request.user.is_staff
    source = Post.objects if is_staff else Post.published
    post = get_object_or_404(source.select_related("category", "author"), slug=slug)
    related = Post.published.filter(category=post.category).exclude(pk=post.pk)[:3] if post.category else []
    return render(request, "website/blog/post_detail.html", {
        "post": post,
        "related": related,
        "is_preview": not post.is_live,
        "seo": build_seo(request, post, title=post.title, description=post.excerpt or post.body,
                         image=post.cover_image, og_type="article"),
    })
