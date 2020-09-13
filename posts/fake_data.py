from faker import Faker


class FakeData:

    def __init__(self):
        self.fake = Faker()

    def fake_password(self):
        return self.fake.password(length=40, special_chars=True)

    def fake_username(self):
        return self.fake.simple_profile()["username"]

    def fake_email(self):
        return self.fake.simple_profile()["mail"]

    def fake_text(self):
        return self.fake.text()

    def fake_slug(self):
        return self.fake.slug()
