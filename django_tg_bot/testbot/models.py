from django.contrib.postgres.fields import ArrayField
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Answer(models.Model):
    chat_id = models.PositiveBigIntegerField(
        null=False,
        blank=False,
    )
    tg_login = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    user_fullname = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    phone_number = PhoneNumberField(
        null=True,
        blank=True,
        unique=True,
    )
    choices = ArrayField(
        models.CharField(
            max_length=50,
        ),
        default=list,
    )

    def __str__(self):
        return f'Chat_id: {self.chat_id}\nLogin: {self.tg_login}'

    class Meta:
        verbose_name = 'Answer'
        verbose_name_plural = 'Answers'
