from datetime import timezone

from django.contrib.auth.models import AbstractUser, Permission, Group, User
# Create your models here.
from django.db import models

class Post(models.Model):
    prompt = models.TextField()
    title = models.CharField(max_length = 200, blank = True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def delete(self):
        """ Soft delete instead of hard delete """
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """ Restore soft-deleted posts """
        self.deleted_at = None
        self.save()

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.content.split(".")[0]
        super().save(*args, **kwargs)

    @classmethod
    def active(cls):
        """ Get only non-deleted posts """
        return cls.objects.filter(deleted_at__isnull=True)

    def __str__(self):
        return self.content[:50]


class PostHistory(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="history")
    previous_content = models.TextField()
    edited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Edit on {self.edited_at.strftime('%Y-%m-%d %H:%M:%S')}"



class LinkedAccount(models.Model):
    PLATFORM_CHOICES = [
        ("mastodon", "Mastodon"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    access_token = models.TextField()  # Store OAuth access token
    username = models.CharField(max_length=255, blank=True, null=True)  # Store linked account username
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "platform")  # Prevent duplicate accounts per user

    def __str__(self):
        return f"{self.user.username} - {self.platform} ({self.username})"