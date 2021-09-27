from django import forms

from .models import Answer


class AnswerForm(forms.ModelForm):

    class Meta:
        model = Answer
        fields = (
            'id',
            'chat_id',
            'tg_login',
            'user_fullname',
            'phone_number',
            'choices',
        )
        widgets = {
            'chat_id': forms.NumberInput,
            'tg_login': forms.TextInput,
            'user_fullname': forms.TextInput,
            'phone_number': forms.TextInput(
                attrs={
                    'placeholder': 'Phone',
                },
            ),
            'choices': forms.Textarea(),
        }
