from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache

from .fake_data import FakeData
from .models import Post, User, Group, Comment, Follow


class TestStringMethods(TestCase):

    POST_CACHE = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache"
        }
    }

    fake_data = FakeData()

    user_1 = fake_data.fake_username()
    email_1 = fake_data.fake_email()
    password_1 = fake_data.fake_password()

    user_2 = fake_data.fake_username()
    email_2 = fake_data.fake_email()
    password_2 = fake_data.fake_password()

    user_3 = fake_data.fake_username()
    email_3 = fake_data.fake_email()
    password_3 = fake_data.fake_password()

    @staticmethod
    def get_image():
        return SimpleUploadedFile(
            "test.gif",
            (
                b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00"
                b"\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00"
                b"\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
            ),
            content_type="image/gif"
        )

    @staticmethod
    def upload_not_image():
        return SimpleUploadedFile("file.txt", b"i-am-a-text-file")

    def setUp(self, user_1=user_1, email_1=email_1, password_1=password_1):
        self.user = User.objects.create_user(
            username=user_1, email=email_1, password=password_1
        )
        self.non_auth_client = Client()
        self.client.force_login(self.user)
        self.text = "text_1"
        self.group = Group.objects.create(
            title="title_1", slug="slug_1", description="desc_1"
        )

    def test_signup(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, template_name="signup.html")

    def test_profile(self):
        response_profile = self.client.get(
            reverse(
                "profile",
                kwargs={
                    "username": self.user.username
                }
            )
        )
        self.assertEqual(response_profile.status_code, 200)

    def test_auth_user_can_publish(self):
        response = self.client.post(
            reverse("new_post"),
            data={
                "group": self.group.id,
                "text": self.text
            },
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        created_post = Post.objects.first()
        self.assertEqual(created_post.text, self.text)
        self.assertEqual(created_post.group, self.group)
        self.assertEqual(created_post.author, self.user)

    def test_non_auth_cant_post(self):
        response = self.non_auth_client.post(
            reverse("new_post"),
            data={
                "post": self.text
            }
        )

        self.assertRedirects(
            response, reverse("login") + "?next=" + reverse("new_post")
        )
        self.assertEqual(Post.objects.count(), 0)

    @override_settings(CACHES=POST_CACHE)
    def check_contain_post(self, url, user, group, text):
        response = self.client.get(url)

        if "paginator" in response.context:
            self.assertEqual(response.context["paginator"].count, 1)
            post = response.context["page"][0]
        else:
            post = response.context["post"]

        self.assertEqual(post.text, text)
        self.assertEqual(post.group, group)
        self.assertEqual(post.author, user)
        self.assertTrue(post.image)
        self.assertContains(response, "<img")

    def test_check_post(self):
        post = Post.objects.create(
            text=self.text, group=self.group, author=self.user
        )
        image = self.get_image()

        self.client.post(
            reverse(
                "post_edit",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            ),
            data={
                "group": self.group.id,
                "text": self.text,
                "image": image
            },
            follow=True
        )

        urls = [
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse(
                "post",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            ),
            reverse("group", kwargs={"slug": self.group.slug}),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.check_contain_post(
                    url, self.user, self.group, self.text
                )

    def test_check_not_image_file(self):
        post = Post.objects.create(
            text=self.text, group=self.group, author=self.user
        )
        no_image = self.upload_not_image()
        response = self.client.post(
            reverse(
                "post_edit",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            ),
            data={
                "group": self.group.id,
                "text": self.text,
                "image": no_image
            },
            forward=True
        )

        self.assertFormError(
            response, "form", "image",
            "Загрузите правильное изображение. Файл, который вы загрузили, "
            "поврежден или не является изображением."
        )

    def test_check_edit(self):
        post = Post.objects.create(
            text=self.text, group=self.group, author=self.user
        )
        group = Group.objects.create(
            title="title_2", slug="slug_2", description="desc_2"
        )
        new_text = "text_2"
        image = self.get_image()

        self.client.post(
            reverse(
                "post_edit",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            ),
            data={
                "group": group.id,
                "text": new_text,
                "image": image
            },
            follow=True
        )

        urls = (
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse(
                "post",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            )
        )

        for url in urls:
            with self.subTest(url=url):
                self.check_contain_post(url, self.user, group, new_text)
        response = self.client.get(
            reverse(
                "group",
                kwargs={
                    "slug": self.group.slug
                }
            )
        )
        self.assertEqual(response.context["paginator"].count, 0)

    def test_cache(self):
        self.client.get(reverse("index"))
        post = Post.objects.create(
            text="new text", group=self.group, author=self.user
        )
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, post.text)

        key = make_template_fragment_key("index_page")
        cache.delete(key)

        response = self.client.get(reverse("index"))
        self.assertContains(response, post.text)

    def test_check_comments(self):
        post = Post.objects.create(
            text=self.text, group=self.group, author=self.user)
        self.client.post(
            reverse(
                "add_comment",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            ),
            data={
                "text": "Comment",
                "post": post.id,
                "author": self.user.id
            }
        )

        comment = post.comments.select_related("author").first()
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(comment.text, "Comment")
        self.assertEqual(comment.post, post)
        self.assertEqual(comment.author, self.user)

    def test_check_non_auth_comments(self):
        post = Post.objects.create(
            text=self.text, group=self.group, author=self.user
        )
        self.non_auth_client.post(
            reverse(
                "add_comment",
                kwargs={
                    "username": self.user.username,
                    "post_id": post.id
                }
            ),
            data={
                "text": "Comment",
                "post": post.id,
                "author": self.user.id
            }
        )
        self.assertEqual(Comment.objects.count(), 0)

    def test_check_follow(
            self, user_2=user_2, email_2=email_2, password_2=password_2
    ):
        leo = User.objects.create_user(
            username=user_2, email=email_2, password=password_2
        )
        self.client.post(
            reverse(
                "profile_follow",
                kwargs={
                    "username": leo.username,
                }
            )
        )
        self.assertEqual(Follow.objects.count(), 1)

        follow = Follow.objects.first()
        self.assertEqual(follow.author, leo)
        self.assertEqual(follow.user, self.user)

    def test_check_follow_non_auth(
            self, user_2=user_2, email_2=email_2, password_2=password_2
    ):
        leo = User.objects.create_user(
            username=user_2, email=email_2, password=password_2
        )
        self.non_auth_client.post(
            reverse(
                "profile_follow",
                kwargs={
                    "username": leo.username,
                }
            )
        )
        self.assertEqual(leo.following.count(), 0)

    def test_check_unfollow(
            self, user_2=user_2, email_2=email_2, password_2=password_2
    ):
        leo = User.objects.create_user(
            username=user_2, email=email_2, password=password_2
        )
        leo.following.create(user=self.user, author=leo)

        self.client.post(
            reverse(
                "profile_unfollow",
                kwargs={
                    "username": leo.username,
                }
            )
        )
        self.assertEqual(leo.following.count(), 0)

    def test_check_follow_posts(
            self, user_2=user_2, email_2=email_2, password_2=password_2
    ):
        image = self.get_image()
        leo = User.objects.create_user(
            username=user_2, email=email_2, password=password_2
        )

        post = Post.objects.create(
            text="post leo", group=self.group, author=leo, image=image
        )

        self.client.post(
            reverse(
                "profile_follow",
                kwargs={
                    "username": leo.username,
                }
            )
        )
        self.check_contain_post(
            reverse("follow_index"), leo, self.group, post.text
        )

    def test_check_non_follow_posts(
            self, user_3=user_3, email_3=email_3, password_3=password_3
    ):
        image = self.get_image()

        mao = User.objects.create_user(
            username=user_3, email=email_3, password=password_3
        )
        post_mao = Post.objects.create(
            text="post mao", group=self.group, author=mao, image=image
        )

        response = self.client.get(reverse("follow_index"))
        self.assertNotContains(response, post_mao.text)
