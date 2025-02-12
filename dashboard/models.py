import hashlib
import os
from django.db import models
from django.contrib.auth.models import User



class Profile(models.Model):
  
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username}"


class Dataset(models.Model):
    file = models.FileField(upload_to='datasets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_hash = models.CharField(max_length=64, unique=True, null=True)
    compare_with = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='comparisons')
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to the user who uploaded the dataset

    def save(self, *args, **kwargs):
        # Calculate hash of the file content for uniqueness check
        self.file.seek(0)
        file_hash = hashlib.sha256(self.file.read()).hexdigest()
        self.file.seek(0)  # Reset file pointer after reading
        self.file_hash = file_hash
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete the file from storage if it exists
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)


