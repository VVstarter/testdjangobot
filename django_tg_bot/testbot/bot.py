from typing import Callable
from django.conf import settings
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, Filters, MessageHandler, CommandHandler, Updater, ConversationHandler, \
    CallbackQueryHandler
from telegram.utils.request import Request
import phonenumbers

from testbot.models import Answer
from testbot.logger import tg_logger
from testbot.google_sheet_writer import GoogleSheetsWriter
from testbot.constants import (
    MENU,
    SUBMIT_BUTTON_TEXT,
    SUBMIT_BUTTON_CALLBACK_DATA,
    FULLNAME_INPUT_STEP,
    PHONE_NUMBER_INPUT_STEP,
    CHOICES_INPUT_STEP,
    NAME_PATTERN,
    PHONE_PATTERN,
    CHOICES_PATTERN,
    CHOICES_MATCHES_DICT,
    FULLNAME_REPLY,
    PHONE_NUMBER_REPLY,
    CHOICES_REPLY,
    PHONE_CODES,
)


def log_errors(method: Callable) -> Callable:
    def inner(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except BaseException as e:
            tg_logger.error(e)
            raise e

    return inner


class TestBot:

    def __init__(self):
        self.request = Request(
            connect_timeout=0.5,
            read_timeout=1.0,
            con_pool_size=20,
        )
        self.bot = Bot(
            request=self.request,
            token=settings.TG_BOT_TOKEN,
        )
        self.updater = Updater(
            bot=self.bot,
            use_context=True,
            workers=10,
        )
        self.conversation_handler = self.__create_conversational_handler()
        self.updater.dispatcher.add_handler(
            self.conversation_handler,
        )
        self.google_sheets_writer = GoogleSheetsWriter()

    def __create_conversational_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler(
                    command='start',
                    callback=self.__command_start,
                )
            ],
            states={
                FULLNAME_INPUT_STEP: [
                    MessageHandler(
                        filters=Filters.regex(
                            pattern=NAME_PATTERN,
                        ),
                        callback=self.__update_fullname,
                    ),
                ],
                PHONE_NUMBER_INPUT_STEP: [
                    MessageHandler(
                        filters=Filters.regex(
                            pattern=PHONE_PATTERN,
                        ),
                        callback=self.__update_phone_number,
                    ),
                ],
                CHOICES_INPUT_STEP: [
                    CallbackQueryHandler(
                        callback=self.__update_choices,
                        pattern=CHOICES_PATTERN,
                    ),
                ],
            },
            fallbacks=[
                CommandHandler(
                    command='start',
                    callback=self.__command_start,
                )
            ],
        )

    def run(self) -> None:
        self.updater.start_polling()

    @log_errors
    def __command_start(
            self,
            update: Update,
            context: CallbackContext,
    ) -> None:
        context.user_data.clear()
        chat_id = update.message.chat_id
        tg_login = update.message.from_user.username
        answer = self.__get_user_answer(
            chat_id=chat_id,
            tg_login=tg_login,
        )

        if answer:
            update.message.reply_text(
                text=FULLNAME_REPLY,
            )
            return FULLNAME_INPUT_STEP

    @log_errors
    def __update_fullname(
            self,
            update: Update,
            context: CallbackContext,
    ) -> None:
        fullname = update.message.text

        if not [character for character in fullname if character.isalpha()] or ' ' not in fullname \
                or any([x.strip().startswith('-') for x in fullname.split()]):
            return FULLNAME_INPUT_STEP

        context.user_data['user_fullname'] = fullname.strip()
        update.message.reply_text(
            text=PHONE_NUMBER_REPLY,
        )
        return PHONE_NUMBER_INPUT_STEP

    @log_errors
    def __update_phone_number(
            self,
            update: Update,
            context: CallbackContext,
    ) -> None:
        phone_number = None

        for phone_code_dict in PHONE_CODES:
            if update.message.text.strip().startswith(phone_code_dict['dial_code']):
                try:
                    phone_number = phonenumbers.parse(
                        number=update.message.text.strip(),
                        region=phone_code_dict['code'],
                    )
                except BaseException:
                    return PHONE_NUMBER_INPUT_STEP
                break

        if not phone_number or not phonenumbers.is_valid_number(phone_number):
            return PHONE_NUMBER_INPUT_STEP

        context.user_data['phone_number'] = f'+{phone_number.country_code}{phone_number.national_number}'
        keyboard = [
            [
                InlineKeyboardButton(
                    text=menu_button['text'],
                    callback_data=menu_button['callback_data'],
                ),
            ] for menu_button in MENU
        ]
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=SUBMIT_BUTTON_TEXT,
                    callback_data=SUBMIT_BUTTON_CALLBACK_DATA,
                ),
            ],
        )
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=keyboard,
        )
        update.message.reply_text(
            text=CHOICES_REPLY,
            reply_markup=reply_markup,
        )
        return CHOICES_INPUT_STEP

    @log_errors
    def __update_choices(
            self,
            update: Update,
            context: CallbackContext,
    ) -> None:

        context.user_data['choices'] = list() \
            if not context.user_data.get('choices') \
            else context.user_data['choices']

        if update.callback_query.data == 'SUBMIT' and len(context.user_data['choices']) >= 1:
            chat_id = update.callback_query.message.chat_id
            tg_login = update.callback_query.message.chat.username
            answer = self.__get_user_answer(
                chat_id=chat_id,
                tg_login=tg_login,
            )
            answer.user_fullname = context.user_data['user_fullname']
            answer.phone_number = context.user_data['phone_number']
            answer.choices = context.user_data['choices']
            answer.save()
            self.__add_answer_to_google_sheets(
                answer=answer,
            )
            update.effective_message.reply_text(
                text="Готово!",
            )
            return ConversationHandler.END
        else:
            self.__update_button_name_and_choices_list(
                update=update,
                context=context,
            )

    @log_errors
    def __add_answer_to_google_sheets(
            self,
            answer: Answer,
    ) -> None:
        data = [
            answer.chat_id,
            answer.tg_login,
            answer.user_fullname,
            answer.phone_number.as_e164,
            ', '.join(answer.choices),
        ]
        self.google_sheets_writer.write_to_google_spreadsheet(
            data=data,
        )
        tg_logger.info(f'Successfully wrote to spreadsheet {data}')

    @staticmethod
    @log_errors
    def __get_user_answer(
            chat_id: int,
            tg_login: str,
    ) -> Answer:
        answer, _ = Answer.objects.get_or_create(
            chat_id=chat_id,
            defaults={
                'tg_login': tg_login,
            }
        )
        return answer

    @staticmethod
    @log_errors
    def __update_button_name_and_choices_list(
            update: Update,
            context: CallbackContext,
    ):
        if not CHOICES_MATCHES_DICT.get(update.callback_query.data, {}).get('name'):
            return
        if CHOICES_MATCHES_DICT[update.callback_query.data]['name'] not in context.user_data['choices']:
            context.user_data['choices'].append(CHOICES_MATCHES_DICT[update.callback_query.data]['name'])
            button_index = CHOICES_MATCHES_DICT[update.callback_query.data]['index']
            update.effective_message.reply_markup.inline_keyboard[button_index][0].text = ' '.join(
                [
                    '✅',
                    update.effective_message.reply_markup.inline_keyboard[button_index][0].text,
                ]
            )
        else:
            context.user_data['choices'].remove(CHOICES_MATCHES_DICT[update.callback_query.data]['name'])
            button_index = CHOICES_MATCHES_DICT[update.callback_query.data]['index']
            update.effective_message.reply_markup.inline_keyboard[button_index][0].text = update \
                .effective_message.reply_markup.inline_keyboard[button_index][0].text \
                .strip('✅ ')

        tg_logger.info(context.user_data['choices'])
        update.callback_query.edit_message_reply_markup(update.effective_message.reply_markup)
