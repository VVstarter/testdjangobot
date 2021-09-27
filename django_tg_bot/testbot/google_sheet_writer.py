from typing import List

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from testbot.logger import tg_logger


class GoogleSheetsWriter:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
    ]

    def __init__(self):
        self.service = build(
            serviceName='sheets',
            version='v4',
            credentials=service_account.Credentials.from_service_account_info(
                info=settings.GOOGLE_CREDS,
            ),
        )

    def write_to_google_spreadsheet(
            self,
            data: list,
            spreadsheet_id: str = settings.GOOGLE_SPREADSHEET_ID,
            sheets_range: str = "A{}:F{}",
    ) -> None:
        try:
            resource = {
                "majorDimension": "ROWS",
                "values": [data]
            }
            values_list: List[list] = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheets_range.format('', ''),
            ).execute()['values']

            for position, values in enumerate(values_list):
                if values[0] == str(data[0]):
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=sheets_range.format(position + 1, position + 1),
                        body=resource,
                        valueInputOption="USER_ENTERED"
                    ).execute()
                    return
            else:
                self.service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=sheets_range.format(1, 1),
                    body=resource,
                    valueInputOption="USER_ENTERED"
                ).execute()

        except BaseException as e:
            tg_logger.exception('Exception when writing to Google spreadsheet')
            tg_logger.exception(e)
