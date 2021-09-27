from django.contrib import admin

from .forms import AnswerForm
from .models import Answer


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'chat_id',
        'tg_login',
        'user_fullname',
        'phone_number',
        'choices',
    )
    form = AnswerForm
