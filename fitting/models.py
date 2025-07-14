from django.db import models
from django.conf import settings

class UserImage(models.Model):
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        db_index=True,
        null=False,
    )
    user_image_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_image'
    
    def __str__(self):
        return f"UserImage {self.id}"

