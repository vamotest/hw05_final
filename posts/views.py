from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow, Comment


def get_paginated_view(request, posts, page_size=10):
    paginator = Paginator(posts, page_size)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return page, paginator


def index(request):
    posts = Post.objects.all()
    page, paginator = get_paginated_view(request, posts)
    context = {"page": page, "paginator": paginator}
    return render(request, "index.html", context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page, paginator = get_paginated_view(request, posts)
    context = {"group": group, "page": page, "paginator": paginator}
    return render(request, "group.html", context)


@login_required
def new_post(request):

    if request.method != "POST":
        form = PostForm()
        return render(request, "posts/new_post.html", {"form": form})

    form = PostForm(request.POST)

    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("index")
    return render(request, "posts/new_post.html", {"form": form})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.order_by("-pub_date").all()
    page, paginator = get_paginated_view(request, posts)
    context = {"page": page, "paginator": paginator, "author": author}
    return render(request, "posts/profile.html", context)


def post_view(request, username, post_id):
    user = get_object_or_404(User, username=username)
    post = get_object_or_404(user.posts, id=post_id)
    count = Post.objects.filter(author=user).count()
    user_followers = user.follower.filter(author=user)
    user_follow = Follow.objects.filter(user=user).count()
    comments = Comment.objects.select_related("author").filter(post=post)
    form = CommentForm()

    context = {
        "post": post,
        "profile": user,
        "count": count,
        "comments": comments,
        "form": form,
        "user_followers": user_followers,
        "user_follow": user_follow,
    }
    return render(request, "posts/post.html", context)


@login_required
def post_edit(request, username, post_id):
    user = get_object_or_404(User, username=username)
    if request.user != user:
        return redirect("post", username=username, post_id=post_id)

    post = get_object_or_404(user.posts.all(), pk=post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )

    if request.method != "POST":
        return render(request, "posts/new_post.html", {"form": form, "post": post})

    if form.is_valid():
        form.save()
        return redirect("post", username=username, post_id=post.pk)
    return render(request, "posts/new_post.html", {"form": form, "post": post})


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    username = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id)

    if request.method == "POST":
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            post.pub_date = timezone.now()
            comment.save()
            return redirect("post", username=username, post_id=post_id)

    return redirect("post", username=post.author.username, post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page, paginator = get_paginated_view(request, posts)
    context = {
        "page": page,
        "paginator": paginator,
        "follow": True
    }
    return render(request, "posts/follow.html", context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)

    if author == request.user or Follow.objects.filter(
            user=request.user, author=author).exists():
        return redirect(reverse("profile", kwargs={"username": username}))

    Follow.objects.get_or_create(user=request.user, author=author)
    return redirect(reverse("profile", kwargs={"username": username}))


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(author=author)

    if Follow.objects.filter(user=request.user, author=author):
        follow.delete()

    return redirect(reverse("profile", kwargs={"username": username}))
